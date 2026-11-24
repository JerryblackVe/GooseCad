import json
import unittest
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopAbs import TopAbs_EDGE
from OCP.gp import gp_Pnt
from goosecad.geometry.kernel import box
from goosecad.geometry.topology import HistoryResolver, Reference, Status, box_roles


def builder(x=0, width=10):
    b = BRepPrimAPI_MakeBox(gp_Pnt(x, 0, 0), width, 10, 10)
    b.Build()
    return b


class PersistentTopologyTests(unittest.TestCase):
    def test_merge_and_reverse_source_order(self):
        a, b = builder(), builder(10)
        op = BRepAlgoAPI_Fuse(a.Shape(), b.Shape())
        op.SimplifyResult(True, True)
        r = HistoryResolver(op)
        sources = {'a': box_roles(a)['z+'], 'b': box_roles(b)['z+']}
        for order in (sources, dict(reversed(list(sources.items())))):
            result = r.resolve_many(order)
            self.assertEqual({v.status for v in result.values()}, {Status.MERGED})
            self.assertTrue(result['a'].candidates[0].IsSame(result['b'].candidates[0]))

    def test_generated_edges_are_not_replacement_faces(self):
        a = builder()
        op = BRepAlgoAPI_Cut(a.Shape(), box(2,20,20,(4,-5,-5)))
        source = box_roles(a)['z+']
        self.assertEqual(len(HistoryResolver(op, TopAbs_EDGE).generated(source)), 2)
        self.assertEqual(HistoryResolver(op).resolve(source).status, Status.AMBIGUOUS)

    def test_serialized_semantic_role_rebuild(self):
        old = builder()
        reference = Reference('box-A', 'x+')
        restored = Reference.from_record(json.loads(json.dumps(reference.to_record())))
        new = builder(width=25)
        roles = box_roles(new)
        result = restored.bind({'box-A': dict(reversed(list(roles.items())))})
        self.assertEqual(result.status, Status.RESOLVED)
        self.assertTrue(result.candidates[0].IsSame(roles['x+']))
        self.assertFalse(result.candidates[0].IsSame(box_roles(old)['x+']))

    def test_missing_feature_and_role(self):
        self.assertEqual(Reference('a','z+').bind({}).status, Status.UNRESOLVED)
        self.assertEqual(Reference('a','unknown').bind({'a':box_roles(builder())}).status, Status.UNRESOLVED)

    def test_invalid_records(self):
        for record in (None, {}, {'schema':True,'feature_id':'a','role':'x+'},
                       {'schema':2,'feature_id':'a','role':'x+'}, {'schema':1,'feature_id':'','role':'x+'}):
            with self.assertRaises(ValueError): Reference.from_record(record)
