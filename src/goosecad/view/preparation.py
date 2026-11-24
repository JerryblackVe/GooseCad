"""CPU-only scene preparation. Never creates or accesses Qt/VTK objects.

Plans are captured on the scene owner; the worker consumes immutable display
snapshots and the thread-safe document/cache under exclusive document access.
Cancellation does not roll back geometry; it only discards prepared display data.
"""
from dataclasses import dataclass
from goosecad.geometry.mesh_cache import MeshCache, MeshSettings, MeshSnapshot
from goosecad.document.native import NativeDocument
from goosecad.parametric import Cancelled


class ViewError(RuntimeError):
    pass


def terminal_bodies(document):
    consumed = {dep for feature in document.features for dep in feature.dependencies}
    return tuple(f.id for f in document.features if f.id not in consumed)


@dataclass(frozen=True, slots=True)
class DisplayConfig:
    settings: MeshSettings = MeshSettings()
    max_vertices: int = 1_000_000
    max_triangles: int = 2_000_000

    def __post_init__(self):
        if (type(self.settings) is not MeshSettings
                or type(self.max_vertices) is not int
                or type(self.max_triangles) is not int
                or min(self.max_vertices,self.max_triangles)<1):
            raise ViewError("Invalid scene configuration")

    def initial_request(self, document):
        return MeshRequest(document, MeshCache(document), document.revision,
                           terminal_bodies(document), self.settings, (),
                           self.max_vertices, self.max_triangles)


@dataclass(frozen=True, slots=True)
class MeshRequest:
    document: NativeDocument
    cache: MeshCache
    revision: int
    bodies: tuple[str, ...]
    settings: MeshSettings
    reusable: tuple[MeshSnapshot, ...]
    max_vertices: int
    max_triangles: int

    def __post_init__(self):
        DisplayConfig(self.settings,self.max_vertices,self.max_triangles)
        if (self.cache.document is not self.document
                or type(self.bodies) is not tuple or len(self.bodies)>256
                or any(type(b) is not str for b in self.bodies)
                or len(set(self.bodies))!=len(self.bodies)):
            raise ViewError("Invalid scene request")

    def prepare(self, *, cancelled=None):
        def check():
            if cancelled is not None and cancelled():
                raise Cancelled("Display preparation cancelled")
            if self.document.revision != self.revision:
                raise ViewError("Document changed during scene preparation")
        check()
        old = {snapshot.body: snapshot for snapshot in self.reusable}
        snapshots = []
        nv = nt = 0
        for body in self.bodies:
            check()
            snapshot = old.get(body)
            if (snapshot is None or snapshot.settings != self.settings
                    or not self.cache.is_current(snapshot)):
                snapshot = self.cache.get(body, self.settings)
            nv += len(snapshot.mesh.vertices)
            nt += len(snapshot.mesh.triangles)
            if nv > self.max_vertices or nt > self.max_triangles:
                raise ViewError("Scene output budget exceeded")
            snapshots.append(snapshot)
        check()
        prepared = PreparedMeshes(self, tuple(snapshots))
        prepared.validate()
        return prepared


@dataclass(frozen=True, slots=True)
class PreparedMeshes:
    request: MeshRequest
    snapshots: tuple[MeshSnapshot, ...]

    def validate(self):
        plan = self.request
        if plan.document.revision != plan.revision:
            raise ViewError("Prepared display is stale")
        if tuple(s.body for s in self.snapshots) != plan.bodies:
            raise ViewError("Invalid prepared body list")
        nv = nt = 0
        for s in self.snapshots:
            if s.settings != plan.settings or not plan.cache.is_current(s):
                raise ViewError("Prepared display snapshot is stale or foreign")
            nv += len(s.mesh.vertices)
            nt += len(s.mesh.triangles)
        if nv > plan.max_vertices or nt > plan.max_triangles:
            raise ViewError("Scene output budget exceeded")
