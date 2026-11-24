"""Synchronous baseline and asynchronous command latency on the same runner.

The command-return metric measures dispatch/control updates, not photon latency.
The end-to-end metric includes event-loop dispatch and scene refresh. The actual
document edit time excludes Qt refresh. No GPU performance claims from Xvfb.
"""
import csv
import os
import platform
import statistics
import sys
import time
from time import perf_counter_ns

from PySide6 import __version__ as qt_version
from PySide6.QtWidgets import QApplication, QMessageBox
from unittest.mock import patch
from goosecad.ui.main_window import MainWindow
from vtk import vtkVersion


def main(path):
    app = QApplication([])
    window = MainWindow(autosave_interval=0)
    window.show()
    window.initialize_view()
    app.processEvents()
    rows = []
    measured = []
    real_edit = window.session.document.edit

    def timed_edit(*args, **kwargs):
        start = perf_counter_ns()
        try:
            return real_edit(*args, **kwargs)
        finally:
            measured.append((perf_counter_ns() - start) / 1e6)

    window.session.document.edit = timed_edit
    def fail(exc):
        raise RuntimeError("Benchmark operation failed") from exc
    window._error = fail
    caps = window.scene.window.ReportCapabilities()
    renderer = next((line.strip() for line in caps.splitlines()
                     if "renderer string" in line.lower()), "unknown")
    size = window.viewport.size()
    metadata = (platform.platform(), platform.processor() or "unknown",
                os.cpu_count(), qt_version, vtkVersion.GetVTKVersion(),
                f"{size.width()}x{size.height()}", "box 1 body, 3 inputs", renderer)
    try:
        for mode in ("sync", "async"):
            for i in range(35):
                row = next(i for i in range(window.parameters.rowCount())
                           if window.parameters.item(i, 0).text() == "width")
                expected = 22 if window.session.document.value("width") == 21 else 21
                window.parameters.item(row, 1).setText(str(expected))
                measured.clear()
                start = perf_counter_ns()
                if mode == "sync":
                    assert window.apply_parameters()
                else:
                    window.apply_button.click()
                    assert window.tasks.busy, "asynchronous command not dispatched"
                returned = perf_counter_ns()
                deadline = time.monotonic() + 10
                while window.tasks.busy:
                    app.processEvents()
                    if time.monotonic() >= deadline:
                        raise RuntimeError("asynchronous benchmark timed out")
                    if window.tasks.busy:
                        time.sleep(.001)
                app.processEvents()
                finished = perf_counter_ns()
                assert window.session.document.value("width") == expected
                assert window._view_ok and len(measured) == 1
                if i >= 5:
                    rows.append((mode, i - 5, (returned - start) / 1e6,
                                 measured[0], (finished - start) / 1e6, *metadata))
        with open(path, "w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(("mode", "sample", "command_return_ms", "document_edit_ms",
                             "end_to_end_ms", "platform", "cpu", "logical_cpus", "qt",
                             "vtk", "viewport", "model", "renderer"))
            writer.writerows(rows)
        for mode in ("sync", "async"):
            for index, label in ((2, "command_return_ms"), (3, "document_edit_ms"),
                                 (4, "end_to_end_ms")):
                values = [r[index] for r in rows if r[0] == mode]
                p95 = statistics.quantiles(values, n=100, method="inclusive")[94]
                print(f"{mode} {label}: n={len(values)} median={statistics.median(values):.6f} p95={p95:.6f}", flush=True)
    finally:
        # Do not destroy a running worker. On exceptional timeout request
        # cancellation and let the owning event loop collect the result.
        if window.tasks.busy:
            window.cancel_task()
            deadline = time.monotonic() + 10
            while window.tasks.busy and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.005)
        if not window.tasks.busy:
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Discard):
                window.close()
            app.processEvents()


if __name__ == "__main__":
    main(sys.argv[1])
