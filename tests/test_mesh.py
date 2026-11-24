import unittest
import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Trsf,gp_Vec,gp_Ax1,gp_Pnt,gp_Dir
from goosecad.geometry.mesh import tessellate,_faces
from goosecad.geometry.kernel import box,sphere,boolean,properties,GeometryError
from goosecad.geometry.curves import Curve,make_region,extrude_region

def volume(m):
    a,b,c=m.vertices[m.triangles].transpose(1,0,2)
    return np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6

def triangulations(s):
    f=_faces(s)
    return [BRep_Tool.Triangulation_s(TopoDS.Face_s(f.FindKey(i)),TopLoc_Location()) for i in range(1,f.Extent()+1)]

class MeshTests(unittest.TestCase):
    def test_box_winding_and_ranges(self):
        m=tessellate(box(2,3,4)); self.assertEqual(m.vertices.shape,(24,3));self.assertEqual(m.triangles.shape,(12,3));self.assertEqual(m.face_offsets,tuple(range(0,13,2)))
        self.assertAlmostEqual(volume(m),24); self.assertFalse(m.vertices.flags.writeable); self.assertFalse(m.triangles.flags.writeable)
        self.assertEqual(m.vertices.dtype,np.float64); self.assertEqual(m.triangles.dtype,np.uint32)
    def test_transformed_shape(self):
        s=box(2,3,4); tr=gp_Trsf(); tr.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)),np.pi/2); tr.SetTranslationPart(gp_Vec(10,20,30))
        s=s.Moved(TopLoc_Location(tr)); m=tessellate(s)
        np.testing.assert_allclose(m.vertices.min(axis=0),(7,20,30),atol=1e-10); np.testing.assert_allclose(m.vertices.max(axis=0),(10,22,34),atol=1e-10); self.assertAlmostEqual(volume(m),24)
    def test_original_not_meshed(self):
        s=sphere(5); self.assertTrue(all(x is None for x in triangulations(s))); p=properties(s)
        tessellate(s,linear=.05); self.assertTrue(all(x is None for x in triangulations(s))); self.assertEqual(properties(s),p)
    def test_existing_mesh_not_replaced(self):
        s=sphere(5); op=BRepMesh_IncrementalMesh(s,.5,False,.5); self.assertTrue(op.IsDone()); old=triangulations(s)[0]; count=old.NbTriangles()
        tessellate(s,linear=.01,angular=.1); self.assertEqual(triangulations(s)[0].NbTriangles(),count); self.assertEqual(old.NbTriangles(),count)
    def test_quality(self):
        s=sphere(10); coarse=tessellate(s,linear=1,angular=.8);fine=tessellate(s,linear=.05,angular=.2);v=properties(s).volume
        self.assertGreater(len(fine.triangles),len(coarse.triangles));self.assertLess(abs(volume(fine)-v),abs(volume(coarse)-v))
    def test_hole(self):
        r=make_region(((Curve('circle',(5,0,2)),),(Curve('circle',(5,0,1)),)));s=extrude_region(r,3);m=tessellate(s,linear=.01,angular=.2)
        self.assertAlmostEqual(volume(m)/properties(s).volume,1,delta=.02)
    def test_empty_and_budgets(self):
        m=tessellate(boolean('common',box(1,1,1),box(1,1,1,(5,5,5))));self.assertEqual(m.triangles.shape,(0,3));self.assertEqual(m.face_offsets,(0,))
        for kwargs in ({'max_vertices':23},{'max_triangles':11},{'linear':0},{'angular':float('nan')},{'max_vertices':True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(GeometryError): tessellate(box(2,3,4),**kwargs)
    def test_fast_path_equivalence(self):
        s=sphere(5);a=tessellate(s);b=tessellate(s,_identity_fast=False)
        np.testing.assert_array_equal(a.vertices,b.vertices);np.testing.assert_array_equal(a.triangles,b.triangles);self.assertEqual(a.face_offsets,b.face_offsets)
