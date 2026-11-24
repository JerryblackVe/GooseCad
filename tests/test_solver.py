import unittest
from math import hypot
from goosecad.constraints import Constraint as C, solve, SolverError

class SolverTests(unittest.TestCase):
    def test_free(self):
        r=solve({'a':(1,2)},[]); self.assertEqual(r.dof,2); self.assertEqual(r.points['a'],(1,2))
    def test_fix_and_axes(self):
        r=solve({'a':(0,0),'b':(2,3),'c':(8,9)},[C('fix','a',value=(1,2)),C('horizontal','a','b'),C('vertical','b','c')]); self.assertEqual(r.status,'solved'); self.assertEqual(r.dof,2); self.assertAlmostEqual(r.points['b'][1],2); self.assertAlmostEqual(r.points['b'][0],r.points['c'][0])
    def test_coincidence(self):
        r=solve({'a':(1,2),'b':(3,4)},[C('coincident','a','b')]); self.assertEqual(r.dof,2); self.assertAlmostEqual(r.points['a'][0],r.points['b'][0]); self.assertAlmostEqual(r.points['a'][1],r.points['b'][1])
    def test_conflict(self):
        r=solve({'a':(0,0)},[C('fix','a',value=(1,2)),C('fix','a',value=(2,2))]); self.assertEqual(r.status,'inconsistent_linear'); self.assertIsNone(r.points)
    def test_dependent_rows(self):
        r=solve({'a':(0,0)},[C('fix','a',value=(1,2)),C('fix','a',value=(1,2))]); self.assertEqual(r.dof,0); self.assertEqual(r.dependent_rows,2)
    def test_distance(self):
        r=solve({'a':(0,0),'b':(2,1)},[C('fix','a',value=(0,0)),C('horizontal','a','b'),C('distance','a','b',5)]); self.assertEqual(r.status,'solved'); self.assertEqual(r.dof,0); self.assertAlmostEqual(hypot(*r.points['b']),5,places=6)
    def test_distance_free(self):
        r=solve({'a':(0,0),'b':(1,2)},[C('distance','a','b',5)]); self.assertEqual(r.status,'solved'); self.assertEqual(r.dof,3); self.assertAlmostEqual(hypot(*(x-y for x,y in zip(r.points['a'],r.points['b']))),5,places=6)
    def test_degenerate(self):
        r=solve({'a':(0,0),'b':(0,0)},[C('distance','a','b',1)]); self.assertEqual(r.status,'unresolved'); self.assertIsNone(r.points)
    def test_nonlinear_failure(self):
        r=solve({'a':(0,0),'b':(1,0)},[C('fix','a',value=(0,0)),C('fix','b',value=(1,0)),C('distance','a','b',5)]); self.assertEqual(r.status,'unresolved'); self.assertIsNone(r.points)
    def test_partition_equivalence(self):
        points={f'p{i}':(0,0) for i in range(10)}; cs=[C('fix',f'p{i}',value=(i,i)) for i in range(10)]
        a,b=solve(points,cs),solve(points,cs,partition=False); self.assertEqual(a,b); self.assertEqual(points['p1'],(0,0))
    def test_invalid(self):
        for c in [C('distance','a','b',0),C('horizontal','a','a'),C('x','a'),C('fix','a',value=(1,float('nan'))),C('coincident','a','missing')]:
            self.assertRaises(SolverError,solve,{'a':(0,0),'b':(1,1)},[c])
    def test_solution_can_be_reused(self):
        p={'a':(0,0),'b':(2,1)}; c=[C('fix','a',value=(0,0)),C('distance','a','b',5)]; r=solve(p,c)
        self.assertEqual(solve(r.points,c).status,'solved'); self.assertIs(type(r.points['a'][0]),float)
    def test_partition_residual_equivalence(self):
        p={f'p{i}':(i,i+1) for i in range(20)}; cs=[C('horizontal',f'p{i}',f'p{i+1}') for i in range(0,20,2)]
        a,b=solve(p,cs),solve(p,cs,partition=False)
        self.assertEqual((a.dof,a.dependent_rows),(b.dof,b.dependent_rows)); self.assertLessEqual(a.max_residual,1e-7); self.assertLessEqual(b.max_residual,1e-7)
        for k in p:
            for x,y in zip(a.points[k],b.points[k]): self.assertAlmostEqual(x,y,places=8)
    def test_direct_linear_projection(self):
        p={'a':(0,2),'b':(6,8),'c':(3,10)}; cs=[C('coincident','a','b'),C('horizontal','b','c'),C('horizontal','a','c'),C('fix','c',value=(3,5))]
        a,b=solve(p,cs),solve(p,cs,partition=False)
        self.assertEqual((a.dof,a.dependent_rows),(b.dof,b.dependent_rows)); self.assertEqual(a.points['a'],(3,5)); self.assertEqual(a.points['b'],(3,5)); self.assertEqual(a.max_residual,0.)
        for k in p:
            for x,y in zip(a.points[k],b.points[k]): self.assertAlmostEqual(x,y,places=8)
    def test_close_anchor_fallback(self):
        p={'a':(0,0)}; cs=[C('fix','a',value=(1,2)),C('fix','a',value=(1+1e-8,2))]
        a,b=solve(p,cs),solve(p,cs,partition=False); self.assertEqual(a,b); self.assertEqual(a.status,'solved')
