"""Closed declarative templates for new native parameter documents."""
from dataclasses import dataclass
from math import isfinite
from goosecad.document.native import NativeDocument, Feature, NativeError
from goosecad.geometry.kernel import MIN_LENGTH, MAX_LENGTH

PRIMITIVES = {
    "box": ("width","depth","height"),
    "cylinder": ("radius","height"),
    "sphere": ("radius",),
}


@dataclass(frozen=True, slots=True)
class PrimitiveSpec:
    kind: str
    dimensions: tuple[float, ...]

    def __post_init__(self):
        if type(self.kind) is not str or self.kind not in PRIMITIVES:
            raise NativeError("Unsupported primitive")
        if (type(self.dimensions) is not tuple
                or len(self.dimensions) != len(PRIMITIVES[self.kind])
                or any(type(v) not in (int,float) or not isfinite(v)
                       or not MIN_LENGTH < v <= MAX_LENGTH for v in self.dimensions)):
            raise NativeError("Invalid primitive dimensions")

    def append_to(self, document, *, expected_revision=None, cancelled=None):
        if not isinstance(document,NativeDocument):
            raise NativeError("Expected native document")
        revision = document.revision if expected_revision is None else expected_revision
        used = set(document.node_ids)
        suffix = 1
        while True:
            body = self.kind if suffix == 1 else f"{self.kind}_{suffix}"
            names = tuple(f"{body}_{name}" for name in PRIMITIVES[self.kind])
            if body not in used and not used.intersection(names):
                break
            suffix += 1
        return document.append_features(dict(zip(names,self.dimensions)),
                  (Feature(body,self.kind,names),),expected_revision=revision,cancelled=cancelled)

    def build(self):
        names = PRIMITIVES[self.kind]
        return NativeDocument(dict(zip(names,self.dimensions)),
                              (Feature(self.kind,self.kind,names),))


@dataclass(frozen=True, slots=True)
class BooleanSpec:
    kind: str
    left: str
    right: str

    def __post_init__(self):
        if type(self.kind) is not str or self.kind not in ("union","cut","common"):
            raise NativeError("Unsupported Boolean operation")
        if (type(self.left) is not str or type(self.right) is not str
                or not self.left or not self.right or self.left == self.right):
            raise NativeError("Select two distinct bodies")

    def append_to(self, document, *, expected_revision=None, cancelled=None):
        if not isinstance(document,NativeDocument):
            raise NativeError("Expected native document")
        revision = document.revision if expected_revision is None else expected_revision
        used = set(document.node_ids)
        suffix = 1
        while True:
            body = self.kind if suffix == 1 else f"{self.kind}_{suffix}"
            if body not in used:
                break
            suffix += 1
        return document.append_features({},(Feature(body,self.kind,(self.left,self.right)),),
                                        expected_revision=revision,cancelled=cancelled)
