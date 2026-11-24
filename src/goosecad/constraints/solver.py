"""Experimental planar point solver; deterministic analytic residual/Jacobian.

Linear constraints use least-squares correction; nonlinear distance uses TRF.
Degrees of freedom and dependent equations are *local* Jacobian rank estimates.
An unsuccessful nonlinear solve is not proof of inconsistency. No mutation of inputs.
"""
from dataclasses import dataclass
from math import isfinite, fsum
import numpy as np
from scipy.optimize import least_squares

MAX_POINTS=256
MAX_CONSTRAINTS=512
TOL=1e-7  # mm, fixed in this experiment
RANK_TOL=1e-9

class SolverError(ValueError): pass

@dataclass(frozen=True,slots=True)
class Constraint:
    kind: str
    a: str
    b: str | None = None
    value: float | tuple[float,float] | None = None

@dataclass(frozen=True,slots=True)
class SolveResult:
    status: str
    points: dict[str,tuple[float,float]] | None
    dof: int | None
    dependent_rows: int | None
    max_residual: float


def _num(v):
    if type(v) not in (int,float) or not -1e6<=v<=1e6 or not isfinite(v): raise SolverError('Invalid coordinate or distance')
    return float(v)


def _validate(points,constraints):
    if type(points) is not dict or not 0<len(points)<=MAX_POINTS: raise SolverError('Invalid point count')
    coords={}
    for name,p in points.items():
        if type(name) is not str or not name or type(p) not in (tuple,list) or len(p)!=2: raise SolverError('Invalid point')
        coords[name]=tuple(_num(v) for v in p)
    cs=tuple(constraints)
    if len(cs)>MAX_CONSTRAINTS: raise SolverError('Too many constraints')
    for c in cs:
        if type(c) is not Constraint or type(c.kind) is not str or type(c.a) is not str or c.a not in coords: raise SolverError('Invalid constraint')
        if c.kind=='fix':
            if c.b is not None or type(c.value) not in (list,tuple) or len(c.value)!=2: raise SolverError('Fix requires a point target')
            tuple(_num(v) for v in c.value)
        else:
            if c.kind not in ('horizontal','vertical','coincident','distance') or type(c.b) is not str or c.b not in coords or c.a==c.b: raise SolverError('Invalid pair constraint')
            if c.kind=='distance':
                if _num(c.value)<=TOL: raise SolverError('Use coincidence for zero distance')
            elif c.value is not None: raise SolverError('Unexpected constraint value')
    return coords,cs


