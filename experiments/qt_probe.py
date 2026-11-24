"""Run under a graphical session; verify actual Qt/VTK render and event loop."""
import sys
from time import perf_counter
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6 import __version__ as qt_version
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk
from goosecad.geometry.kernel import box
from goosecad.geometry.mesh import tessellate
from goosecad.view.scene import polydata

def main():
    app = QApplication(sys.argv)
    widget = QVTKRenderWindowInteractor()
    widget.resize(640, 480)
    window = widget.GetRenderWindow()
    renderer = vtk.vtkRenderer()
    window.AddRenderer(renderer)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(polydata(tessellate(box(20, 30, 40))))
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    renderer.AddActor(actor)
    renderer.ResetCamera()
    widget.show()
    widget.Initialize()
    result = [1]
    def check():
        try:
            start = perf_counter()
            window.Render()
            elapsed = (perf_counter() - start) * 1000
            image = vtk.vtkWindowToImageFilter()
            image.SetInput(window)
            image.ReadFrontBufferOff()
            image.Update()
            pixels = image.GetOutput().GetPointData().GetScalars()
            from vtk.util.numpy_support import vtk_to_numpy
            import numpy as np
            data = vtk_to_numpy(pixels)
            assert np.any(data != data[0]), "No visible geometry"
            print(f"Qt={qt_version}, VTK={vtk.vtkVersion.GetVTKVersion()}, render_ms={elapsed:.3f}")
            result[0] = 0
        finally:
            app.quit()
    QTimer.singleShot(0, check)
    app.exec()
    widget.close()
    return result[0]

if __name__ == "__main__":
    raise SystemExit(main())
