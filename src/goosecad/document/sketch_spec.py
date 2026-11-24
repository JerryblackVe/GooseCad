"""Version 2 declarative sketch records. All coordinates and targets reference inputs."""
from dataclasses import dataclass
from goosecad.constraints.solver import Constraint, MAX_POINTS, MAX_CONSTRAINTS, TOL
from goosecad.sketch.profile import solve_profile
from goosecad.parametric import Operation

@dataclass(frozen=True, slots=True)
class PointSpec:
    id: str
    x: str
    y: str

@dataclass(frozen=True, slots=True)
class ConstraintSpec:
    id: str
    kind: str
    a: str
    b: str | None = None
    targets: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class SketchSpec:
    id: str
    points: tuple[PointSpec, ...]
    constraints: tuple[ConstraintSpec, ...] = ()

    def dependencies(self):
        return tuple(dict.fromkeys([v for p in self.points for v in (p.x,p.y)] +
                                   [v for c in self.constraints for v in c.targets]))

    def operation(self):
        deps=self.dependencies(); index={v:i for i,v in enumerate(deps)}
        # Compile positional indices once, not on each parameter change.
        points=tuple((p.id,index[p.x],index[p.y]) for p in self.points)
        constraints=tuple((c.kind,c.a,c.b,tuple(index[t] for t in c.targets)) for c in self.constraints)
        order=tuple(p.id for p in self.points)
        def compute(*values):
            coords={n:(values[x],values[y]) for n,x,y in points}
            cs=tuple(Constraint(k,a,b,tuple(values[i] for i in t) if k=='fix' else values[t[0]] if k=='distance' else None)
                     for k,a,b,t in constraints)
            return solve_profile(coords,cs,order)
        return Operation(self.id,deps,compute)


def sketch_payload(s):
    return {'id':s.id,'points':[{'id':p.id,'x':p.x,'y':p.y} for p in s.points],
            'constraints':[{'id':c.id,'kind':c.kind,'a':c.a,'b':c.b,'targets':list(c.targets)} for c in s.constraints]}


def parse_sketch(row, params, identifier, error):
    if type(row) is not dict or set(row)!={'id','points','constraints'}:
        raise error('Invalid sketch record')
    name=identifier(row['id']); points=row['points']; constraints=row['constraints']
    if type(points) is not list or not 3<=len(points)<=MAX_POINTS or type(constraints) is not list or len(constraints)>MAX_CONSTRAINTS:
        raise error('Invalid sketch point or constraint count')
    ps=[]; names=set()
    for p in points:
        if type(p) is not dict or set(p)!={'id','x','y'}: raise error('Invalid point record')
        n,x,y=(identifier(p[k]) for k in ('id','x','y'))
        if n in names or x not in params or y not in params: raise error('Duplicate point or missing coordinate parameter')
        names.add(n); ps.append(PointSpec(n,x,y))
    cs=[]; ids=set()
    for c in constraints:
        if type(c) is not dict or set(c)!={'id','kind','a','b','targets'}: raise error('Invalid constraint record')
        n,a=identifier(c['id']),identifier(c['a']); k,b,t=c['kind'],c['b'],c['targets']
        if n in ids or a not in names or type(k) is not str or type(t) is not list: raise error('Invalid constraint identity')
        ids.add(n)
        if k=='fix':
            if b is not None or len(t)!=2: raise error('Fix requires two targets and no second point')
        else:
            if k not in ('horizontal','vertical','coincident','distance') or type(b) is not str or b not in names or b==a:
                raise error('Invalid pair constraint')
            if len(t)!=(1 if k=='distance' else 0): raise error('Invalid target arity')
        t=tuple(identifier(v) for v in t)
        if any(v not in params for v in t): raise error('Unknown target parameter')
        if k=='distance' and params[t[0]]<=TOL: raise error('Distance target must exceed solver tolerance')
        cs.append(ConstraintSpec(n,k,a,b,t))
    return SketchSpec(name,tuple(ps),tuple(cs))
