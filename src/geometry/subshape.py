"""Experimental semantic box references, independent of enumeration order."""
from dataclasses import dataclass
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.TopExp import TopExp
from OCP.TopAbs import TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt
from src.geometry.kernel import checked, positive
from src.geometry.topology import ROLES, Resolution

_OPPOSITES = ({'TopFace','BottomFace'}, {'LeftFace','RightFace'}, {'FrontFace','BackFace'})

@dataclass(frozen=True)
class SubshapeReference:
    feature_id: str
    roles: tuple

    def __post_init__(self):
        if not isinstance(self.feature_id, str) or not self.feature_id:
            raise ValueError('Invalid feature ID')
        if (not isinstance(self.roles, tuple) or len(self.roles) not in (2, 3)
                or any(not isinstance(r, str) or r not in ROLES for r in self.roles)
                or len(set(self.roles)) != len(self.roles)
                or any(pair <= set(self.roles) for pair in _OPPOSITES)):
            raise ValueError('Invalid adjacent faces')
        object.__setattr__(self, 'roles', tuple(sorted(self.roles)))

    def to_record(self):
        return {'schema': 1, 'feature_id': self.feature_id, 'roles': list(self.roles)}

    @classmethod
    def from_record(cls, record):
        if (not isinstance(record, dict) or set(record) != {'schema','feature_id','roles'}
                or type(record['schema']) is not int or record['schema'] != 1
                or not isinstance(record['roles'], list)):
            raise ValueError('Invalid reference record')
        return cls(record['feature_id'], tuple(record['roles']))


def _mapped(shape, kind):
    index = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, index)
    return index


def cut_subshape(feature_id, height, cutter_width, reference, center=5):
    """Return exact result and same-kind lineage. Generated shapes are not aliases."""
    positive(height, cutter_width)
    if reference.feature_id != feature_id:
        raise ValueError('Foreign feature reference')
    kind = TopAbs_EDGE if len(reference.roles) == 2 else TopAbs_VERTEX
    base = BRepPrimAPI_MakeBox(10, 10, height)
    maps = [_mapped(getattr(base, role)(), kind) for role in reference.roles]
    common = [maps[0].FindKey(i) for i in range(1, maps[0].Extent()+1)
              if all(m.Contains(maps[0].FindKey(i)) for m in maps[1:])]
    if len(common) != 1:
        raise ValueError('Semantic reference not unique')
    source = common[0]
    tool = BRepPrimAPI_MakeBox(gp_Pnt(center-cutter_width/2,-1,-1),
                              gp_Pnt(center+cutter_width/2,11,height+1))
    op = BRepAlgoAPI_Cut(base.Shape(), tool.Shape())
    if not op.IsDone():
        raise RuntimeError('Cut failed')
    result = checked(op.Shape())
    index = _mapped(result, kind)
    candidates = []
    for candidate in (source, *op.Modified(source)):
        if index.Contains(candidate) and not any(candidate.IsSame(x) for x in candidates):
            candidates.append(candidate)
    status = ('resolved' if len(candidates)==1 else 'ambiguous' if candidates else
              'deleted' if op.IsDeleted(source) else 'unresolved')
    return result, Resolution(status, tuple(candidates), len(list(op.Generated(source))))
