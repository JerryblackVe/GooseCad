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

    def build(self):
        names = PRIMITIVES[self.kind]
        return NativeDocument(dict(zip(names,self.dimensions)),
                              (Feature(self.kind,self.kind,names),))
