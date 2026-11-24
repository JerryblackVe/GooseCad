"""Compare synchronous/async phases on identical synthetic native models.

Bodies share the native origin, so this is not a spatial assembly or FPS test.
All timings are CPU/wall time under a real Qt event loop; geometry checks are
outside the timed interval. Xvfb software is not representative of GPU speed.
"""
import csv
import math
import os
import platform
import statistics
import sys
from time import perf_counter_ns
from unittest.mock import patch

from PySide6 import __version__ as qt_version
from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from vtk import vtkVersion
from goosecad.document.native import NativeDocument, Feature
from goosecad.document.session import DocumentSession
from goosecad.geometry.kernel import properties
from goosecad.ui.main_window import MainWindow
from goosecad.view.preparation import MeshRequest


def make_model(count, shared):
    params = {"r": 6}
    features = []
    for i in range(count):
        name = "r" if shared or i == 0 else f"r{i}"
        if name not in params:
            params[name] = 6 + i / 2
        features.append(Feature(f"s{i}", "sphere", (name,)))
    return DocumentSession(NativeDocument(params, features))


def measure_case(app, case, count, shared, repetitions):
    window = MainWindow(make_model(count, shared), autosave_interval=0)
    window.show()
    window.initialize_view()
    app.processEvents()
    errors = []
    window._error = lambda exc: errors.append(exc)
    measurements = {}
    old_edit = window.session.document.edit
    old_publish = window.scene.publish
    old_render = window.scene.render
    old_prepare = MeshRequest.prepare

    def timed(name, callback, *args, **kwargs):
        begin = perf_counter_ns()
        try:
            return callback(*args, **kwargs)
        finally:
            measurements[name] = (perf_counter_ns()-begin)/1e6

    def edit(*args, **kwargs):
        return timed("edit_ms",old_edit,*args,**kwargs)
    def publish(*args, **kwargs):
        return timed("publish_ms",old_publish,*args,**kwargs)
    def render(*args, **kwargs):
        return timed("render_ms",old_render,*args,**kwargs)
    def prepare(request, **kwargs):
        return timed("mesh_ms",old_prepare,request,**kwargs)

    window.session.document.edit = edit
    window.scene.publish = publish
    window.scene.render = render
    row = next(i for i in range(window.parameters.rowCount())
               if window.parameters.item(i,0).text() == "r")
    viewport = window.viewport.size()
    caps = window.scene.window.ReportCapabilities()
    renderer = next((l.strip() for l in caps.splitlines()
                     if "renderer string" in l.lower()),"unknown")
    rows = []
    try:
        with patch.object(MeshRequest,"prepare",new=prepare):
            for mode in ("sync","async"):
                for i in range(repetitions+5):
                    before = {body: actor for body,(_,actor) in window.scene._actors.items()}
                    radius = 7 if window.session.document.value("r") == 6 else 6
                    window.parameters.item(row,1).setText(str(radius))
                    measurements.clear()
                    errors.clear()
                    loop = QEventLoop()
                    timeout = QTimer()
                    timeout.setSingleShot(True)
                    timeout.timeout.connect(loop.quit)
                    def finished():
                        if not window.tasks.busy:
                            loop.quit()
                    window.task_finished.connect(finished,Qt.ConnectionType.QueuedConnection)
                    try:
                        start = perf_counter_ns()
                        if mode == "sync":
                            assert window.apply_parameters()
                        else:
                            window.apply_button.click()
                            assert window.tasks.busy
                        returned = perf_counter_ns()
                        if mode == "async":
                            timeout.start(30_000)
                            loop.exec()
                            assert not window.tasks.busy, "worker timeout"
                        ended = perf_counter_ns()
                    finally:
                        timeout.stop()
                        window.task_finished.disconnect(finished)
                    if errors:
                        raise RuntimeError("benchmark GUI failure") from errors[0]
                    assert window._view_ok
                    assert set(measurements) == {"edit_ms","mesh_ms","publish_ms","render_ms"}
                    assert window.session.document.value("r") == radius
                    changed = sum(before[b] is not actor for b,(_,actor) in window.scene._actors.items())
                    assert changed == (count if shared else 1), (case,changed)
                    # Independent check of exact B-Rep mass, not mesh volume.
                    for body in (("s0", f"s{count-1}") if shared and count>1 else ("s0",)):
                        p = properties(window.session.document.value(body))
                        assert p.solids == 1
                        assert math.isclose(p.volume,4*math.pi*radius**3/3,rel_tol=1e-9)
                    triangles = sum(len(s.mesh.triangles) for s,_ in window.scene._actors.values())
                    if i>=5:
                        rows.append((case,count,mode,i-5,(returned-start)/1e6,
                                     measurements["edit_ms"],measurements["mesh_ms"],
                                     measurements["publish_ms"],measurements["render_ms"],
                                     (ended-start)/1e6,changed,triangles,window.scene.cache.info().bytes,
                                     platform.platform(),platform.processor() or "unknown",os.cpu_count(),
                                     qt_version,vtkVersion.GetVTKVersion(),
                                     f"{viewport.width()}x{viewport.height()}",renderer))
                    app.processEvents()
    finally:
        if not window.tasks.busy:
            with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.Discard):
                window.close()
            app.processEvents()
    return rows


def main(path):
    app = QApplication([])
    rows=[]
    for case,count,shared,reps in (("one_sphere",1,False,30),
                                    ("20_independent",20,False,15),
                                    ("20_shared",20,True,15)):
        rows.extend(measure_case(app,case,count,shared,reps))
    with open(path,"w",newline="",encoding="utf-8") as out:
        writer=csv.writer(out)
        writer.writerow(("case","bodies","mode","sample","command_return_ms","edit_ms",
                         "mesh_ms","publish_ms","render_ms","end_to_end_ms","changed_actors",
                         "triangles","cache_bytes","platform","cpu","logical_cpus","qt","vtk",
                         "viewport","renderer"))
        writer.writerows(rows)
    for case in ("one_sphere","20_independent","20_shared"):
        for mode in ("sync","async"):
            selected=[r for r in rows if r[0]==case and r[2]==mode]
            for col,name in ((4,"command_return_ms"),(5,"edit_ms"),(6,"mesh_ms"),
                             (7,"publish_ms"),(8,"render_ms"),(9,"end_to_end_ms")):
                values=[r[col] for r in selected]
                p95=statistics.quantiles(values,n=100,method="inclusive")[94]
                print(f"{case} {mode} {name}: n={len(values)} median={statistics.median(values):.6f} p95={p95:.6f}",flush=True)


if __name__=="__main__":
    main(sys.argv[1])
