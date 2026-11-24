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
