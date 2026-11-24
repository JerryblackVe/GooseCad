import unittest, math, tempfile
from pathlib import Path
from src.geometry.kernel import box,cylinder,boolean,volume,export_step
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
class KernelTests(unittest.TestCase):
    def test_box(self): self.assertAlmostEqual(volume(box(10,20,30)),6000)
    def test_cylinder(self): self.assertAlmostEqual(volume(cylinder(2,5)),20*math.pi)
    def test_invalid(self):
        for v in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): box(v,1,1)
    def test_cut(self): self.assertAlmostEqual(volume(boolean(box(10,10,10),box(5,5,5),'cut')),875)
    def test_union(self): self.assertAlmostEqual(volume(boolean(box(10,10,10),box(5,5,5),'union')),1000)
    def test_intersection(self): self.assertAlmostEqual(volume(boolean(box(10,10,10),box(5,5,5),'intersection')),125)
    def test_step(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'box.step'; export_step(box(10,20,30),p)
            r=STEPControl_Reader(); self.assertEqual(r.ReadFile(str(p)),IFSelect_RetDone); self.assertGreater(r.TransferRoots(),0); self.assertAlmostEqual(volume(r.OneShape()),6000)
if __name__=='__main__': unittest.main()
