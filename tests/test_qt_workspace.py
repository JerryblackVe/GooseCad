"""Opt-in real Qt/VTK integration: run under a supported graphical session."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

@unittest.skipUnless(os.environ.get("GOOSECAD_TEST_QT") == "1", "requires real Qt/VTK context")
class QtWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_edit_undo_redo_save_open_and_conflict(self):
        from goosecad.ui.main_window import MainWindow
        from goosecad.document.session import DocumentSession
        from PySide6.QtWidgets import QMessageBox
        window = MainWindow()
        window.show()
        window.initialize_view()
        self.app.processEvents()
        try:
            self.assertTrue(window._view_ok)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "part.gcad"
                self.assertTrue(window.save_as_path(path))
                row = next(i for i in range(window.parameters.rowCount())
                           if window.parameters.item(i, 0).text() == "width")
                window.parameters.item(row, 1).setText("25")
                self.assertTrue(window.apply_parameters())
                self.assertTrue(window.session.dirty)
                self.assertEqual(window.session.document.value("width"), 25)
                self.assertTrue(window.undo())
                self.assertFalse(window.session.dirty)
                self.assertTrue(window.redo())
                self.assertTrue(window.save_document())
                self.assertTrue(window.open_path(path))
                self.assertEqual(window.session.document.value("width"), 25)
                other = DocumentSession.open(path)
                other.edit({"width": 30})
                other.save()
                window.session.edit({"width": 35})
                with patch.object(window, "_error") as error:
                    self.assertFalse(window.save_document())
                    error.assert_called_once()
                self.assertTrue(window.session.dirty)
                self.assertEqual(DocumentSession.open(path).document.value("width"), 30)
        finally:
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
                window.close()
            self.app.processEvents()

    def test_invalid_edit_open_and_save_as_preserve_session(self):
        from goosecad.ui.main_window import MainWindow
        from PySide6.QtWidgets import QMessageBox
        window = MainWindow()
        window.show()
        window.initialize_view()
        try:
            original = window.session
            row = next(i for i in range(window.parameters.rowCount())
                       if window.parameters.item(i, 0).text() == "width")
            window.parameters.item(row, 1).setText("0")
            with patch.object(window, "_error") as error:
                self.assertFalse(window.apply_parameters())
                error.assert_called_once()
            self.assertEqual(original.document.value("width"), 20)
            self.assertFalse(original.dirty)
            window.parameters.item(row, 1).setText("20")
            self.assertTrue(window.apply_parameters())
            with tempfile.TemporaryDirectory() as directory:
                bad = Path(directory) / "broken.gcad"
                bad.write_bytes(b"not a native document")
                with patch.object(window, "_error") as error:
                    self.assertFalse(window.open_path(bad))
                    error.assert_called_once()
                self.assertIs(window.session, original)
                with patch.object(window, "_error") as error:
                    self.assertFalse(window.save_as_path(bad))
                    error.assert_called_once()
                self.assertEqual(bad.read_bytes(), b"not a native document")
                self.assertIsNone(original.path)
            import numpy as np
            import vtk
            from vtk.util.numpy_support import vtk_to_numpy
            image = vtk.vtkWindowToImageFilter()
            image.SetInput(window.scene.window)
            image.ReadFrontBufferOff()
            image.Update()
            pixels = vtk_to_numpy(image.GetOutput().GetPointData().GetScalars())
            self.assertTrue(np.any(pixels != pixels[0]), "no visible geometry")
        finally:
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
                window.close()
            self.app.processEvents()

    def test_async_button_cancel_and_close_guard(self):
        import time
        from threading import Event
        from PySide6.QtWidgets import QMessageBox
        from goosecad.ui.main_window import MainWindow
        window = MainWindow()
        window.show()
        window.initialize_view()
        entered, release = Event(), Event()
        real_edit = window.session.document.edit
        def gated(*args, **kwargs):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("test gate timeout")
            return real_edit(*args, **kwargs)
        def finish():
            deadline = time.monotonic() + 10
            while window.tasks.busy:
                self.app.processEvents()
                if time.monotonic() > deadline:
                    self.fail("Qt worker did not finish")
                time.sleep(.005)
        try:
            row = next(i for i in range(window.parameters.rowCount())
                       if window.parameters.item(i, 0).text() == "width")
            window.parameters.item(row, 1).setText("27")
            with patch.object(window.session.document, "edit", side_effect=gated):
                window.apply_button.click()
                self.assertTrue(entered.wait(5))
                self.app.processEvents()
                self.assertTrue(window.tasks.busy)
                self.assertFalse(window.save_action.isEnabled())
                self.assertTrue(window.cancel_action.isEnabled())
                self.assertFalse(window.close())
                window.cancel_action.trigger()
                release.set()
                finish()
            self.assertEqual(window.session.document.value("width"), 20)
            self.assertTrue(window.apply_button.isEnabled())
            window.apply_button.click()
            finish()
            self.assertEqual(window.session.document.value("width"), 27)
            self.assertTrue(window.undo_action.isEnabled())
            window.undo_action.trigger()
            finish()
            self.assertEqual(window.session.document.value("width"), 20)
            window.redo_action.trigger()
            finish()
            self.assertEqual(window.session.document.value("width"), 27)
        finally:
            release.set()
            finish()
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
                window.close()
            self.app.processEvents()
