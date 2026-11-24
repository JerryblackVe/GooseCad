"""Measure end-to-end synchronous parameter confirmation in an actual Qt/VTK window.

Linux CI uses software rendering under Xvfb. These are not native GPU/FPS or
input-to-photon measurements. Raw samples allow later comparable baselines.
"""
import csv
import platform
import sys
from time import perf_counter_ns
from PySide6 import __version__ as qt_version
from PySide6.QtWidgets import QApplication, QMessageBox
from goosecad.ui.main_window import MainWindow
from vtk import vtkVersion

def main(path):
    app = QApplication([])
    window = MainWindow()
    window.show()
    window.initialize_view()
    app.processEvents()
    rows = []
    row = next(i for i in range(window.parameters.rowCount())
               if window.parameters.item(i, 0).text() == "width")
    def fail(exc):
        raise RuntimeError("Benchmark operation failed") from exc
    window._error = fail
    try:
        for i in range(35):
            window.parameters.item(row, 1).setText(str(21 + i % 2))
            start = perf_counter_ns()
            assert window.apply_parameters() and window._view_ok
            app.processEvents()
            elapsed = (perf_counter_ns() - start) / 1e6
            if i >= 5:
                rows.append((i - 5, elapsed, platform.platform(), qt_version,
                             vtkVersion.GetVTKVersion(), "box 1 body, 3 inputs", "Xvfb/software CI"))
        with open(path, "w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(("sample", "confirm_and_render_ms", "platform", "qt", "vtk", "model", "backend"))
            writer.writerows(rows)
    finally:
        # Discard benchmark-only edits without interactive modal dialogs.
        window._can_replace = lambda: True
        window.close()
        app.processEvents()

if __name__ == "__main__":
    main(sys.argv[1])
