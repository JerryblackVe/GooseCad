"""Experimental native formats v1/v2: declarative, checksummed, bounded JSON.

Single writer per path (external coordination required). No untrusted callbacks,
no pickle, no arbitrary B-Rep payloads. Native evaluation is not sandboxed.
"""
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
import json
import os
from pathlib import Path
import stat
import tempfile
from threading import RLock

from goosecad.document.document import Document, DocumentError
from goosecad.parametric import Input, Operation
from goosecad.geometry.kernel import box, cylinder, sphere, boolean

from goosecad.document.sketch_spec import SketchSpec, PointSpec, ConstraintSpec, sketch_payload, parse_sketch
from goosecad.geometry.sweep import extrude, revolve

MAX_BYTES = 2 * 1024 * 1024
MAX_NODES = 2048
MAX_ID = 128
FORMAT = 'GooseCAD'
VERSION = 2
SUPPORTED_VERSIONS = (1, 2)
MAX_SKETCH_ITEMS = 8192
# Closed, trusted operations; type/arity checked before native evaluation.
_REGISTRY = {
    'box': (('number',)*3, 'shape', box),
    'cylinder': (('number',)*2, 'shape', cylinder),
    'sphere': (('number',), 'shape', sphere),
    'union': (('shape',)*2, 'shape', lambda a,b: boolean('union',a,b)),
    'cut': (('shape',)*2, 'shape', lambda a,b: boolean('cut',a,b)),
    'common': (('shape',)*2, 'shape', lambda a,b: boolean('common',a,b)),
}

_SWEEPS = {
    'extrude': (('profile','number'), 'shape', lambda p,h: extrude(p.vertices,h)),
    'revolve': (('profile','number'), 'shape', lambda p,a: revolve(p.vertices,a)),
}

def _registry(version):
    return _REGISTRY if version==1 else {**_REGISTRY,**_SWEEPS}

class NativeError(DocumentError): pass
class UnsupportedVersion(NativeError): pass

@dataclass(frozen=True, slots=True)
class Feature:
    id: str
    kind: str
    dependencies: tuple[str, ...]


def _number(v):
    if type(v) not in (int,float) or not -1e6 <= v <= 1e6 or not isfinite(v):
        raise NativeError('Expected finite numeric parameter within ±1e6')
    return v


def _id(v):
    if type(v) is not str or not 0 < len(v) <= MAX_ID or not v.isascii() or not all(c.isalnum() or c in '_-.' for c in v):
        raise NativeError('Invalid node identifier')
    return v


def _canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',',':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def _pairs(pairs):
    d = {}
    for k,v in pairs:
        if k in d: raise NativeError('Duplicate JSON key')
        d[k] = v
    return d


def _bad_constant(v): raise NativeError('Nonfinite JSON constant')


def _spec(payload, version=1):
    registry=_registry(version)
    keys={'parameters','features'} | ({'sketches'} if version==2 else set())
    if type(payload) is not dict or set(payload) != keys:
        raise NativeError('Invalid payload')
    params, rows = payload['parameters'], payload['features']
    sketches=payload.get('sketches',[])
    if type(sketches) is not list: raise NativeError('Invalid sketches collection')
    if type(params) is not dict or type(rows) is not list or len(params)+len(rows)+len(sketches)>MAX_NODES:
        raise NativeError('Invalid or oversized node collection')
    params = {_id(k): _number(v) for k,v in params.items()}
    types = dict.fromkeys(params,'number'); features = []; profiles=[]; total_items=0
    for row in sketches:
        sketch=parse_sketch(row,params,_id,NativeError)
        total_items+=len(sketch.points)+len(sketch.constraints)
        if total_items>MAX_SKETCH_ITEMS or sketch.id in types: raise NativeError('Sketch limit or duplicate node')
        types[sketch.id]='profile'; profiles.append(sketch)
    for row in rows:
        if type(row) is not dict or set(row) != {'id','kind','dependencies'}:
            raise NativeError('Invalid feature record')
        name, kind, deps = _id(row['id']), row['kind'], row['dependencies']
        if name in types or type(kind) is not str or kind not in registry or type(deps) is not list:
            raise NativeError('Duplicate identifier or unsupported operation')
        signature, result, _ = registry[kind]
        if len(deps)!=len(signature): raise NativeError('Invalid operation arity')
        deps = tuple(_id(d) for d in deps)
        if len(set(deps))!=len(deps): raise NativeError('Repeated dependency not supported')
        features.append(Feature(name,kind,deps)); types[name]=result
    for f in features:
        if tuple(types.get(d) for d in f.dependencies) != registry[f.kind][0]:
            raise NativeError('Unknown or incompatible dependency')
    # Check acyclicity before calling any OCCT function.
    from collections import deque
    successors = {n:[] for n in types}; degree = dict.fromkeys(types,0)
    for name,deps in [(f.id,f.dependencies) for f in features]+[(p.id,p.dependencies()) for p in profiles]:
        for d in deps: successors[d].append(name); degree[name]+=1
    queue=deque(n for n in types if not degree[n]); count=0
    while queue:
        n=queue.popleft(); count+=1
        for c in successors[n]:
            degree[c]-=1
            if degree[c]==0: queue.append(c)
    if count!=len(types): raise NativeError('Circular dependency')
    return params,tuple(features),tuple(profiles)


def _payload(params, features, sketches=(), version=1):
    result={'parameters':dict(params),'features':[{'id':f.id,'kind':f.kind,'dependencies':list(f.dependencies)} for f in features]}
    if version==2: result['sketches']=[sketch_payload(s) for s in sketches]
    return result


