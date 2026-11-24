"""Version 3 closed curve-region schema; every scalar refers to a DAG input."""
from dataclasses import dataclass
from goosecad.geometry.curves import Curve, ARITY, MAX_LOOPS, MAX_EDGES, make_region
from goosecad.parametric import Operation

@dataclass(frozen=True, slots=True)
class CurveSpec:
    kind: str
    coordinates: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class RegionSpec:
    id: str
    loops: tuple[tuple[CurveSpec, ...], ...]

    def dependencies(self):
        return tuple(dict.fromkeys(p for loop in self.loops for c in loop for p in c.coordinates))

    def operation(self):
        deps=self.dependencies(); index={n:i for i,n in enumerate(deps)}
        loops=tuple(tuple((c.kind,tuple(index[p] for p in c.coordinates)) for c in loop) for loop in self.loops)
        return Operation(self.id,deps,lambda *values: make_region(tuple(tuple(Curve(k,tuple(values[i] for i in ids)) for k,ids in loop) for loop in loops)))


def region_payload(s):
    return {'id':s.id,'loops':[[{'kind':c.kind,'coordinates':list(c.coordinates)} for c in loop] for loop in s.loops]}


def parse_region(row,params,identifier,error):
    if type(row) is not dict or set(row)!={'id','loops'}: raise error('Invalid curve region record')
    name=identifier(row['id']); loops=row['loops']
    if type(loops) is not list or not 1<=len(loops)<=MAX_LOOPS or any(type(loop) is not list or not loop for loop in loops) or sum(map(len,loops))>MAX_EDGES:
        raise error('Invalid region size')
    parsed=[]
    for loop in loops:
        curves=[]
        for c in loop:
            if type(c) is not dict or set(c)!={'kind','coordinates'}: raise error('Invalid curve record')
            k,p=c['kind'],c['coordinates']
            if type(k) is not str or k not in ARITY or type(p) is not list or len(p)!=ARITY[k]: raise error('Invalid curve kind or arity')
            p=tuple(identifier(v) for v in p)
            if any(v not in params for v in p): raise error('Missing curve parameter')
            curves.append(CurveSpec(k,p))
        if (len(curves)==1)!=(curves[0].kind=='circle') or (len(curves)>1 and any(c.kind=='circle' for c in curves)):
            raise error('Circle must be a separate loop')
        parsed.append(tuple(curves))
    return RegionSpec(name,tuple(parsed))