def _component(coords,cs):
    if not cs: return 'solved',dict(coords),2*len(coords),0,0.
    names=tuple(coords); idx={n:2*i for i,n in enumerate(names)}; x=np.array([v for p in coords.values() for v in p],dtype=float)
    rows=[]; targets=[]; distances=[]
    for c in cs:
        a=idx[c.a]; b=idx[c.b] if c.b is not None else None
        if c.kind=='distance': distances.append((a,b,float(c.value))); continue
        axes=(0,1) if c.kind in ('fix','coincident') else (1,) if c.kind=='horizontal' else (0,)
        for axis in axes:
            row=np.zeros(len(x)); row[a+axis]=1
            if b is not None: row[b+axis]=-1
            rows.append(row); targets.append(float(c.value[axis]) if c.kind=='fix' else 0.)
    A=np.array(rows).reshape((-1,len(x))); t=np.array(targets)
    if len(A):
        delta,_,rank,_=np.linalg.lstsq(A,t-A@x,rcond=RANK_TOL); x=x+delta
        linear_error=float(np.max(np.abs(A@x-t)))
        if linear_error>TOL: return 'inconsistent_linear',None,None,None,linear_error
    else: rank=0
    if not distances:
        if not np.all(np.isfinite(x)) or np.any(np.abs(x)>1e6): return 'unresolved',None,None,None,float('inf')
        return 'solved',dict(zip(names,(tuple(map(float,p)) for p in x.reshape(-1,2)))),len(x)-int(rank),len(A)-int(rank),float(np.max(np.abs(A@x-t),initial=0.))
    def residual(y):
        return np.concatenate((A@y-t,np.array([np.linalg.norm(y[a:a+2]-y[b:b+2])-d for a,b,d in distances])))
    def jac(y):
        J=np.zeros((len(A)+len(distances),len(y))); J[:len(A)]=A
        for i,(a,b,_) in enumerate(distances,len(A)):
            v=y[a:a+2]-y[b:b+2]; norm=np.linalg.norm(v)
            if norm>1e-14: J[i,a:a+2]=v/norm; J[i,b:b+2]=-v/norm
        return J
    if any(np.linalg.norm(x[a:a+2]-x[b:b+2])<=1e-14 for a,b,d in distances):
        return 'unresolved',None,None,None,float(np.max(np.abs(residual(x))))
    fit=least_squares(residual,x,jac=jac,method='trf',ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=200)
    err=float(np.max(np.abs(residual(fit.x))))
    if not np.all(np.isfinite(fit.x)) or np.any(np.abs(fit.x)>1e6) or err>TOL: return 'unresolved',None,None,None,err
    rank=int(np.linalg.matrix_rank(jac(fit.x),tol=RANK_TOL))
    return 'solved',dict(zip(names,(tuple(map(float,p)) for p in fit.x.reshape(-1,2)))),len(x)-rank,len(A)+len(distances)-rank,err



def _linear_equalities(coords,cs):
    """Exact equality components on scalar coordinates; no dense matrix.

    Conflicting anchor targets fall back to the numerical diagnostic path.
    Unanchored groups use the orthogonal projection (mean of initial values).
    """
    parent={(n,i):(n,i) for n in coords for i in (0,1)}
    def root(k):
        while parent[k]!=k:
            parent[k]=parent[parent[k]]; k=parent[k]
        return k
    pins=[]; equations=0
    for c in cs:
        axes=(0,1) if c.kind in ('fix','coincident') else (1,) if c.kind=='horizontal' else (0,)
        for axis in axes:
            equations+=1
            if c.kind=='fix': pins.append(((c.a,axis),float(c.value[axis])))
            else: parent[root((c.b,axis))]=root((c.a,axis))
    fixed={}
    for key,v in pins:
        k=root(key)
        if k in fixed and fixed[k]!=v: return None
        fixed[k]=v
    groups={}
    for n,i in parent: groups.setdefault(root((n,i)),[]).append(coords[n][i])
    solution={k:fixed[k] if k in fixed else fsum(v)/len(v) for k,v in groups.items()}
    dof=len(groups)-len(fixed); rank=len(parent)-dof
    return SolveResult('solved',{n:(solution[root((n,0))],solution[root((n,1))]) for n in coords},dof,equations-rank,0.)


def solve(points,constraints,*,partition=True):
    """Solve components independently; partition=False is a benchmark baseline."""
    coords,cs=_validate(points,constraints)
    if not partition: return SolveResult(*_component(coords,cs))
    if all(c.kind!='distance' for c in cs):
        direct=_linear_equalities(coords,cs)
        if direct is not None: return direct
    parent={n:n for n in coords}
    def root(n):
        while parent[n]!=n:
            parent[n]=parent[parent[n]]; n=parent[n]
        return n
    for c in cs:
        if c.b is not None: parent[root(c.b)]=root(c.a)
    groups={}; sub={}
    for n,p in coords.items(): groups.setdefault(root(n),{})[n]=p
    for c in cs: sub.setdefault(root(c.a),[]).append(c)
    result={}; dof=dep=0; error=0.
    for k,g in groups.items():
        status,p,d,r,e=_component(g,sub.get(k,()))
        if status!='solved': return SolveResult(status,None,None,None,e)
        result.update(p); dof+=d; dep+=r; error=max(error,e)
    return SolveResult('solved',result,dof,dep,error)
