import os,unittest
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from goosecad.document.native import NativeDocument,Feature
from goosecad.view.scene import Scene,polydata,ViewError
from goosecad.geometry.mesh import tessellate
from goosecad.geometry.kernel import box

def model():return NativeDocument({'x':2,'y':3,'z':4,'r':2},(Feature('box','box',('x','y','z')),Feature('sphere','sphere',('r',))))
class ViewTests(unittest.TestCase):
    def test_buffers(self):
        m=tessellate(box(2,3,4));p=polydata(m);self.assertEqual(p.GetNumberOfCells(),12);np.testing.assert_array_equal(vtk_to_numpy(p.GetPoints().GetData()),m.vertices);np.testing.assert_array_equal(vtk_to_numpy(p.GetPolys().GetConnectivityArray()).reshape(-1,3),m.triangles)
    @unittest.skipUnless(os.getenv('GC_RENDER_TESTS')=='1','explicit render test opt-in')
    def test_render_pick_and_revision(self):
        d=model();s=Scene(d,offscreen=True,size=(320,240))
        try:
            self.assertEqual(s.refresh(['box']),('box',));s.fit();s.orbit(30,20);s.render()
            im=vtk.vtkWindowToImageFilter();im.SetInput(s.window);im.ReadFrontBufferOff();im.Update();pixels=vtk_to_numpy(im.GetOutput().GetPointData().GetScalars());self.assertGreater(np.count_nonzero(np.any(pixels!=pixels[0],axis=1)),len(pixels)/100)
            hit=s.pick(160,120);self.assertIsNotNone(hit);self.assertEqual(hit.body,'box');self.assertTrue(0<=hit.face<6)
            d.edit({'x':6});self.assertIsNone(s.pick(160,120));
            with self.assertRaises(ViewError):s.render()
            self.assertEqual(s.refresh(['box']),('box',));s.fit();s.render();self.assertIsNotNone(s.pick(160,120));self.assertEqual(s.refresh(['box']),())
        finally:s.close()
    @unittest.skipUnless(os.getenv('GC_RENDER_TESTS')=='1','explicit render test opt-in')
    def test_actor_reuse_and_remove(self):
        d=model();s=Scene(d,offscreen=True,size=(160,120))
        try:
            s.refresh(['box','sphere']);old=s._actors['sphere'][1];d.edit({'x':6});self.assertEqual(s.refresh(['box','sphere']),('box',));self.assertIs(old,s._actors['sphere'][1]);s.cache.clear();self.assertEqual(s.refresh(['box','sphere']),());self.assertIs(old,s._actors['sphere'][1]);s.refresh(['box']);self.assertEqual(s.renderer.GetActors().GetNumberOfItems(),1)
        finally:s.close()

    @unittest.skipUnless(os.getenv('GC_INTERACT_TESTS')=='1','explicit window interaction opt-in')
    def test_window_trackball_events(self):
        d=model();s=Scene(d,size=(320,240))
        try:
            s.refresh(['box']);s.fit();i=vtk.vtkRenderWindowInteractor();i.SetRenderWindow(s.window);i.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera());s.render();i.Initialize()
            before=s.renderer.GetActiveCamera().GetPosition()
            i.SetEventInformation(160,120);i.InvokeEvent('LeftButtonPressEvent');i.SetEventInformation(190,145);i.InvokeEvent('MouseMoveEvent');i.InvokeEvent('LeftButtonReleaseEvent')
            self.assertNotEqual(before,s.renderer.GetActiveCamera().GetPosition())
            i.Disable()
        finally:s.close()

    @unittest.skipUnless(os.getenv('GC_RENDER_TESTS')=='1','explicit render test opt-in')
    def test_scene_budget_preserves_previous(self):
        s=Scene(model(),offscreen=True,max_vertices=24,max_triangles=12)
        try:
            s.refresh(['box']);old=s._actors['box'][1]
            with self.assertRaises(ViewError):s.refresh(['box','sphere'])
            self.assertIs(old,s._actors['box'][1]);self.assertEqual(s.renderer.GetActors().GetNumberOfItems(),1)
        finally:s.close()

    def test_prepare_worker_publish_owner_and_reject_stale(self):
        from concurrent.futures import ThreadPoolExecutor
        from goosecad.parametric import Cancelled
        from threading import get_ident
        d=model();s=Scene(d,offscreen=True)
        try:
            s.refresh(['box','sphere'])
            old_sphere=s._actors['sphere'][1]
            old_box=s._actors['box'][1]
            d.edit({'x':6})
            plan=s.plan_refresh(['box','sphere'])
            owner=get_ident()
            def prepare():
                self.assertNotEqual(get_ident(),owner)
                return plan.prepare()
            with ThreadPoolExecutor(max_workers=1) as pool:
                prepared=pool.submit(prepare).result(timeout=10)
                self.assertIs(old_box,s._actors['box'][1])
                self.assertEqual(s.publish(prepared),('box',))
                self.assertIs(old_sphere,s._actors['sphere'][1])
                self.assertIsNot(old_box,s._actors['box'][1])
                with self.assertRaises(ViewError):
                    pool.submit(s.publish,prepared).result(timeout=10)
                with self.assertRaises(Cancelled):
                    pool.submit(plan.prepare,cancelled=lambda:True).result(timeout=10)
                d.edit({'x':9})
                with self.assertRaises(ViewError):
                    s.publish(prepared)
                self.assertEqual(s.refresh(['box','sphere']),('box',))
        finally:s.close()

    def test_foreign_prepared_scene_and_budget(self):
        d=model();s=Scene(d,offscreen=True,max_vertices=24,max_triangles=12)
        other=Scene(d,offscreen=True)
        try:
            s.refresh(['box']);old=s._actors['box'][1]
            with self.assertRaises(ViewError):
                s.plan_refresh(['box','sphere']).prepare()
            with self.assertRaises(ViewError):
                s.publish(other.plan_refresh(['box']).prepare())
            self.assertIs(old,s._actors['box'][1])
        finally:
            other.close();s.close()