def _encode(payload, version=1):
    body={'format':FORMAT,'version':version,'payload':payload}
    encoded=_canonical({**body,'sha256':sha256(_canonical(body)).hexdigest()})+b'\n'
    if len(encoded)>MAX_BYTES: raise NativeError('Document too large')
    return encoded


def _decode(data):
    if len(data)>MAX_BYTES: raise NativeError('Document too large')
    try:
        envelope=json.loads(data.decode('utf-8'),object_pairs_hook=_pairs,parse_constant=_bad_constant)
        if type(envelope) is not dict or envelope.get('format')!=FORMAT:
            raise NativeError('Not a GooseCAD document')
        if type(envelope.get('version')) is not int or envelope['version'] not in SUPPORTED_VERSIONS:
            raise UnsupportedVersion('Unsupported native format version')
        if set(envelope)!={'format','version','payload','sha256'}: raise NativeError('Invalid envelope')
        digest=envelope.pop('sha256')
        if type(digest) is not str or digest!=sha256(_canonical(envelope)).hexdigest():
            raise NativeError('Checksum mismatch')
        version=envelope['version']
        return version,*_spec(envelope['payload'],version)
    except NativeError: raise
    except (ValueError,TypeError,OverflowError,RecursionError) as exc:
        raise NativeError('Malformed native document') from exc


class NativeDocument:
    """Closed-schema document; only parameters editable. History is session-only."""
    def __init__(self, parameters, features=(), *, sketches=(), version=None):
        sketches=tuple(sketches)
        if version is None: version=2 if sketches else 1
        if type(version) is not int or version not in SUPPORTED_VERSIONS: raise UnsupportedVersion('Unsupported native format version')
        if version==1 and sketches: raise NativeError('Sketches require format v2')
        params, features, sketches = _spec(_payload(parameters,features,sketches,version),version)
        self._initialize(version,params,features,sketches)

    def _initialize(self, version, params, features, sketches):
        self._version=version; self._sketches=sketches
        self._features=features; self._ids=tuple(params); registry=_registry(version)
        self._document=Document([*(Input(k,v) for k,v in params.items()),
          *(s.operation() for s in sketches),
          *(Operation(f.id,f.dependencies,registry[f.kind][2]) for f in features)])
        self._lock=RLock()

    @property
    def format_version(self): return self._version
    def upgraded(self):
        """Return independent v2 snapshot; session history is not transferred."""
        with self._lock:
            return NativeDocument({k:self._document.value(k) for k in self._ids},self._features,sketches=self._sketches,version=2)
    @property
    def revision(self): return self._document.revision
    def value(self,name): return self._document.value(name)
    def edit(self,changes,**kwargs):
        if type(changes) is not dict or any(type(k) is not str for k in changes):
            raise NativeError("Native edits require a plain dictionary of string identifiers")
        with self._lock: return self._document.edit({k:_number(v) for k,v in changes.items()},**kwargs)
    def undo(self,**kwargs):
        with self._lock: return self._document.undo(**kwargs)
    def redo(self,**kwargs):
        with self._lock: return self._document.redo(**kwargs)
    def to_bytes(self):
        with self._lock:
            # Read only input values, not a full graph snapshot or B-Rep copies.
            return _encode(_payload({k:self._document.value(k) for k in self._ids},self._features,self._sketches,self._version),self._version)
    @classmethod
    def from_bytes(cls,data):
        version,params,features,sketches=_decode(data)
        result=cls.__new__(cls)
        result._initialize(version,params,features,sketches)
        return result


def _check_path(path):
    # Reject symlinks and nonregular files. Not a defense against hostile directory races.
    try: mode=path.lstat().st_mode
    except FileNotFoundError: return False
    if not stat.S_ISREG(mode): raise NativeError('Expected regular document file')
    return True


def _read(path):
    if not _check_path(path): raise FileNotFoundError(path)
    with path.open('rb') as f: data=f.read(MAX_BYTES+1)
    return data


def _atomic(path,data):
    _check_path(path)
    fd,tmp=tempfile.mkstemp(prefix='.goosecad-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass


def _sync_dir(path):
    # POSIX directory durability. Windows directory fsync not portable.
    if os.name=='posix':
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
        try: os.fsync(fd)
        finally: os.close(fd)


def recovery_path(path):
    path=Path(path); return path.with_name(path.name+'.previous')


def save(document,path,*,allow_upgrade=False):
    """Atomic replacement; preserve previous validated bytes before replacing.

    A directory-fsync error after replace is reported; commit may have happened.
    Existing structurally invalid or unsupported-version primary is never overwritten.
    Migration v1 to v2 requires allow_upgrade=True; downgrade is rejected.
    """
    path=Path(path)
    if path.name.lower().endswith('.previous'):
        raise NativeError("Reserved recovery filename; choose a new primary path")
    data=document.to_bytes(); previous=recovery_path(path)
    if _check_path(path):
        old=_read(path); old_version,*_=_decode(old)
        if old_version!=document.format_version and not (old_version==1 and document.format_version==2 and allow_upgrade is True):
            raise NativeError('Format replacement requires explicit v1 to v2 upgrade; downgrade forbidden')
        _atomic(previous,old); _sync_dir(path.parent)
    _atomic(path,data); _sync_dir(path.parent)


def load(path):
    return NativeDocument.from_bytes(_read(Path(path)))


def recover(path):
    """Explicitly load previous revision into memory; never overwrite primary."""
    return load(recovery_path(path))
