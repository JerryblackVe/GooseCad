import unittest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.TopoDS import TopoDS_Shape
from goosecad.geometry.kernel import box
from goosecad.geometry.topology import HistoryResolver, Status, Reference, box_roles

class TopologyTests(unittest.TestCase):
    def setUp(self):
        self.builder = BRepPrimAPI_MakeBox(10,10,10)
        self.builder.Build()
        self.roles = box_roles(self.builder)
    def resolver(self, offset):
        return HistoryResolver(BRepAlgoAPI_Cut(self.builder.Shape(),box(2,20,20,(offset,-5,-5))))
    def test_split_is_ambiguous(self):
        r = self.resolver(4).resolve(self.roles['z+'])
        self.assertEqual(r.status,Status.AMBIGUOUS)
        self.assertEqual(len(r.candidates),2)
    def test_unchanged(self):
        r = self.resolver(11).resolve(self.roles['z+'])
        self.assertEqual(r.status,Status.RESOLVED)
        self.assertTrue(r.candidates[0].IsSame(self.roles['z+']))
    def test_modified(self):
        r = self.resolver(0).resolve(self.roles['z+'])
        self.assertEqual(r.status,Status.RESOLVED)
        self.assertFalse(r.candidates[0].IsSame(self.roles['z+']))
    def test_deleted(self):
        r = self.resolver(0).resolve(self.roles['x-'])
        self.assertEqual(r.status,Status.DELETED)
    def test_null(self):
        self.assertEqual(self.resolver(4).resolve(TopoDS_Shape()).status,Status.UNRESOLVED)
    def test_parameter_edit(self):
        b = BRepPrimAPI_MakeBox(20,15,12); b.Build()
        ref = Reference('box-1','z+')
        roles = box_roles(b)
        self.assertEqual(set(roles),set(self.roles))
        self.assertFalse(roles[ref.role].IsSame(self.roles[ref.role]))
        self.assertEqual(len(roles),6)
    def test_roles_coordinates(self):
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        b = BRepPrimAPI_MakeBox(20,15,12); b.Build()
        for role, face in box_roles(b).items():
            props = GProp_GProps(); BRepGProp.SurfaceProperties_s(face,props)
            axis = 'xyz'.index(role[0])
            self.assertAlmostEqual(props.CentreOfMass().Coord()[axis], (20,15,12)[axis] if role[1]=='+' else 0)
