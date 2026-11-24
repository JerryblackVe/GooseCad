import unittest
from math import pi
from goosecad.geometry.sweep import extrude,revolve,validate_polygon
from goosecad.geometry.kernel import GeometryError,properties
from goosecad.constraints.solver import Constraint
from goosecad.sketch import solve_profile
from goosecad.parametric import Graph,Input,Operation,EvaluationError

RECT=((1,0),(3,0),(3,4),(1,4))
class SweepTests(unittest.TestCase):
    def test_extrusion(self):
        for h in (3,-3):
            p=properties(extrude(RECT,h)); self.assertAlmostEqual(p.volume,24); self.assertAlmostEqual(p.area,52);self.assertEqual(p.solids,1); self.assertAlmostEqual(p.center[2],h/2)
    def test_revolve(self):
        for angle in (pi/2,pi,2*pi):
            p=properties(revolve(RECT,angle));self.assertAlmostEqual(p.volume,16*angle,places=7);self.assertEqual(p.solids,1)
    def test_reverse_winding(self):
        self.assertAlmostEqual(properties(extrude(RECT[::-1],3)).volume,24)
        self.assertAlmostEqual(properties(revolve(RECT[::-1])).volume,32*pi)
    def test_concave(self):
        pts=((0,0),(3,0),(3,1),(1,1),(1,3),(0,3))
        self.assertAlmostEqual(properties(extrude(pts,2)).volume,10)
    def test_invalid_profile(self):
        for p in [((0,0),(1,1),(0,1),(1,0)),((0,0),(1,0),(1,0)),((0,0),(1,0),(2,0)),((0,0),(1,0),(1,float('nan'))),((0,0),(2,0),(2,2),(1,0),(0,2))]:
            with self.subTest(p=p),self.assertRaises(GeometryError): extrude(p,1)
    def test_invalid_sweeps(self):
        for h in (0,float('nan'),True,1e8):
            with self.assertRaises(GeometryError): extrude(RECT,h)
        for a in (0,-1,7,float('inf'),True):
            with self.assertRaises(GeometryError): revolve(RECT,a)
        with self.assertRaises(GeometryError): revolve(((0,0),(2,0),(2,1),(0,1)))
    def test_broadphase_agrees(self):
        from math import cos,sin
        for n in (4,16,64,128,256):
            p=tuple((10*cos(2*pi*i/n),10*sin(2*pi*i/n)) for i in range(n))
            self.assertEqual(validate_polygon(p),validate_polygon(p,_broadphase=False))
        p=((0,0),(2,2),(0,2),(2,0))
        for mode in (True,False):
            with self.assertRaises(GeometryError): validate_polygon(p,_broadphase=mode)
    def test_solved_profile(self):
        pts=dict(zip('abcd',RECT));cs=[Constraint('fix',n,value=p) for n,p in pts.items()]
        profile=solve_profile(pts,cs,tuple(pts));self.assertEqual(profile.dof,0);self.assertEqual(profile.vertices,RECT)
        self.assertAlmostEqual(properties(extrude(profile.vertices,3)).volume,24)
    def test_bad_sketch(self):
        pts=dict(zip('abcd',RECT)); cs=[Constraint('fix','a',value=(1,0)),Constraint('fix','a',value=(2,0))]
        with self.assertRaises(GeometryError): solve_profile(pts,cs,tuple(pts))
        with self.assertRaises(GeometryError): solve_profile(pts,[],('a','b','c'))
    def test_parametric_rebuild_and_rollback(self):
        def profile(w):
            p=dict(zip('abcd',((1,0),(1+w,0),(1+w,4),(1,4))))
            return solve_profile(p,[Constraint('fix',n,value=v) for n,v in p.items()],tuple(p))
        g=Graph([Input('w',2),Operation('profile',('w',),profile),Operation('solid',('profile',),lambda p:extrude(p.vertices,3))])
        g.update({'w':4});self.assertAlmostEqual(properties(g.value('solid')).volume,48)
        old=g.snapshot()
        with self.assertRaises(EvaluationError):g.update({'w':0})
        self.assertEqual(g.snapshot(),old)

    def test_distance_drives_profile(self):
        pts=dict(zip('abcd',RECT))
        cs=[Constraint('fix','a',value=(1,0)),Constraint('horizontal','a','b'),Constraint('vertical','b','c'),Constraint('horizontal','c','d'),Constraint('vertical','d','a'),Constraint('distance','a','b',3),Constraint('distance','a','d',4)]
        profile=solve_profile(pts,cs,tuple(pts));self.assertEqual(profile.dof,0)
        self.assertAlmostEqual(properties(extrude(profile.vertices,3)).volume,36,places=5)
