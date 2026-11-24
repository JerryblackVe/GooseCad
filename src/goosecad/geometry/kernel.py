"""Native OCCT operations via OCP. Units: mm, mm², mm³. No mesh approximation."""
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeSphere
from OCP.GProp import GProp_GProps
from OCP.Precision import Precision
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape, TopTools_ListOfShape
from OCP.TopoDS import TopoDS_Shape
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location

MIN_LENGTH = Precision.Confusion_s()
# Conservative experimental domain; not an OCCT-wide limit.
MAX_LENGTH = 1e6

class GeometryError(ValueError):
    """Input or kernel result violates the current geometry contract."""

@dataclass(frozen=True)
class Properties:
    volume: float
    area: float
    center: tuple[float, float, float] | None
    solids: int


def _dimension(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not MIN_LENGTH < value <= MAX_LENGTH:
        raise GeometryError("Dimension must be finite, above OCCT confusion and at most 1e6 mm")
    return float(value)


def _point(origin: tuple[float, float, float]) -> gp_Pnt:
    if len(origin) != 3 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not -MAX_LENGTH <= x <= MAX_LENGTH for x in origin):
        raise GeometryError("Origin must contain three finite coordinates within ±1e6 mm")
    return gp_Pnt(*origin)


def _solid_count(shape: TopoDS_Shape) -> int:
    shapes = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_SOLID, shapes)
    return shapes.Extent()


def _validate(shape: TopoDS_Shape, *, allow_empty: bool = False) -> TopoDS_Shape:
    if shape.IsNull() or not BRepCheck_Analyzer(shape).IsValid():
        raise GeometryError("Null or invalid B-Rep")
    if not allow_empty and not _solid_count(shape):
        raise GeometryError("Expected at least one solid")
    return shape


def _primitive(builder) -> TopoDS_Shape:
    builder.Build()
    if not builder.IsDone():
        raise GeometryError("OCCT primitive failed")
    return _validate(builder.Shape())


def box(x: float, y: float, z: float, origin=(0., 0., 0.)) -> TopoDS_Shape:
    return _primitive(BRepPrimAPI_MakeBox(_point(origin), _dimension(x), _dimension(y), _dimension(z)))


def cylinder(radius: float, height: float, origin=(0., 0., 0.)) -> TopoDS_Shape:
    return _primitive(BRepPrimAPI_MakeCylinder(gp_Ax2(_point(origin), gp_Dir(0, 0, 1)), _dimension(radius), _dimension(height)))


def sphere(radius: float, origin=(0., 0., 0.)) -> TopoDS_Shape:
    return _primitive(BRepPrimAPI_MakeSphere(_point(origin), _dimension(radius)))


def translate(shape: TopoDS_Shape, dx: float, dy: float, dz: float) -> TopoDS_Shape:
    """Exact rigid B-Rep placement; offset components in mm within ±1e6.

    New location shares underlying topology under the borrowed-read-only
    contract; never mutates the source or tessellates. Empty compounds remain
    valid. The offset bound is per operation, not a global workspace bound.
    """
    if not isinstance(shape, TopoDS_Shape):
        raise GeometryError("Expected B-Rep shape")
    if any(type(v) not in (int,float) or not isfinite(v)
           or not -MAX_LENGTH <= v <= MAX_LENGTH for v in (dx,dy,dz)):
        raise GeometryError("Translation must contain finite offsets within ±1e6 mm")
    _validate(shape,allow_empty=True)
    if dx == dy == dz == 0:
        return shape
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(dx,dy,dz))
    result = shape.Moved(TopLoc_Location(transform))
    return _validate(result,allow_empty=True)


def properties(shape: TopoDS_Shape) -> Properties:
    _validate(shape, allow_empty=True)
    return _properties_validated(shape)


def _properties_validated(shape: TopoDS_Shape) -> Properties:
    count = _solid_count(shape)
    v, a = GProp_GProps(), GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, v, True, True)
    BRepGProp.SurfaceProperties_s(shape, a, True)
    volume, area = v.Mass(), a.Mass()
    if not isfinite(volume) or not isfinite(area) or volume < 0 or area < 0:
        raise GeometryError("Invalid mass properties")
    if count and volume <= 0:
        raise GeometryError("Solid must have positive volume")
    center = v.CentreOfMass().Coord() if volume > 0 else None
    return Properties(volume, area, center, count)


def boolean(kind: Literal['union', 'cut', 'common'], left: TopoDS_Shape, right: TopoDS_Shape, *, parallel: bool = False) -> TopoDS_Shape:
    """Only independent jobs; parallelism opt-in until benchmarked. Do not mutate inputs."""
    algorithms = {'union': BRepAlgoAPI_Fuse, 'cut': BRepAlgoAPI_Cut, 'common': BRepAlgoAPI_Common}
    if kind not in algorithms:
        raise GeometryError("Unknown Boolean operation")
    _validate(left)
    _validate(right)
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(left)
    tools.Append(right)
    op = algorithms[kind]()
    op.SetArguments(args)
    op.SetTools(tools)
    op.SetNonDestructive(True)
    op.SetRunParallel(parallel)
    op.Build()
    if not op.IsDone():
        raise GeometryError("OCCT Boolean failed")
    result = _validate(op.Shape(), allow_empty=True)
    # A zero-volume common/cut is a valid empty result, not a failed operation.
    _properties_validated(result)
    return result
