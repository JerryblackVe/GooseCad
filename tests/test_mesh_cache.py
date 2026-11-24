import unittest
from unittest.mock import patch
import numpy as np
from goosecad.document.native import NativeDocument,Feature
from goosecad.geometry.mesh_cache import MeshCache,MeshSettings,mesh_bytes
from goosecad.geometry.kernel import GeometryError
from goosecad.parametric.dag import EvaluationError

def model():
    return NativeDocument({'x':2,'y':3,'z':4,'r':5},(Feature('box','box',('x','y','z')),Feature('sphere','sphere',('r',))))

class MeshCacheTests(unittest.TestCase):
    def test_hits_and_selective_edit(self):
        d=model();c=MeshCache(d);a=c.get('box');b=c.get('sphere');self.assertIs(a,c.get('box'))
        d.edit({'x':6});self.assertFalse(c.is_current(a));self.assertTrue(c.is_current(b));self.assertIs(b,c.get('sphere'))
        a2=c.get('box');self.assertEqual(a2.mesh.vertices[:,0].max(),6);self.assertNotEqual(a.revision,a2.revision);self.assertEqual(c.info().entries,2)
    def test_undo_redo_never_reuse_old_stamp(self):
        d=model();c=MeshCache(d);a=c.get('box');d.edit({'x':6});b=c.get('box');d.undo();u=c.get('box');d.redo();r=c.get('box')
        self.assertEqual(len({s.revision for s in (a,b,u,r)}),4);np.testing.assert_array_equal(a.mesh.vertices,u.mesh.vertices);np.testing.assert_array_equal(b.mesh.vertices,r.mesh.vertices)
    def test_failed_edit_keeps_cache(self):
        d=model();c=MeshCache(d);a=c.get('box')
        with self.assertRaises(EvaluationError):d.edit({'x':0})
        self.assertIs(a,c.get('box'));self.assertTrue(c.is_current(a))
    def test_reload_namespace(self):
        d=model();c=MeshCache(d);a=c.get('box');e=NativeDocument.from_bytes(d.to_bytes());q=MeshCache(e);b=q.get('box')
        self.assertFalse(q.is_current(a));self.assertTrue(q.is_current(b));self.assertIsNot(a,b)
    def test_settings_and_immutable(self):
        c=MeshCache(model());a=c.get('sphere');b=c.get('sphere',MeshSettings(linear=.01,angular=.1));self.assertGreater(len(b.mesh.triangles),len(a.mesh.triangles))
        for arr in (a.mesh.vertices,a.mesh.triangles):
            with self.assertRaises(ValueError):arr.setflags(write=True)
        with self.assertRaises(GeometryError):MeshSettings(linear=float('nan'))
        with self.assertRaises(GeometryError):c.get('x')
    def test_lru_and_byte_budget(self):
        d=model();c=MeshCache(d,max_entries=2);a=c.get('box');b=c.get('sphere');c.get('box');c.get('box',MeshSettings(linear=.2));self.assertIs(a,c.get('box'));self.assertIsNot(b,c.get('sphere'))
        n=mesh_bytes(a.mesh);q=MeshCache(d,max_bytes=n,max_entries=10);q.get('box');self.assertEqual(q.info().bytes,n);q.get('sphere');self.assertLessEqual(q.info().bytes,n);self.assertEqual(q.info().entries,1)
        q.clear();self.assertEqual(q.info().bytes,0)
    def test_no_cache_and_failed_build(self):
        c=MeshCache(model(),max_entries=0);self.assertIsNot(c.get('box'),c.get('box'));self.assertEqual(c.info().entries,0)
        q=MeshCache(model());
        with self.assertRaises(GeometryError):q.get('box',MeshSettings(max_vertices=1))
        self.assertEqual(q.info().entries,0)
    def test_edit_during_mesh(self):
        from goosecad.geometry.mesh import tessellate
        d=model();c=MeshCache(d)
        def interleave(s,**kw):
            d.edit({'x':6});return tessellate(s,**kw)
        with patch('goosecad.geometry.mesh_cache.tessellate',side_effect=interleave):a=c.get('box')
        self.assertFalse(c.is_current(a));self.assertEqual(c.info().entries,0);self.assertEqual(c.get('box').mesh.vertices[:,0].max(),6)
    def test_clear_during_mesh(self):
        from goosecad.geometry.mesh import tessellate
        c=MeshCache(model())
        def interleave(s,**kw):c.clear();return tessellate(s,**kw)
        with patch('goosecad.geometry.mesh_cache.tessellate',side_effect=interleave):c.get('box')
        self.assertEqual(c.info().entries,0)

    def test_large_face_cache_and_revision(self):
        from goosecad.geometry.mesh import tessellate
        d = model()
        d.edit({'r': 20})
        c = MeshCache(d)
        settings = MeshSettings(linear=.01, angular=.1)
        unchanged = c.get('box')
        first = c.get('sphere', settings)
        self.assertGreater(len(first.mesh.vertices), 8192)
        self.assertGreater(len(first.mesh.triangles), 8192)
        reference = tessellate(d.value('sphere'), linear=.01, angular=.1, _identity_fast=False)
        np.testing.assert_array_equal(first.mesh.vertices, reference.vertices)
        np.testing.assert_array_equal(first.mesh.triangles, reference.triangles)
        self.assertEqual(first.mesh.face_offsets, reference.face_offsets)
        self.assertIs(c.get('sphere', settings), first)
        d.edit({'r': 21})
        self.assertFalse(c.is_current(first))
        self.assertTrue(c.is_current(unchanged))
        self.assertIs(c.get('box'), unchanged)
        second = c.get('sphere', settings)
        self.assertTrue(c.is_current(second))
        self.assertNotEqual(first.revision, second.revision)
        reference = tessellate(d.value('sphere'), linear=.01, angular=.1, _identity_fast=False)
        np.testing.assert_array_equal(second.mesh.vertices, reference.vertices)
        np.testing.assert_array_equal(second.mesh.triangles, reference.triangles)
        self.assertEqual(second.mesh.face_offsets, reference.face_offsets)
        self.assertFalse(second.mesh.vertices.flags.writeable)
        self.assertFalse(second.mesh.triangles.flags.writeable)
