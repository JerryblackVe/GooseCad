"""Bounded XY regions with exact lines, three-point circular arcs and circles.

One outer loop, disjoint nonnested holes. All coordinates in mm. The returned
face is borrowed read-only, as are other DAG geometry values.
"""
from dataclasses import dataclass
from math import hypot, pi
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRepTools import BRepTools
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.GC import GC_MakeArcOfCircle
from OCP.gp import gp_Pnt, gp_Ax2, gp_Ax1, gp_Dir, gp_Circ, gp_Pln, gp_Vec
from OCP.TopoDS import TopoDS, TopoDS_Face
from OCP.TopAbs import TopAbs_IN, TopAbs_OUT
from OCP.Standard import Standard_Failure
from .kernel import GeometryError, MIN_LENGTH, MAX_LENGTH, _dimension, _validate

MAX_LOOPS = 32
MAX_EDGES = 256
ARITY = {'line':4, 'arc':6, 'circle':3}

@dataclass(frozen=True, slots=True)
class Curve:
    kind: str
    coordinates: tuple[float, ...]

@dataclass(frozen=True, slots=True)
class Region:
    face: TopoDS_Face
    area: float
    xmin: float


def _p(x,y): return gp_Pnt(x,y,0.)

def _xy_dist(a,b): return hypot(a[0]-b[0],a[1]-b[1])

def _edge(c):
    if type(c) is not Curve or type(c.kind) is not str or c.kind not in ARITY or type(c.coordinates) not in (tuple,list) or len(c.coordinates)!=ARITY[c.kind]:
        raise GeometryError('Invalid curve specification')
    v=c.coordinates
    if any(type(x) not in (int,float) or not -MAX_LENGTH<=x<=MAX_LENGTH for x in v): raise GeometryError('Invalid curve coordinates')
    if c.kind=='circle':
        x,y,r=v; _dimension(r)
        if abs(x)+r>MAX_LENGTH or abs(y)+r>MAX_LENGTH: raise GeometryError('Circle outside domain')
        builder=BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(_p(x,y),gp_Dir(0,0,1)),r))
        first=last=(x+r,y)
    else:
        first=tuple(v[:2]); last=tuple(v[-2:])
        if _xy_dist(first,last)<=MIN_LENGTH: raise GeometryError('Coincident curve endpoints')
        if c.kind=='line': builder=BRepBuilderAPI_MakeEdge(_p(*first),_p(*last))
        else:
            mid=tuple(v[2:4]); length=_xy_dist(first,last)
            if min(_xy_dist(first,mid),_xy_dist(last,mid))<=MIN_LENGTH or abs((last[0]-first[0])*(mid[1]-first[1])-(last[1]-first[1])*(mid[0]-first[0]))/length<=MIN_LENGTH:
                raise GeometryError('Degenerate circular arc')
            arc=GC_MakeArcOfCircle(_p(*first),_p(*mid),_p(*last))
            if not arc.IsDone(): raise GeometryError('OCCT arc failed')
            builder=BRepBuilderAPI_MakeEdge(arc.Value())
    if not builder.IsDone(): raise GeometryError('OCCT edge failed')
    return builder.Edge(),first,last


def _bounds(shape):
    b=Bnd_Box(); BRepBndLib.AddOptimal_s(shape,b,False,False)
    return b.Get()


def _area(face):
    p=GProp_GProps(); BRepGProp.SurfaceProperties_s(face,p)
    return p.Mass()


