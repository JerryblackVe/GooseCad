"""Experimental semantic box-face references and OCCT cut lineage."""
from dataclasses import dataclass
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.TopExp import TopExp
from OCP.TopAbs import TopAbs_FACE
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt
from src.geometry.kernel import checked, positive

ROLES = ('TopFace','BottomFace','LeftFace','RightFace','FrontFace','BackFace')

@dataclass(frozen=True)
class FaceReference:
    feature_id: str
    role: str

@dataclass(frozen=True)
class Resolution:
    status: str
    candidates: tuple
    generated_count: int

def cut_box(feature_id, height, cutter_width, reference):
    positive(height, cutter_width)
    if reference.feature_id != feature_id or reference.role not in ROLES:
        raise ValueError('Unknown semantic reference')
    a = BRepPrimAPI_MakeBox(10, 10, height)
    b = BRepPrimAPI_MakeBox(gp_Pnt(5-cutter_width/2,-1,-1),gp_Pnt(5+cutter_width/2,11,height+1))
    source = getattr(a, reference.role)()
    op = BRepAlgoAPI_Cut(a.Shape(), b.Shape())
    if not op.IsDone():
        raise RuntimeError('Cut failed')
    result = checked(op.Shape())
    faces = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(result, TopAbs_FACE, faces)
    candidates = []
    for face in (source, *op.Modified(source)):
        if faces.Contains(face) and not any(face.IsSame(x) for x in candidates):
            candidates.append(face)
    status = ('resolved' if len(candidates)==1 else 'ambiguous' if candidates else 'deleted' if op.IsDeleted(source) else 'unresolved')
    return result, Resolution(status, tuple(candidates), len(list(op.Generated(source))))
