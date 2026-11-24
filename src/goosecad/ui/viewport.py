"""Owned QVTK viewport with explicit, idempotent teardown.

VTK 9.6.2 QVTKRenderWindowInteractor forwards missing attributes to _Iren
and connects parent destruction to close(). During Python GC its fields may
already be cleared; the base __getattr__ can then recurse. MainWindow closes
this widget before destroying the parent. A subsequent close is harmless.
"""
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


class OwnedViewport(QVTKRenderWindowInteractor):
    def __getattr__(self, name):
        # Do not delegate to the base's recursive lookup on a partially
        # initialized or GC-cleared Python wrapper.
        state = object.__getattribute__(self, "__dict__")
        if "_Iren" not in state:
            raise AttributeError(name)
        return super().__getattr__(name)

    def Finalize(self):
        state = object.__getattribute__(self, "__dict__")
        window = state.get("_RenderWindow")
        if window is None or state.get("_gc_finalized"):
            return
        state["_gc_finalized"] = True
        timer = state.get("_Timer")
        if timer is not None:
            timer.stop()
        interactor = state.get("_Iren")
        if interactor is not None:
            interactor.RemoveObservers("CreateTimerEvent")
            interactor.RemoveObservers("DestroyTimerEvent")
            interactor.Disable()
        window.RemoveObservers("CursorChangedEvent")
        window.Finalize()

    def closeEvent(self, event):
        self.Finalize()
        event.accept()

    def paintEvent(self, event):
        state = object.__getattribute__(self, "__dict__")
        if not state.get("_gc_finalized") and "_Iren" in state:
            super().paintEvent(event)

    def resizeEvent(self, event):
        state = object.__getattribute__(self, "__dict__")
        if not state.get("_gc_finalized") and "_Iren" in state:
            super().resizeEvent(event)