def _loop(curves):
    if not curves or (any(c.kind=='circle' for c in curves if type(c) is Curve) and len(curves)!=1): raise GeometryError('A circle must be its own loop')
    if len(curves)==1 and (type(curves[0]) is not Curve or curves[0].kind!='circle'): raise GeometryError('Open loop')
    builder=BRepBuilderAPI_MakeWire(); start=previous=None
    for c in curves:
        edge,first,last=_edge(c)
        if start is None: start=first
        # No auto-healing or near-endpoint snapping in this format.
        if previous is not None and first!=previous: raise GeometryError('Disconnected ordered loop')
        builder.Add(edge)
        if not builder.IsDone(): raise GeometryError('OCCT wire failed')
        previous=last
    if start!=previous: raise GeometryError('Open loop')
    wire=builder.Wire()
    fb=BRepBuilderAPI_MakeFace(gp_Pln(_p(0,0),gp_Dir(0,0,1)),wire,True)
    if not fb.IsDone(): raise GeometryError('OCCT loop face failed')
    face=fb.Face()
    if not BRepCheck_Analyzer(face).IsValid() or _area(face)<=MIN_LENGTH**2: raise GeometryError('Invalid or self-intersecting loop')
    wire=BRepTools.OuterWire_s(face)
    bounds=_bounds(wire)
    if max(abs(bounds[i]) for i in (0,1,3,4))>MAX_LENGTH+MIN_LENGTH: raise GeometryError('Curve outside domain')
    return face,wire,start,bounds


def _state(face,point): return BRepClass_FaceClassifier(face,_p(*point),MIN_LENGTH).State()


def _separate(a,b,*,broadphase):
    # Skip expensive exact distance when XY boxes are strictly disjoint.
    if broadphase and (a[3][3]+MIN_LENGTH<b[3][0] or b[3][3]+MIN_LENGTH<a[3][0] or a[3][4]+MIN_LENGTH<b[3][1] or b[3][4]+MIN_LENGTH<a[3][1]): return True
    dist=BRepExtrema_DistShapeShape(a[1],b[1],MIN_LENGTH)
    if not dist.IsDone() or dist.Value()<=MIN_LENGTH: raise GeometryError('Loops intersect or touch')
    return False


def make_region(loops, *, _broadphase=True):
    if type(loops) not in (tuple,list) or not 1<=len(loops)<=MAX_LOOPS or any(type(c) not in (tuple,list) for c in loops) or sum(map(len,loops))>MAX_EDGES:
        raise GeometryError('Invalid region size')
    try:
        outer,*holes=[_loop(c) for c in loops]
        for i,h in enumerate(holes):
            if _separate(outer,h,broadphase=_broadphase) or _state(outer[0],h[2])!=TopAbs_IN: raise GeometryError('Hole outside outer loop')
            for other in holes[:i]:
                if _separate(h,other,broadphase=_broadphase): continue
                if _state(h[0],other[2])!=TopAbs_OUT or _state(other[0],h[2])!=TopAbs_OUT: raise GeometryError('Nested or overlapping holes')
        if holes:
            fb=BRepBuilderAPI_MakeFace(outer[0])
            for h in holes: fb.Add(TopoDS.Wire_s(h[1].Reversed()))
            if not fb.IsDone(): raise GeometryError('OCCT region face failed')
            face=fb.Face()
            if not BRepCheck_Analyzer(face).IsValid(): raise GeometryError('Invalid region face')
        else: face=outer[0]
        area=_area(face)
        if not area>MIN_LENGTH**2: raise GeometryError('Empty region')
        return Region(face,area,outer[3][0])
    except Standard_Failure as exc: raise GeometryError('OCCT region exception') from exc


def extrude_region(region,height):
    if type(region) is not Region or type(height) not in (int,float): raise GeometryError('Invalid region or height')
    _dimension(abs(height))
    try:
        op=BRepPrimAPI_MakePrism(region.face,gp_Vec(0,0,height),True)
        if not op.IsDone(): raise GeometryError('OCCT prism failed')
        return _validate(op.Shape())
    except Standard_Failure as exc: raise GeometryError('OCCT prism exception') from exc


def revolve_region(region,angle=2*pi):
    if type(region) is not Region or type(angle) not in (int,float) or not MIN_LENGTH<angle<=2*pi: raise GeometryError('Invalid region or angle')
    if region.xmin<=MIN_LENGTH: raise GeometryError('Region must be strictly positive X')
    try:
        axis=gp_Ax1(_p(0,0),gp_Dir(0,1,0))
        op=BRepPrimAPI_MakeRevol(region.face,axis,True) if angle==2*pi else BRepPrimAPI_MakeRevol(region.face,axis,angle,True)
        if not op.IsDone(): raise GeometryError('OCCT revolution failed')
        return _validate(op.Shape())
    except Standard_Failure as exc: raise GeometryError('OCCT revolution exception') from exc
