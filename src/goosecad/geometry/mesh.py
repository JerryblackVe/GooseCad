"""Display-only tessellation, isolated from authoritative B-Rep geometry.

Face IDs are local to one mesh snapshot; no persistent topological naming.
Output budgets are checked before Python buffers, not before OCCT allocation.
"""
from dataclasses import dataclass
from math import pi
import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_FORWARD
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Shape
from OCP.Standard import Standard_Failure
from .kernel import GeometryError, _validate

MAX_FACES=4096
MAX_VERTICES=1_000_000
MAX_TRIANGLES=2_000_000

@dataclass(frozen=True,slots=True)
class DisplayMesh:
    vertices: np.ndarray # float64 XYZ, world coordinates, mm
    triangles: np.ndarray # uint32, zero-based, winding respects face orientation
    face_offsets: tuple[int,...] # triangle ranges by 0-based snapshot face index


def _faces(shape):
    m=TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(shape,TopAbs_FACE,m)
    return m


def tessellate(shape,*,linear=.1,angular=.5,parallel=False,max_vertices=MAX_VERTICES,max_triangles=MAX_TRIANGLES,_identity_fast=True):
    if not isinstance(shape,TopoDS_Shape) or type(linear) not in (int,float) or not .01<=linear<=1e6 or type(angular) not in (int,float) or not .1<=angular<=pi/2 or type(parallel) is not bool:
        raise GeometryError('Invalid tessellation settings')
    if type(max_vertices) is not int or not 0<max_vertices<=MAX_VERTICES or type(max_triangles) is not int or not 0<max_triangles<=MAX_TRIANGLES:
        raise GeometryError('Invalid mesh budget')
    try:
        _validate(shape,allow_empty=True)
        faces=_faces(shape)
        if faces.Extent()>MAX_FACES: raise GeometryError('Too many faces for display mesh')
        if not faces.Extent():
            v=np.empty((0,3),dtype=np.float64); t=np.empty((0,3),dtype=np.uint32);v.setflags(write=False);t.setflags(write=False)
            return DisplayMesh(v,t,(0,))
        copy=BRepBuilderAPI_Copy(shape,True,False)
        if not copy.IsDone(): raise GeometryError('B-Rep isolation failed')
        op=BRepMesh_IncrementalMesh(copy.Shape(),linear,False,angular,parallel)
        if not op.IsDone(): raise GeometryError('OCCT mesh failed')
        chunks=[]; nv=nt=0; offsets=[0]
        for i in range(1,faces.Extent()+1):
            original=faces.FindKey(i); f=TopoDS.Face_s(copy.ModifiedShape(original)); location=TopLoc_Location()
            tri=BRep_Tool.Triangulation_s(f,location)
            if tri is None or not tri.NbNodes() or not tri.NbTriangles(): raise GeometryError('Missing face triangulation')
            if original.Orientation() not in (TopAbs_FORWARD,TopAbs_REVERSED): raise GeometryError('Unsupported face orientation')
            tr=location.Transformation(); reverse=(original.Orientation()==TopAbs_REVERSED)!=tr.IsNegative()
            chunks.append((tri,tr,reverse,location.IsIdentity(),nv,nt));nv+=tri.NbNodes();nt+=tri.NbTriangles();offsets.append(nt)
            if nv>max_vertices or nt>max_triangles: raise GeometryError('Display mesh exceeds output budget')
        vertices=np.empty((nv,3),dtype=np.float64); triangles=np.empty((nt,3),dtype=np.uint32)
        for tri,tr,reverse,identity,vo,to in chunks:
            nodes = tri.NbNodes()
            count = tri.NbTriangles()
            transform = not (_identity_fast and identity)
            # NumPy allocation overhead dominates tiny faces (e.g. planar boxes).
            if count < 64:
                for i in range(1,tri.NbNodes()+1):
                    p=tri.Node(i)
                    if transform: p=p.Transformed(tr)
                    vertices[vo+i-1]=p.Coord()
                for i in range(1,tri.NbTriangles()+1):
                    a,b,c=tri.Triangle(i).Get()
                    if min(a,b,c)<1 or max(a,b,c)>tri.NbNodes() or len({a,b,c})!=3: raise GeometryError('Invalid triangle indices')
                    if reverse: b,c=c,b
                    triangles[to+i-1]=(vo+a-1,vo+b-1,vo+c-1)
                continue
            # OCP 7.9 exposes individual accessors, not a NumPy buffer view.
            # Bounded batches avoid a temporary Python list for an entire large face.
            for start in range(0,nodes,8192):
                stop=min(start+8192,nodes)
                ids=range(start+1,stop+1)
                if not transform:
                    vertices[vo+start:vo+stop]=[tri.Node(i).Coord() for i in ids]
                else:
                    vertices[vo+start:vo+stop]=[tri.Node(i).Transformed(tr).Coord() for i in ids]
            for start in range(0,count,8192):
                stop=min(start+8192,count)
                indices=np.array([tri.Triangle(i).Get() for i in range(start+1,stop+1)],dtype=np.int64)
                if (indices.min()<1 or indices.max()>nodes or np.any(indices[:,0]==indices[:,1]) or np.any(indices[:,1]==indices[:,2]) or np.any(indices[:,0]==indices[:,2])):
                    raise GeometryError('Invalid triangle indices')
                if reverse: indices=indices[:,[0,2,1]]
                triangles[to+start:to+stop]=indices+(vo-1)
        if not np.isfinite(vertices).all(): raise GeometryError('Nonfinite mesh vertex')
        vertices.setflags(write=False);triangles.setflags(write=False)
        return DisplayMesh(vertices,triangles,tuple(offsets))
    except Standard_Failure as exc: raise GeometryError('OCCT tessellation exception') from exc
