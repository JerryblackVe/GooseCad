import math
import unittest
import numpy as np
from OCP.TopoDS import TopoDS_Shape
from goosecad.geometry.kernel import box,sphere,boolean,translate,properties,GeometryError
from goosecad.geometry.mesh import tessellate


class TranslationTests(unittest.TestCase):
    def test_exact_mass_center_and_source_unchanged(self):
        shape=box(2,3,4)
        original=properties(shape)
        moved=translate(shape,10,-20,30)
        result=properties(moved)
        self.assertTrue(moved.IsPartner(shape))
        self.assertFalse(moved.IsSame(shape))
        self.assertEqual(properties(shape),original)
        self.assertAlmostEqual(result.volume,original.volume,places=10)
        self.assertAlmostEqual(result.area,original.area,places=10)
        np.testing.assert_allclose(result.center,(11,-18.5,32),atol=1e-10)
        self.assertIs(translate(shape,0,0,0),shape)
        back=translate(moved,-10,20,-30)
        np.testing.assert_allclose(properties(back).center,original.center,atol=1e-10)

    def test_translated_boolean_overlap_and_mesh(self):
        left=box(2,3,4)
        right=translate(left,1,0,0)
        self.assertAlmostEqual(properties(boolean("common",left,right)).volume,12,places=9)
        self.assertAlmostEqual(properties(boolean("union",left,right)).volume,36,places=9)
        self.assertAlmostEqual(properties(boolean("cut",left,right)).volume,12,places=9)
        moved=translate(left,-10,20,30)
        mesh=tessellate(moved)
        np.testing.assert_allclose(mesh.vertices.min(axis=0),(-10,20,30),atol=1e-10)
        np.testing.assert_allclose(mesh.vertices.max(axis=0),(-8,23,34),atol=1e-10)
        a,b,c=mesh.vertices[mesh.triangles].transpose(1,0,2)
        self.assertAlmostEqual(np.einsum("ij,ij->i",a,np.cross(b,c)).sum()/6,24,places=9)

    def test_empty_shape_and_invalid_offsets(self):
        left=box(1,1,1)
        empty=boolean("common",left,translate(left,3,0,0))
        self.assertEqual(properties(translate(empty,2,3,4)).solids,0)
        self.assertEqual(len(tessellate(translate(empty,2,3,4)).triangles),0)
        for invalid in (True,float("nan"),float("inf"),1e7,"1"):
            with self.subTest(invalid=invalid), self.assertRaises(GeometryError):
                translate(left,invalid,0,0)
        with self.assertRaises(GeometryError):
            translate(None,1,2,3)
        with self.assertRaises(GeometryError):
            translate(TopoDS_Shape(),1,2,3)
