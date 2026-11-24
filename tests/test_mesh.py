import unittest
import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Trsf,gp_Vec,gp_Ax1,gp_Ax2,gp_Pnt,gp_Dir
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
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

    def test_mirrored_box_and_sphere(self):
        tr = gp_Trsf()
        tr.SetMirror(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)))
        self.assertTrue(tr.IsNegative())
        for shape, center, expected in ((box(2, 3, 4, (2, 0, 0)), (-3, 1.5, 2), 24.),
                                        (sphere(5, (8, 0, 0)), (-8, 0, 0), 4*np.pi*125/3)):
            # A negative TopLoc exercises the winding correction; OCCT's signed
            # B-Rep mass for that location is negative. A transformed copy is
            # the physically valid mirrored solid, with positive exact mass.
            located = shape.Moved(TopLoc_Location(tr))
            copied = BRepBuilderAPI_Transform(shape, tr, True).Shape()
            self.assertAlmostEqual(properties(copied).volume, expected, delta=expected*1e-10)
            for reflected in (located, copied):
                with self.subTest(expected=expected, negative=reflected.Location().Transformation().IsNegative()):
                    mesh = tessellate(reflected, linear=.01, angular=.2)
                    slow = tessellate(reflected, linear=.01, angular=.2, _identity_fast=False)
                    np.testing.assert_array_equal(mesh.vertices, slow.vertices)
                    np.testing.assert_array_equal(mesh.triangles, slow.triangles)
                    self.assertEqual(mesh.face_offsets, slow.face_offsets)
                    self.assertGreater(volume(mesh), 0)
                    self.assertAlmostEqual(volume(mesh), expected, delta=expected*.005)
                    a, b, c = mesh.vertices[mesh.triangles].transpose(1, 0, 2)
                    normals = np.cross(b-a, c-a)
                    radial = (a+b+c)/3 - center
                    nondegenerate = np.linalg.norm(normals, axis=1) > 1e-12
                    self.assertGreater(np.count_nonzero(nondegenerate), 0)
                    self.assertTrue(np.all(np.einsum('ij,ij->i', normals, radial)[nondegenerate] > 0))

    def test_parallel_equivalence(self):
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Compound
        builder = BRep_Builder()
        shapes = TopoDS_Compound()
        builder.MakeCompound(shapes)
        for i in range(20):
            builder.Add(shapes, sphere(5, (i*15, 0, 0)))
        for shape in (box(2, 3, 4), sphere(5), shapes):
            with self.subTest(faces=_faces(shape).Extent()):
                serial = tessellate(shape, linear=.05, angular=.3)
                parallel = tessellate(shape, linear=.05, angular=.3, parallel=True)
                self.assertEqual(serial.vertices.shape, parallel.vertices.shape)
                self.assertEqual(serial.triangles.shape, parallel.triangles.shape)
                self.assertEqual(serial.face_offsets, parallel.face_offsets)
                self.assertGreater(volume(parallel), 0)
                self.assertAlmostEqual(volume(serial), volume(parallel), delta=properties(shape).volume*1e-10)
                self.assertAlmostEqual(volume(parallel), properties(shape).volume, delta=properties(shape).volume*.03)
                def sorted_vertices(m):
                    return m.vertices[np.lexsort(m.vertices.T[::-1])]
                np.testing.assert_allclose(sorted_vertices(serial), sorted_vertices(parallel), rtol=0, atol=1e-10)
