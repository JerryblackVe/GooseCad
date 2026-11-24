import json
import unittest
from src.geometry.subshape import SubshapeReference, cut_subshape
from src.geometry.kernel import volume
from src.parametric.graph import Graph, EvaluationCancelled

class SubshapeTests(unittest.TestCase):
    def test_edge_split(self):
        ref = SubshapeReference('box', ('TopFace','LeftFace'))
        for height in (10, 20):
            shape, resolution = cut_subshape('box', height, 2, ref)
            self.assertEqual(resolution.status, 'ambiguous')
            self.assertEqual(len(resolution.candidates), 2)
            self.assertAlmostEqual(volume(shape), 80*height)

    def test_edge_deleted(self):
        ref = SubshapeReference('box', ('TopFace','FrontFace'))
        _, resolution = cut_subshape('box', 12, 2, ref, center=10)
        self.assertEqual(resolution.status, 'deleted')
        self.assertEqual(resolution.candidates, ())

    def test_vertex_deleted(self):
        ref = SubshapeReference('box', ('TopFace','FrontFace','LeftFace'))
        _, resolution = cut_subshape('box', 12, 2, ref, center=10)
        self.assertEqual(resolution.status, 'deleted')

    def test_vertex_record_roundtrip(self):
        ref = SubshapeReference('box', ('TopFace','FrontFace','RightFace'))
        restored = SubshapeReference.from_record(json.loads(json.dumps(ref.to_record())))
        self.assertEqual(ref, restored)
        for height in (10, 12, 20):
            _, resolution = cut_subshape('box', height, 2, restored)
            self.assertEqual(resolution.status, 'resolved')

    def test_invalid_reference(self):
        with self.assertRaises(ValueError):
            SubshapeReference('box', ('TopFace','BottomFace'))
        with self.assertRaises(ValueError):
            SubshapeReference.from_record({'schema': 2, 'feature_id': 'box', 'roles': []})

class ScalabilityTests(unittest.TestCase):
    def test_long_chain(self):
        g = Graph(); g.add(0, (), lambda: 0)
        for i in range(1, 1000): g.add(i, (i-1,), lambda x: x+1)
        self.assertEqual(len(g.evaluate()), 1000)
        g.replace_compute(0, lambda: 5)
        self.assertEqual(len(g.evaluate()), 1000)
        self.assertEqual(g.value(999), 1004)

    def test_cancellation_atomic(self):
        g = Graph(); g.add('a', (), lambda: 1); g.add('b', ('a',), lambda a: a+1)
        g.evaluate(); g.replace_compute('a', lambda: 9)
        calls = iter([False, True])
        with self.assertRaises(EvaluationCancelled): g.evaluate(lambda: next(calls))
        with self.assertRaises(RuntimeError): g.value('a')
        self.assertEqual(g.evaluate(), ('a','b'))
        self.assertEqual(g.value('b'), 10)

    def test_independent_1000(self):
        g = Graph()
        for i in range(1000): g.add(i, (), lambda: 0)
        g.evaluate(); g.replace_compute(500, lambda: 10)
        self.assertEqual(g.evaluate(), (500,))
        self.assertEqual(g.value(500), 10)
        self.assertEqual(g.value(501), 0)
