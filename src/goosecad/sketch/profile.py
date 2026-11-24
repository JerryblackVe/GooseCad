"""Connect the point solver to an ordered closed polygon; no UI or disk schema yet."""
from dataclasses import dataclass
from goosecad.constraints.solver import solve
from goosecad.geometry.sweep import validate_polygon
from goosecad.geometry.kernel import GeometryError

@dataclass(frozen=True,slots=True)
class SolvedProfile:
    vertices: tuple[tuple[float,float],...]
    dof: int
    max_residual: float

def solve_profile(points,constraints,order):
    if type(order) not in (tuple,list) or any(type(n) is not str for n in order) or len(set(order))!=len(order):
        raise GeometryError('Invalid profile order')
    result=solve(points,constraints)
    if result.status!='solved': raise GeometryError('Sketch not solved: '+result.status)
    if set(order)!=set(result.points): raise GeometryError('Profile must contain all solved points exactly once')
    return SolvedProfile(validate_polygon(tuple(result.points[n] for n in order)),result.dof,result.max_residual)
