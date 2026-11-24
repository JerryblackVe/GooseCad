"""Session-local LRU for display snapshots, not authoritative B-Rep.

A cache binds one document instance: reload/recovery must create a new cache.
Node stamps are published atomically by the DAG. Returned snapshots can become
obsolete after return; consumers must compare stamps before presenting/picking.
Cache locks never enclose document calls or native meshing. Concurrent misses
may duplicate work; callers must obey the graph's borrowed-read-only contract.
The byte budget counts retained mesh arrays and face offsets, not OCCT, GPU,
external references or all Python allocator overhead. Entry count bounds metadata.
"""
from collections import OrderedDict
from dataclasses import dataclass
from math import pi
from sys import getsizeof
from threading import RLock
import numpy as np
from OCP.TopoDS import TopoDS_Shape
from goosecad.document.native import NativeDocument
from .kernel import GeometryError
from .mesh import DisplayMesh, tessellate, MAX_VERTICES, MAX_TRIANGLES

@dataclass(frozen=True, slots=True)
class MeshSettings:
    linear: float = .1
    angular: float = .5
    parallel: bool = False
    max_vertices: int = MAX_VERTICES
    max_triangles: int = MAX_TRIANGLES
    def __post_init__(self):
        if type(self.linear) not in (int,float) or not .01 <= self.linear <= 1e6 or type(self.angular) not in (int,float) or not .1 <= self.angular <= pi/2 or type(self.parallel) is not bool:
            raise GeometryError('Invalid mesh settings')
        if type(self.max_vertices) is not int or not 0 < self.max_vertices <= MAX_VERTICES or type(self.max_triangles) is not int or not 0 < self.max_triangles <= MAX_TRIANGLES:
            raise GeometryError('Invalid mesh budget')

@dataclass(frozen=True, slots=True)
class MeshSnapshot:
    body: str
    revision: int
    settings: MeshSettings
    mesh: DisplayMesh
    _owner: object

@dataclass(frozen=True, slots=True)
class CacheInfo:
    entries: int
    bytes: int
    hits: int
    misses: int
    evictions: int


def _immutable(mesh):
    # NumPy's write=False alone is reversible on owning arrays. A bytes owner
    # makes cached buffers genuinely read-only, even through setflags().
    v=np.frombuffer(mesh.vertices.tobytes(),dtype=np.float64).reshape(mesh.vertices.shape)
    t=np.frombuffer(mesh.triangles.tobytes(),dtype=np.uint32).reshape(mesh.triangles.shape)
    return DisplayMesh(v,t,mesh.face_offsets)


def mesh_bytes(mesh):
    return mesh.vertices.nbytes+mesh.triangles.nbytes+getsizeof(mesh.face_offsets)+sum(getsizeof(x) for x in mesh.face_offsets)


class MeshCache:
    def __init__(self, document: NativeDocument, *, max_bytes=64*1024*1024, max_entries=256):
        if not isinstance(document,NativeDocument) or type(max_bytes) is not int or max_bytes<0 or type(max_entries) is not int or max_entries<0:
            raise GeometryError('Invalid mesh cache configuration')
        self._document=document; self._max_bytes=max_bytes; self._max_entries=max_entries
        self._entries=OrderedDict(); self._bytes=self._hits=self._misses=self._evictions=0
        self._lock=RLock(); self._epoch=0; self._owner=object()

    @property
    def document(self):
        return self._document

    def info(self):
        with self._lock: return CacheInfo(len(self._entries),self._bytes,self._hits,self._misses,self._evictions)

    def clear(self):
        with self._lock:
            self._entries.clear(); self._bytes=0; self._epoch+=1

    def is_current(self, snapshot):
        # Identity of the cache/document is encoded by the snapshot owner check
        # in the viewer; a snapshot from another cache is not accepted here.
        if type(snapshot) is not MeshSnapshot or snapshot._owner is not self._owner: return False
        try:
            revision,_=self._document.versioned_value(snapshot.body)
        except KeyError:
            return False
        return revision==snapshot.revision

    def get(self, body, settings=MeshSettings()):
        if type(body) is not str or type(settings) is not MeshSettings: raise GeometryError('Invalid mesh request')
        revision,shape=self._document.versioned_value(body)
        if not isinstance(shape,TopoDS_Shape): raise GeometryError('Node is not a B-Rep body')
        key=(body,revision,settings)
        with self._lock:
            epoch=self._epoch
            if key in self._entries:
                self._hits+=1; self._entries.move_to_end(key); return self._entries[key][0]
            self._misses+=1
        mesh=_immutable(tessellate(shape,linear=settings.linear,angular=settings.angular,parallel=settings.parallel,max_vertices=settings.max_vertices,max_triangles=settings.max_triangles))
        snapshot=MeshSnapshot(body,revision,settings,mesh,self._owner); cost=mesh_bytes(mesh)
        current,_=self._document.versioned_value(body)
        with self._lock:
            if epoch!=self._epoch or current!=revision or not self._max_entries or cost>self._max_bytes: return snapshot
            if key in self._entries:
                self._entries.move_to_end(key); return self._entries[key][0]
            for old in tuple(self._entries):
                if old[0]==body and old[1]<revision:
                    _,n=self._entries.pop(old); self._bytes-=n; self._evictions+=1
            while self._entries and (len(self._entries)>=self._max_entries or self._bytes+cost>self._max_bytes):
                _,(_,n)=self._entries.popitem(last=False); self._bytes-=n; self._evictions+=1
            self._entries[key]=(snapshot,cost); self._bytes+=cost
        return snapshot
