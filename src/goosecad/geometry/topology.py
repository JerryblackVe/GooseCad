"""Conservative OCCT history resolver; never guesses by enumeration index."""
from dataclasses import dataclass
from enum import Enum
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS_Shape

class Status(str, Enum):
    RESOLVED = 'resolved'
    AMBIGUOUS = 'ambiguous'
    DELETED = 'deleted'
    UNRESOLVED = 'unresolved'

@dataclass(frozen=True)
class Reference:
    feature_id: str
    role: str

@dataclass(frozen=True)
class Resolution:
    status: Status
    candidates: tuple[TopoDS_Shape, ...] = ()

class HistoryResolver:
    """Index one operation result once; follow same-type modified/unchanged shapes.

    Generated shapes are provenance, not automatic replacements for old faces.
    Only use with a completed operation and its corresponding input subshapes.
    """
    def __init__(self, operation, shape_type=TopAbs_FACE):
        if not operation.IsDone():
            raise ValueError('Operation not completed')
        self._operation = operation
        self._type = shape_type
        self._result = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(operation.Shape(), shape_type, self._result)

    def _members(self, shapes):
        indices = dict.fromkeys(i for s in shapes if not s.IsNull() and (i := self._result.FindIndex(s)) > 0)
        return tuple(self._result.FindKey(i) for i in indices)

    def generated(self, source):
        return self._members(self._operation.Generated(source))

    def resolve(self, source):
        if source.IsNull() or source.ShapeType() != self._type:
            return Resolution(Status.UNRESOLVED)
        candidates = self._members([source, *self._operation.Modified(source)])
        if len(candidates) > 1:
            return Resolution(Status.AMBIGUOUS, candidates)
        if candidates:
            return Resolution(Status.RESOLVED, candidates)
        if self._operation.IsDeleted(source):
            return Resolution(Status.DELETED)
        return Resolution(Status.UNRESOLVED)


def box_roles(builder):
    """Semantic roles from the primitive builder, stable across dimension edits."""
    if not builder.IsDone():
        raise ValueError('Box not completed')
    return {role: getattr(builder, method)() for role, method in (
        ('x-', 'BackFace'), ('x+', 'FrontFace'), ('y-', 'LeftFace'),
        ('y+', 'RightFace'), ('z-', 'BottomFace'), ('z+', 'TopFace'))}
