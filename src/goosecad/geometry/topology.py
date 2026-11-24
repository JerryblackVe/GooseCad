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
    MERGED = 'merged'
    DELETED = 'deleted'
    UNRESOLVED = 'unresolved'

@dataclass(frozen=True)
class Reference:
    feature_id: str
    role: str

    def to_record(self):
        return {"schema": 1, "feature_id": self.feature_id, "role": self.role}

    @classmethod
    def from_record(cls, record):
        if (not isinstance(record, dict) or set(record) != {"schema", "feature_id", "role"}
                or type(record["schema"]) is not int or record["schema"] != 1
                or any(not isinstance(record[k], str) or not record[k] for k in ("feature_id", "role"))):
            raise ValueError("Invalid reference record")
        return cls(record["feature_id"], record["role"])

    def bind(self, features):
        shape = features.get(self.feature_id, {}).get(self.role)
        if shape is None or shape.IsNull():
            return Resolution(Status.UNRESOLVED)
        return Resolution(Status.RESOLVED, (shape,))

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

    def resolve_many(self, sources):
        """Resolve distinct logical references; report shared targets explicitly.

        A split remains ambiguous even when it shares a target with another source.
        Merged is not permission to silently rebind a downstream feature.
        """
        results = {key: self.resolve(shape) for key, shape in sources.items()}
        owners = {}
        for key, result in results.items():
            for shape in result.candidates:
                owners.setdefault(self._result.FindIndex(shape), set()).add(key)
        for key, result in results.items():
            if result.status == Status.RESOLVED and len(owners[self._result.FindIndex(result.candidates[0])]) > 1:
                results[key] = Resolution(Status.MERGED, result.candidates)
        return results

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
