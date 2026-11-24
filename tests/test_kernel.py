import math
import unittest
from goosecad.geometry.kernel import box, cylinder, sphere, boolean, properties, GeometryError, MIN_LENGTH

class KernelTests(unittest.TestCase):
    def test_box(self):
        p = properties(box(10, 20, 30, (1, 2, 3)))
        self.assertAlmostEqual(p.volume, 6000)
        self.assertAlmostEqual(p.area, 2200)
        self.assertEqual(p.solids, 1)
        for actual, expected in zip(p.center, (6, 12, 18)):
            self.assertAlmostEqual(actual, expected)

    def test_cylinder(self):
        p = properties(cylinder(2, 5))
        self.assertAlmostEqual(p.volume, 20*math.pi)
        self.assertAlmostEqual(p.area, 28*math.pi)

    def test_sphere(self):
        p = properties(sphere(3))
        self.assertAlmostEqual(p.volume, 36*math.pi)
        self.assertAlmostEqual(p.area, 36*math.pi)

    def test_invalid_dimensions(self):
        for d in (0, -1, float('nan'), float('inf'), MIN_LENGTH, 1e7, True):
            with self.subTest(d=d), self.assertRaises(GeometryError):
                box(d, 1, 1)

    def test_invalid_origin(self):
        with self.assertRaises(GeometryError): box(1, 1, 1, (0, float('nan'), 0))

    def test_boolean_overlap(self):
        a, b = box(10, 10, 10), box(10, 10, 10, (5, 0, 0))
        for mode, volume in [('union', 1500), ('cut', 500), ('common', 500)]:
            for parallel in (False, True):
                with self.subTest(mode=mode, parallel=parallel):
                    p = properties(boolean(mode, a, b, parallel=parallel))
                    self.assertAlmostEqual(p.volume, volume)
                    self.assertEqual(p.solids, 1)
        self.assertAlmostEqual(properties(a).volume, 1000)
        self.assertAlmostEqual(properties(b).volume, 1000)

    def test_disjoint(self):
        a, b = box(1, 1, 1), box(1, 1, 1, (2, 0, 0))
        self.assertEqual(properties(boolean('union', a, b)).solids, 2)
        p = properties(boolean('common', a, b))
        self.assertEqual((p.volume, p.solids, p.center), (0, 0, None))

    def test_identical_cut(self):
        a = box(1, 1, 1)
        p = properties(boolean('cut', a, a))
        self.assertEqual((p.volume, p.solids), (0, 0))

    def test_touching(self):
        a, b = box(1, 1, 1), box(1, 1, 1, (1, 0, 0))
        self.assertAlmostEqual(properties(boolean('union', a, b)).volume, 2)
        self.assertEqual(properties(boolean('common', a, b)).solids, 0)

    def test_unknown_operation(self):
        a = box(1, 1, 1)
        with self.assertRaises(GeometryError): boolean('xor', a, a)

if __name__ == '__main__': unittest.main()
