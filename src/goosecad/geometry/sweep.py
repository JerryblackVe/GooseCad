"""Exact B-Rep sweeps from a single simple XY polygon (mm, radians)."""
from math import hypot, pi, fsum
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.gp import gp_Pnt, gp_Vec, gp_Ax1, gp_Dir
from OCP.Standard import Standard_Failure
from .kernel import GeometryError, MIN_LENGTH, MAX_LENGTH, _dimension, _validate

MAX_VERTICES = 256

def _cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

def _near_segment(a,b,c):
    x,y=b[0]-a[0],b[1]-a[1]; dx,dy=c[0]-a[0],c[1]-a[1]
    t=max(0.,min(1.,(dx*x+dy*y)/(x*x+y*y)))
    return hypot(dx-t*x,dy-t*y)<=MIN_LENGTH

def _intersects(a,b,c,d):
    x,y,z,w=_cross(a,b,c),_cross(a,b,d),_cross(c,d,a),_cross(c,d,b)
    if ((x>0>y or y>0>x) and (z>0>w or w>0>z)): return True
    return any((_near_segment(a,b,c),_near_segment(a,b,d),_near_segment(c,d,a),_near_segment(c,d,b)))

def validate_polygon(vertices, *, _broadphase=True):
    """Conservative input contract: no touching, duplicate or collinear adjacent edges."""
    if type(vertices) not in (tuple,list) or not 3<=len(vertices)<=MAX_VERTICES:
        raise GeometryError('Expected 3 to 256 polygon vertices')
    if any(type(p) not in (tuple,list) or len(p)!=2 or any(type(v) not in (int,float) or not -MAX_LENGTH<=v<=MAX_LENGTH for v in p) for p in vertices):
        raise GeometryError('Invalid polygon coordinates')
    pts=tuple(tuple(map(float,p)) for p in vertices); n=len(pts)
    edges=list(zip(pts,pts[1:]+pts[:1])); bounds=[]
    for i,(a,b) in enumerate(edges):
        length=hypot(b[0]-a[0],b[1]-a[1])
        if length<=MIN_LENGTH: raise GeometryError('Degenerate polygon edge')
        # Disallow nearly collinear adjacent edges; explicit conservative subset.
        c=pts[(i+2)%n]
        if abs(_cross(a,b,c))/length<=MIN_LENGTH: raise GeometryError('Collinear adjacent edges')
        bounds.append((min(a[0],b[0]),max(a[0],b[0]),min(a[1],b[1]),max(a[1],b[1])))
    for i,(a,b) in enumerate(edges):
        l,r,bot,top=bounds[i]
        for j in range(i+2,n):
            if i==0 and j==n-1: continue
            if _broadphase:
                l2,r2,bot2,top2=bounds[j]
                if r+MIN_LENGTH<l2 or r2+MIN_LENGTH<l or top+MIN_LENGTH<bot2 or top2+MIN_LENGTH<bot: continue
            if _intersects(a,b,*edges[j]): raise GeometryError('Self-intersecting or touching polygon')
    area2=fsum(_cross(pts[0],a,b) for a,b in edges)
    if abs(area2)<=2*MIN_LENGTH**2: raise GeometryError('Degenerate polygon area')
    return pts

def _face(pts):
    # Internal helper: caller has validated the polygon exactly once.
    poly=BRepBuilderAPI_MakePolygon()
    for x,y in pts: poly.Add(gp_Pnt(x,y,0.))
    poly.Close()
    if not poly.IsDone(): raise GeometryError('OCCT wire failed')
    builder=BRepBuilderAPI_MakeFace(poly.Wire(),True)
    if not builder.IsDone(): raise GeometryError('OCCT face failed')
    face=builder.Face()
    if not BRepCheck_Analyzer(face).IsValid(): raise GeometryError('Invalid OCCT face')
    return face

def extrude(vertices,height):
    if type(height) not in (int,float): raise GeometryError('Invalid extrusion height')
    _dimension(abs(height))
    try:
        builder=BRepPrimAPI_MakePrism(_face(validate_polygon(vertices)),gp_Vec(0,0,height),True)
        if not builder.IsDone(): raise GeometryError('OCCT extrusion failed')
        return _validate(builder.Shape())
    except Standard_Failure as exc: raise GeometryError('OCCT extrusion exception') from exc

def revolve(vertices,angle=2*pi):
    """Revolve around Y, only profiles strictly at positive X; radians."""
    if type(angle) not in (int,float) or not MIN_LENGTH<angle<=2*pi: raise GeometryError('Invalid revolution angle')
    try:
        pts=validate_polygon(vertices)
        if any(x<=MIN_LENGTH for x,y in pts): raise GeometryError('Profile must be strictly on positive X side of Y axis')
        face=_face(pts)
        axis=gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,1,0))
        builder=BRepPrimAPI_MakeRevol(face,axis,True) if angle==2*pi else BRepPrimAPI_MakeRevol(face,axis,angle,True)
        if not builder.IsDone(): raise GeometryError('OCCT revolution failed')
        return _validate(builder.Shape())
    except Standard_Failure as exc: raise GeometryError('OCCT revolution exception') from exc
