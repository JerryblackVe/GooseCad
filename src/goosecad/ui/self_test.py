"""Frozen-runtime smoke test; no GPU context, no user document or settings."""
import json
import math
import tempfile
from pathlib import Path

from PySide6 import __version__ as qt_version
from PySide6.QtWidgets import QApplication, QWidget
import numpy
import scipy
from vtkmodules.vtkCommonCore import vtkVersion
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkRenderWindow, vtkRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera

from goosecad.document.native import NativeDocument, Feature
from goosecad.document.session import DocumentSession
from goosecad.geometry.kernel import properties
from goosecad.document.primitives import PrimitiveSpec, BooleanSpec
from goosecad.geometry.mesh import tessellate
from goosecad.view.scene import polydata


def run():
    app = QApplication(["GooseCAD-self-test"])
    widget = QWidget()
    widget.setWindowTitle("GooseCAD package smoke")
    assert widget.windowTitle() == "GooseCAD package smoke"
    # Check representative compiled dependencies, geometry and native I/O.
    from scipy.linalg import solve
    assert numpy.allclose(solve([[2.,0.],[0.,4.]],[4.,8.]),[2.,2.])
    session = DocumentSession(NativeDocument(
        {"x":2,"y":3,"z":4},(Feature("box","box",("x","y","z")),)))
    assert math.isclose(properties(session.document.value("box")).volume,24.,rel_tol=1e-9)
    session.edit({"x":5})
    mesh = tessellate(session.document.value("box"))
    poly = polydata(mesh)
    assert poly.GetNumberOfCells() == 12
    # Confirm registered VTK factories and camera style without calling Render.
    assert vtkRenderer().GetClassName() == 'vtkOpenGLRenderer'
    interactor = vtkRenderWindowInteractor()
    interactor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
    assert interactor.GetInteractorStyle().GetClassName() == 'vtkInteractorStyleTrackballCamera'
    # Exercise structural history and OCCT Boolean bindings in the frozen image.
    PrimitiveSpec('sphere',(1,)).append_to(session.document)
    BooleanSpec('union','box','sphere').append_to(session.document)
    assert properties(session.document.value('union')).volume > 60
    session.document.undo()
    session.document.undo()
    assert tuple(f.id for f in session.document.features) == ('box',)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/"package-test.gcad"
        session.save_as(path)
        session.edit({"x":6})
        session.save()
        assert DocumentSession.open(path).document.value("x") == 6
        assert DocumentSession.open_recovery(path).document.value("x") == 5
    widget.close()
    app.processEvents()
    print(json.dumps({"status":"passed","qt":qt_version,"vtk":vtkVersion.GetVTKVersion(),
                      "numpy":numpy.__version__,"scipy":scipy.__version__,
                      "scope":"runtime imports, offscreen Qt widget, B-Rep, mesh, native save/recover; no GPU"},
                     sort_keys=True),flush=True)
    return 0
