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
