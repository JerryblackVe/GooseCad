"""Experimental VTK scene; all methods on creating thread. Face IDs are local.

Refresh explicitly after document edits. Picking rejects stale snapshots.
VTK owns copied buffers; these are additional to MeshCache's budget.
"""
from bisect import bisect_right
from dataclasses import dataclass
from threading import get_ident
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray
from goosecad.geometry.mesh_cache import MeshCache,MeshSettings

from goosecad.view.preparation import MeshRequest, PreparedMeshes, ViewError

@dataclass(frozen=True,slots=True)
class Selection:
    body: str
    revision: int
    face: int
    triangle: int


def polydata(mesh):
    p=vtk.vtkPoints();p.SetData(numpy_to_vtk(mesh.vertices,deep=True))
    cells=vtk.vtkCellArray();ids=mesh.triangles.astype(np.int64 if vtk.vtkIdTypeArray().GetDataTypeSize()==8 else np.int32,copy=False).ravel()
    offsets=np.arange(0,len(ids)+1,3,dtype=ids.dtype)
    cells.SetData(numpy_to_vtkIdTypeArray(offsets,deep=True),numpy_to_vtkIdTypeArray(ids,deep=True))
    d=vtk.vtkPolyData();d.SetPoints(p);d.SetPolys(cells);return d

class Scene:
    def __init__(self,document,*,offscreen=False,size=(800,600),settings=MeshSettings(),max_vertices=1_000_000,max_triangles=2_000_000,render_window=None):
        if type(max_vertices) is not int or type(max_triangles) is not int or min(max_vertices,max_triangles)<1:raise ViewError('Invalid scene budget')
        self._max_vertices=max_vertices;self._max_triangles=max_triangles
        self._thread=get_ident();self._closed=False;self._document=document;self.cache=MeshCache(document);self.settings=settings;self._actors={}
        self.renderer=vtk.vtkRenderer();self.renderer.SetBackground(.10,.13,.18)
        self._owns_window=render_window is None
        self.window=vtk.vtkRenderWindow() if self._owns_window else render_window
        if self._owns_window:
            self.window.SetOffScreenRendering(int(offscreen));self.window.SetSize(*size);self.window.SetWindowName('GooseCAD Professional — experimental viewer')
        self.window.SetMultiSamples(0);self.window.AddRenderer(self.renderer)
        self.picker=vtk.vtkCellPicker();self.picker.SetTolerance(.0005)
    @property
    def document(self):
        return self._document

    def is_current_selection(self, selection):
        """Validate a face-local hit against the currently displayed snapshot."""
        self._check()
        if type(selection) is not Selection:
            return False
        state = self._actors.get(selection.body)
        if state is None:
            return False
        snapshot = state[0]
        offsets = snapshot.mesh.face_offsets
        return (
            snapshot.revision == selection.revision
            and self.cache.is_current(snapshot)
            and 0 <= selection.face < len(offsets) - 1
            and offsets[selection.face] <= selection.triangle < offsets[selection.face + 1]
        )

    def _check(self):
        if get_ident()!=self._thread or self._closed:raise ViewError('Scene must be open on its owning thread')
    def plan_refresh(self, bodies):
        """Capture only CPU data on the scene-owning thread."""
        self._check()
        bodies=tuple(bodies)
        if (len(bodies)>256 or any(type(b) is not str for b in bodies)
                or len(set(bodies))!=len(bodies)):
            raise ViewError('Invalid body list')
        return MeshRequest(self._document,self.cache,self._document.revision,
                           bodies,self.settings,
                           tuple(self._actors[b][0] for b in bodies if b in self._actors),
                           self._max_vertices,self._max_triangles)

    def publish(self, prepared):
        """Build VTK buffers transactionally on the owner, never in a worker."""
        self._check()
        if type(prepared) is not PreparedMeshes:
            raise ViewError('Expected prepared display meshes')
        plan=prepared.request
        if (plan.document is not self._document or plan.cache is not self.cache
                or plan.settings!=self.settings
                or plan.max_vertices!=self._max_vertices
                or plan.max_triangles!=self._max_triangles):
            raise ViewError('Prepared display belongs to another scene or settings')
        prepared.validate()
        staged={};changed=[]
        for snapshot in prepared.snapshots:
            body=snapshot.body
            old=self._actors.get(body)
            if old is not None and old[0] is snapshot:
                staged[body]=old;continue
            mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(polydata(snapshot.mesh));mapper.ScalarVisibilityOff()
            actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(.44,.68,.89);actor.GetProperty().SetInterpolationToFlat()
            staged[body]=(snapshot,actor);changed.append(body)
        prepared.validate()
        for body,(snapshot,actor) in self._actors.items():
            if body not in staged or staged[body][1] is not actor:self.renderer.RemoveActor(actor)
        for body in changed:self.renderer.AddActor(staged[body][1])
        self._actors=staged;self.renderer.ResetCameraClippingRange();return tuple(changed)

    def refresh(self,bodies):
        return self.publish(self.plan_refresh(bodies).prepare())
    def fit(self):
        self._check();self.renderer.ResetCamera();self.renderer.ResetCameraClippingRange()
    def orbit(self,azimuth,elevation):
        self._check();c=self.renderer.GetActiveCamera();c.Azimuth(azimuth);c.Elevation(elevation);c.OrthogonalizeViewUp();self.renderer.ResetCameraClippingRange()
    def render(self):
        self._check()
        if not all(self.cache.is_current(s) for s,a in self._actors.values()):raise ViewError('Refresh stale scene before rendering')
        self.window.Render()
    def pick(self,x,y):
        self._check()
        if not self.picker.Pick(x,y,0,self.renderer):return None
        actor=self.picker.GetActor();cell=self.picker.GetCellId()
        for body,(s,a) in self._actors.items():
            if a==actor:
                if not self.cache.is_current(s) or not 0<=cell<len(s.mesh.triangles):return None
                face=bisect_right(s.mesh.face_offsets,cell)-1
                return Selection(body,s.revision,face,cell)
        return None
    def select(self,x,y):
        self._check();hit=self.pick(x,y)
        for body,(s,a) in self._actors.items():a.GetProperty().SetColor(*((.98,.68,.23) if hit and hit.body==body else (.44,.68,.89)))
        return hit
    def close(self):
        self._check();self.renderer.RemoveAllViewProps();self._actors.clear();self.cache.clear()
        self.window.RemoveRenderer(self.renderer)
        if self._owns_window:self.window.Finalize()
        self._closed=True
