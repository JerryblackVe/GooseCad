import math
import unittest
import tempfile
from pathlib import Path
from goosecad.document.primitives import PrimitiveSpec
from goosecad.document.native import NativeError
from goosecad.document.session import DocumentSession
from goosecad.geometry.kernel import properties


class PrimitiveTests(unittest.TestCase):
    def test_exact_volume_and_native_roundtrip(self):
        for kind,dimensions,expected in (("box",(2,3,4),24),
                ("cylinder",(3,5),45*math.pi),("sphere",(3,),36*math.pi)):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as root:
                doc=PrimitiveSpec(kind,dimensions).build()
                self.assertTrue(math.isclose(properties(doc.value(kind)).volume,expected,rel_tol=1e-9))
                current=DocumentSession.new(doc)
                self.assertTrue(current.dirty)
                self.assertIsNone(current.path)
                path=Path(root)/"solid.gcad"
                current.save_as(path)
                self.assertFalse(current.dirty)
                reopened=DocumentSession.open(path)
                self.assertEqual(reopened.document.to_bytes(),doc.to_bytes())
                self.assertTrue(math.isclose(properties(reopened.document.value(kind)).volume,expected,rel_tol=1e-9))

    def test_invalid_specs_fail_before_kernel(self):
        for kind,dimensions in (("unknown",(1,)),("box",(1,2)),("sphere",(0,)),
              ("sphere",(float("nan"),)),("sphere",(float("inf"),)),
              ("sphere",(True,)),("sphere",(1e7,)),("sphere",[1])):
            with self.subTest(kind=kind,dimensions=dimensions):
                with self.assertRaises(NativeError):
                    PrimitiveSpec(kind,dimensions)


    def test_append_mixed_history_and_disk_roundtrip(self):
        from goosecad.document.native import NativeDocument
        from goosecad.parametric import Cancelled
        doc=PrimitiveSpec("box",(2,3,4)).build()
        doc.edit({"width":5})
        stamp,shape=doc.versioned_value("box")
        before=doc.to_bytes()
        spec=PrimitiveSpec("sphere",(3,))
        with self.assertRaises(Cancelled):
            spec.append_to(doc,cancelled=lambda:True)
        self.assertEqual(doc.to_bytes(),before)
        spec.append_to(doc)
        self.assertEqual(doc.versioned_value("box")[0],stamp)
        self.assertIs(doc.value("box"),shape)
        self.assertEqual(tuple(f.id for f in doc.features),("box","sphere"))
        self.assertEqual(doc.parameter_values()["sphere_radius"],3)
        self.assertTrue(math.isclose(properties(doc.value("sphere")).volume,36*math.pi,rel_tol=1e-9))
        doc.edit({"sphere_radius":4})
        after=doc.to_bytes()
        self.assertEqual(NativeDocument.from_bytes(after).to_bytes(),after)
        doc.undo()
        self.assertEqual(doc.parameter_values()["sphere_radius"],3)
        old_stamp=doc.versioned_value("sphere")[0]
        doc.undo()
        self.assertEqual(doc.to_bytes(),before)
        self.assertNotIn("sphere_radius",doc.parameter_values())
        doc.undo()
        self.assertEqual(doc.parameter_values()["width"],2)
        doc.redo()
        doc.redo()
        self.assertGreater(doc.versioned_value("sphere")[0],old_stamp)
        doc.redo()
        self.assertEqual(doc.to_bytes(),after)
        spec.append_to(doc)
        self.assertEqual(tuple(f.id for f in doc.features),("box","sphere","sphere_2"))

    def test_append_validation_and_boolean(self):
        from goosecad.document.native import Feature
        from goosecad.document.document import RevisionConflict
        doc=PrimitiveSpec("box",(2,3,4)).build()
        PrimitiveSpec("sphere",(1,)).append_to(doc)
        before=doc.to_bytes()
        depth=doc.history_depths
        for params,features in (({"width":7},(Feature("b","sphere",("width",)),)),
                                ({},(Feature("box","sphere",("width",)),)),
                                ({},(Feature("b","sphere",("box",)),)),
                                ({},(Feature("b","union",("box","missing")),))):
            with self.assertRaises(NativeError):
                doc.append_features(params,features)
            self.assertEqual(doc.to_bytes(),before)
            self.assertEqual(doc.history_depths,depth)
        with self.assertRaises(RevisionConflict):
            PrimitiveSpec("sphere",(2,)).append_to(doc,expected_revision=-1)
        doc.append_features({},(Feature("joined","union",("box","sphere")),))
        self.assertEqual(doc.features[-1].id,"joined")
        self.assertGreater(properties(doc.value("joined")).volume,24)
        doc.undo()
        self.assertEqual(doc.to_bytes(),before)

    def test_saved_session_undo_structure_returns_clean_and_cas(self):
        from goosecad.document.native import DiskRevisionConflict
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"model.gcad"
            current=DocumentSession.new(PrimitiveSpec("box",(2,3,4)).build())
            token=current.save_as(path)
            PrimitiveSpec("sphere",(2,)).append_to(current.document)
            self.assertTrue(current.dirty)
            current.select_body("sphere")
            current.document.undo()
            self.assertIsNone(current.selection)
            self.assertFalse(current.dirty)
            current.document.redo()
            self.assertTrue(current.dirty)
            self.assertEqual(current.disk_revision,token)
            outsider=DocumentSession.open(path)
            outsider.edit({"width":7})
            outsider.save()
            with self.assertRaises(DiskRevisionConflict):
                current.save()
            self.assertTrue(current.dirty)
            self.assertEqual(DocumentSession.open(path).document.parameter_values()["width"],7)
