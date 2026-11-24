import unittest
from src.parametric.graph import Graph
from src.geometry.kernel import box, volume

class GraphTests(unittest.TestCase):
    def test_incremental_geometry(self):
        g=Graph(); g.add('h',(),lambda:10); g.add('box',('h',),lambda h:box(10,10,h)); g.add('volume',('box',),volume); g.add('independent',(),lambda:42)
        self.assertEqual(len(g.evaluate()),4); self.assertEqual(g.evaluate(),())
        g.replace_compute('h',lambda:12)
        with self.assertRaises(RuntimeError): g.value('volume')
        self.assertEqual(g.evaluate(),('h','box','volume')); self.assertAlmostEqual(g.value('volume'),1200); self.assertEqual(g.value('independent'),42)
    def test_failure_retry(self):
        g=Graph(); g.add('a',(),lambda:1); g.add('b',('a',),lambda a:1/a); g.evaluate(); g.replace_compute('a',lambda:0)
        with self.assertRaises(ZeroDivisionError): g.evaluate()
        with self.assertRaises(RuntimeError): g.value('a')
        g.replace_compute('a',lambda:2); self.assertEqual(g.evaluate(),('a','b')); self.assertEqual(g.value('b'),.5)
    def test_invalid_dependency(self):
        g=Graph()
        with self.assertRaises(ValueError): g.add('a',('a',),lambda a:a)
        g.add('a',(),lambda:1)
        with self.assertRaises(ValueError): g.add('a',(),lambda:2)
    def test_diamond(self):
        g=Graph(); g.add('a',(),lambda:1); g.add('b',('a',),lambda a:a+1); g.add('c',('a',),lambda a:a+2); g.add('d',('b','c'),lambda b,c:b+c); g.evaluate(); g.replace_compute('a',lambda:2)
        self.assertEqual(g.evaluate(),('a','b','c','d')); self.assertEqual(g.value('d'),7)
