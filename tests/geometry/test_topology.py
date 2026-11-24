import unittest
from src.geometry.topology import FaceReference, cut_box
from src.geometry.kernel import volume

class TopologyTests(unittest.TestCase):
    def test_survival_after_edit(self):
        ref = FaceReference('box-1','FrontFace')
        for h in (10,12,20):
            s,r = cut_box('box-1',h,2,ref)
            self.assertEqual(r.status,'resolved'); self.assertEqual(len(r.candidates),1)
            self.assertAlmostEqual(volume(s),80*h)
    def test_split_not_silently_selected(self):
        for h in (10,12):
            _,r = cut_box('box-1',h,2,FaceReference('box-1','TopFace'))
            self.assertEqual(r.status,'ambiguous'); self.assertEqual(len(r.candidates),2)
            self.assertGreater(r.generated_count,0)
    def test_invalid_reference(self):
        with self.assertRaises(ValueError): cut_box('a',10,2,FaceReference('b','TopFace'))
