import math
import unittest
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.GeomAbs import GeomAbs_Circle
from goosecad.geometry.curves import Curve,make_region,extrude_region,revolve_region
from goosecad.geometry.kernel import GeometryError,properties


def circle(x,y,r): return (Curve('circle',(x,y,r)),)
def polygon(points): return tuple(Curve('line',(*a,*b)) for a,b in zip(points,points[1:]+points[:1]))

class CurveTests(unittest.TestCase):
    def test_exact_circle(self):
        r=make_region((circle(5,0,2),)); self.assertAlmostEqual(r.area,4*math.pi,places=10)
        e=TopExp_Explorer(r.face,TopAbs_EDGE)
        self.assertEqual(BRepAdaptor_Curve(TopoDS.Edge_s(e.Current())).GetType(),GeomAbs_Circle)
        p=properties(extrude_region(r,3)); self.assertAlmostEqual(p.volume,12*math.pi,places=9); self.assertAlmostEqual(p.area,20*math.pi,places=9)
        self.assertEqual(p.solids,1)
        self.assertAlmostEqual(properties(extrude_region(r,-3)).center[2],-1.5,places=9)
    def test_annular_extrusion(self):
        r=make_region((circle(5,0,2),circle(5,0,1)))
        self.assertAlmostEqual(r.area,3*math.pi,places=10)
        p=properties(extrude_region(r,3)); self.assertAlmostEqual(p.volume,9*math.pi,places=9); self.assertAlmostEqual(p.area,24*math.pi,places=9)
    def test_revolution_torus(self):
        r=make_region((circle(5,0,2),))
        for a in (math.pi/2,math.pi,2*math.pi):
            self.assertAlmostEqual(properties(revolve_region(r,a)).volume,a*5*4*math.pi,places=8)
    def test_revolution_with_hole(self):
        r=make_region((circle(5,0,2),circle(5,0,1)))
        self.assertAlmostEqual(properties(revolve_region(r)).volume,30*math.pi**2,places=8)
    def test_mixed_arc_line_both_orientations(self):
        for loop in ((Curve('line',(1,0,5,0)),Curve('arc',(5,0,3,2,1,0))), (Curve('arc',(1,0,3,2,5,0)),Curve('line',(5,0,1,0)))):
            r=make_region((loop,)); self.assertAlmostEqual(r.area,2*math.pi,places=9)
            self.assertAlmostEqual(properties(extrude_region(r,2)).volume,4*math.pi,places=9)
    def test_two_arcs(self):
        r=make_region(((Curve('arc',(7,0,5,2,3,0)),Curve('arc',(3,0,5,-2,7,0))),))
        self.assertAlmostEqual(r.area,4*math.pi,places=9)
    def test_multiple_holes_and_winding(self):
        for pts in ([(1,-5),(11,-5),(11,5),(1,5)],[(1,-5),(1,5),(11,5),(11,-5)]):
            r=make_region((polygon(pts),circle(3,0,1),circle(8,0,2)))
            self.assertAlmostEqual(r.area,100-5*math.pi,places=9)
    def test_invalid_holes(self):
        for holes in ((circle(20,0,1),),(circle(6,0,1),),(circle(7,0,1),),(circle(5,0,1),circle(5,0,.3)),(circle(5,0,1),circle(5.5,0,1))):
            with self.subTest(holes=holes), self.assertRaises(GeometryError): make_region((circle(5,0,2),*holes))
    def test_invalid_loops(self):
        for loop in (polygon([(1,0),(5,4),(1,4),(5,0)]), (Curve('line',(1,0,5,0)),Curve('line',(5,1,1,0))), (Curve('line',(1,0,5,0)),Curve('arc',(5,0,3,0,1,0))), circle(5,0,0), (Curve('circle',(float('nan'),0,1)),), (Curve('line',(1,0,5,0)),Curve('line',(5,0,1,0)))):
            with self.subTest(loop=loop),self.assertRaises(GeometryError): make_region((loop,))
    def test_axis_crossing_arc_interior(self):
        # Endpoints positive, arc bulges across the Y axis.
        r=make_region(((Curve('line',(1,-2,1,2)),Curve('arc',(1,2,-1,0,1,-2))),))
        with self.assertRaises(GeometryError): revolve_region(r)
    def test_broadphase_equivalence(self):
        loops=(circle(10,0,8),circle(5,0,1),circle(10,0,1),circle(15,0,1))
        a,b=(make_region(loops,_broadphase=x) for x in (False,True)); self.assertAlmostEqual(a.area,b.area,places=10)
        # overlapping bounding boxes, but separated circular boundaries
        r=make_region((circle(10,0,8),circle(8,-1,1),circle(9.8,.8,1)))
        self.assertAlmostEqual(r.area,62*math.pi,places=9)
