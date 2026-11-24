"""Experimental native format v1: declarative, checksummed, bounded JSON.

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

MAX_BYTES = 2 * 1024 * 1024
MAX_NODES = 2048
MAX_ID = 128
FORMAT = 'GooseCAD'
VERSION = 1
# Closed, trusted operations; type/arity checked before native evaluation.
_REGISTRY = {
    'box': (('number',)*3, 'shape', box),
    'cylinder': (('number',)*2, 'shape', cylinder),
    'sphere': (('number',), 'shape', sphere),
    'union': (('shape',)*2, 'shape', lambda a,b: boolean('union',a,b)),
    'cut': (('shape',)*2, 'shape', lambda a,b: boolean('cut',a,b)),
    'common': (('shape',)*2, 'shape', lambda a,b: boolean('common',a,b)),
}

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


def _spec(payload):
    if type(payload) is not dict or set(payload) != {'parameters','features'}:
        raise NativeError('Invalid payload')
    params, rows = payload['parameters'], payload['features']
    if type(params) is not dict or type(rows) is not list or len(params)+len(rows)>MAX_NODES:
        raise NativeError('Invalid or oversized node collection')
    params = {_id(k): _number(v) for k,v in params.items()}
    types = dict.fromkeys(params,'number'); features = []
    for row in rows:
        if type(row) is not dict or set(row) != {'id','kind','dependencies'}:
            raise NativeError('Invalid feature record')
        name, kind, deps = _id(row['id']), row['kind'], row['dependencies']
        if name in types or type(kind) is not str or kind not in _REGISTRY or type(deps) is not list:
            raise NativeError('Duplicate identifier or unsupported operation')
        signature, result, _ = _REGISTRY[kind]
        if len(deps)!=len(signature): raise NativeError('Invalid operation arity')
        deps = tuple(_id(d) for d in deps)
        if len(set(deps))!=len(deps): raise NativeError('Repeated dependency not supported')
        features.append(Feature(name,kind,deps)); types[name]=result
    for f in features:
        if tuple(types.get(d) for d in f.dependencies) != _REGISTRY[f.kind][0]:
            raise NativeError('Unknown or incompatible dependency')
    # Check acyclicity before calling any OCCT function.
    from collections import deque
    successors = {n:[] for n in types}; degree = dict.fromkeys(types,0)
    for f in features:
        for d in f.dependencies: successors[d].append(f.id); degree[f.id]+=1
    queue=deque(n for n in types if not degree[n]); count=0
    while queue:
        n=queue.popleft(); count+=1
        for c in successors[n]:
            degree[c]-=1
            if degree[c]==0: queue.append(c)
    if count!=len(types): raise NativeError('Circular dependency')
    return params,tuple(features)


def _payload(params, features):
    return {'parameters':dict(params),'features':[{'id':f.id,'kind':f.kind,'dependencies':list(f.dependencies)} for f in features]}


def _encode(payload):
    body={'format':FORMAT,'version':VERSION,'payload':payload}
    encoded=_canonical({**body,'sha256':sha256(_canonical(body)).hexdigest()})+b'\n'
    if len(encoded)>MAX_BYTES: raise NativeError('Document too large')
    return encoded


def _decode(data):
    if len(data)>MAX_BYTES: raise NativeError('Document too large')
    try:
        envelope=json.loads(data.decode('utf-8'),object_pairs_hook=_pairs,parse_constant=_bad_constant)
        if type(envelope) is not dict or envelope.get('format')!=FORMAT:
            raise NativeError('Not a GooseCAD document')
        if type(envelope.get('version')) is not int or envelope['version']!=VERSION:
            raise UnsupportedVersion('Unsupported native format version')
        if set(envelope)!={'format','version','payload','sha256'}: raise NativeError('Invalid envelope')
        digest=envelope.pop('sha256')
        if type(digest) is not str or digest!=sha256(_canonical(envelope)).hexdigest():
            raise NativeError('Checksum mismatch')
        return _spec(envelope['payload'])
    except NativeError: raise
    except (ValueError,TypeError,OverflowError,RecursionError) as exc:
        raise NativeError('Malformed native document') from exc


class NativeDocument:
    """Closed-schema document; only parameters editable. History is session-only."""
    def __init__(self, parameters, features=()):
        params, features = _spec(_payload(parameters,features))
        self._initialize(params,features)

    def _initialize(self, params, features):
        self._features=features; self._ids=tuple(params)
        self._document=Document([*(Input(k,v) for k,v in params.items()),
          *(Operation(f.id,f.dependencies,_REGISTRY[f.kind][2]) for f in features)])
        self._lock=RLock()

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
            return _encode(_payload({k:self._document.value(k) for k in self._ids},self._features))
    @classmethod
    def from_bytes(cls,data):
        params,features=_decode(data)
        result=cls.__new__(cls)
        result._initialize(params,features)
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


def save(document,path):
    """Atomic replacement; preserve previous validated bytes before replacing.

    A directory-fsync error after replace is reported; commit may have happened.
    Existing invalid/newer-format primary is never overwritten by this API.
    """
    path=Path(path)
    if path.name.lower().endswith('.previous'):
        raise NativeError("Reserved recovery filename; choose a new primary path")
    data=document.to_bytes(); previous=recovery_path(path)
    if _check_path(path):
        old=_read(path); _decode(old)
        _atomic(previous,old); _sync_dir(path.parent)
    _atomic(path,data); _sync_dir(path.parent)


def load(path):
    return NativeDocument.from_bytes(_read(Path(path)))


def recover(path):
    """Explicitly load previous revision into memory; never overwrite primary."""
    return load(recovery_path(path))
