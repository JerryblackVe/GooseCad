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

    def test_recovery_and_idempotent_widget_destruction(self):
        import gc
        import sys
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QMessageBox
        from goosecad.ui.main_window import MainWindow
        from goosecad.document.session import DocumentSession
        errors = []
        with patch.object(sys, "excepthook", side_effect=lambda *args: errors.append(args)):
            # The previous QVTK base could recurse during parent destruction.
            for _ in range(2):
                window = MainWindow()
                window.show()
                window.initialize_view()
                with tempfile.TemporaryDirectory() as directory:
                    primary = Path(directory) / "primary.gcad"
                    recovered = Path(directory) / "recovered.gcad"
                    self.assertTrue(window.save_as_path(primary))
                    window.session.edit({"width": 30})
                    self.assertTrue(window.save_document())
                    self.assertTrue(window.recover_path(primary))
                    self.assertTrue(window.session.dirty)
                    self.assertIsNone(window.session.path)
                    self.assertEqual(window.session.document.value("width"), 20)
                    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
                        self.assertFalse(window.close())
                    self.assertTrue(window.save_as_path(recovered))
                    self.assertFalse(window.session.dirty)
                    self.assertEqual(DocumentSession.open(primary).document.value("width"), 30)
                    self.assertTrue(window.close())
                    self.assertTrue(window.close())
                window.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                del window
                gc.collect()
                self.app.processEvents()
        self.assertEqual(errors, [], "unexpected exception in Qt callback")

    def test_async_file_actions_save_then_open_and_conflict(self):
        import time
        from threading import Event
        from PySide6.QtWidgets import QMessageBox
        from goosecad.ui.main_window import MainWindow
        from goosecad.document.session import DocumentSession
        window = MainWindow()
        window.show()
        window.initialize_view()
        entered, release = Event(), Event()
        def finish():
            deadline = time.monotonic() + 15
            while window.tasks.busy:
                self.app.processEvents()
                if time.monotonic() > deadline:
                    self.fail("file task timed out")
                time.sleep(.005)
        try:
            with tempfile.TemporaryDirectory() as directory:
                primary = Path(directory) / "primary.gcad"
                target = Path(directory) / "target.gcad"
                self.assertTrue(window.save_as_path(primary))
                independent = DocumentSession.open(primary)
                independent.edit({"width": 41})
                independent.save_as(target)
                window.session.edit({"width": 29})
                original = window.session
                real_save = original.save
                def gated():
                    entered.set()
                    if not release.wait(10):
                        raise RuntimeError("gate timeout")
                    return real_save()
                with patch.object(original, "save", side_effect=gated):
                    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save):
                        self.assertTrue(window.request_open_path(target))
                    self.assertTrue(entered.wait(5))
                    self.assertIs(window.session, original)
                    self.assertFalse(window.cancel_action.isEnabled())
                    self.assertFalse(window.close())
                    release.set()
                    finish()
                self.assertEqual(DocumentSession.open(primary).document.value("width"), 29)
                self.assertEqual(window.session.document.value("width"), 41)
                self.assertEqual(window.session.path, target)
                other = DocumentSession.open(target)
                other.edit({"width": 43})
                other.save()
                window.session.edit({"width": 45})
                active = window.session
                with patch.object(window, "_error") as error:
                    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save):
                        self.assertTrue(window.request_open_path(primary))
                    finish()
                    error.assert_called_once()
                self.assertIs(window.session, active)
                self.assertTrue(active.dirty)
                self.assertEqual(DocumentSession.open(target).document.value("width"), 43)
        finally:
            release.set()
            finish()
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
                window.close()
            self.app.processEvents()

    def test_async_open_mesh_prepared_on_worker_once(self):
        import time
        from threading import get_ident
        from goosecad.geometry.mesh_cache import MeshCache
        from goosecad.ui.main_window import MainWindow
        from PySide6.QtWidgets import QMessageBox
        window = MainWindow()
        window.show()
        window.initialize_view()
        owner = get_ident()
        calls = []
        real_get = MeshCache.get
        def traced(cache, *args, **kwargs):
            calls.append(get_ident())
            return real_get(cache, *args, **kwargs)
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "candidate.gcad"
                self.assertTrue(window.save_as_path(path))
                with patch.object(MeshCache,"get",new=traced):
                    self.assertTrue(window.request_open_path(path))
                    deadline = time.monotonic()+15
                    while window.tasks.busy:
                        self.app.processEvents()
                        if time.monotonic()>deadline:
                            self.fail("candidate preparation timed out")
                        time.sleep(.005)
                self.assertEqual(len(calls),1)
                self.assertNotEqual(calls[0],owner)
                self.assertTrue(window._view_ok)
                self.assertEqual(window.session.visible_bodies,("box",))
        finally:
            with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.Discard):
                window.close()
            self.app.processEvents()

    def test_autosave_worker_and_recovery_copy(self):
        import time
        from goosecad.document.session import DocumentSession
        from goosecad.document.autosave import list_recoveries
        from goosecad.ui.main_window import MainWindow
        from PySide6.QtWidgets import QMessageBox
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            window = MainWindow(autosave_root=root / "recovery", autosave_interval=120)
            window.show()
            window.initialize_view()
            def finish():
                deadline = time.monotonic()+15
                while window.tasks.busy:
                    self.app.processEvents()
                    if time.monotonic()>deadline:
                        self.fail("autosave timed out")
                    time.sleep(.005)
            try:
                primary = root / "part.gcad"
                self.assertTrue(window.save_as_path(primary))
                window.session.edit({"width": 36})
                self.assertTrue(window._autosave_tick())
                finish()
                self.assertTrue(window.session.dirty)
                self.assertEqual(DocumentSession.open(primary).document.value("width"),20)
                copies = list_recoveries(root / "recovery")
                self.assertEqual(len(copies),1)
                self.assertFalse(window._autosave_tick())
                with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.Discard):
                    self.assertTrue(window.request_open_path(copies[0].path,recovery_copy=True))
                finish()
                self.assertTrue(window.session.dirty)
                self.assertIsNone(window.session.path)
                self.assertEqual(window.session.document.value("width"),36)
            finally:
                finish()
                with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.Discard):
                    window.close()
                self.app.processEvents()

    def test_recovery_catalog_dialog_archive_and_open_previous(self):
        from PySide6.QtWidgets import QMessageBox
        from goosecad.ui.recovery_dialog import RecoveryDialog
        from goosecad.ui.main_window import sample_session
        from goosecad.document.autosave import AutosaveSlot
        from goosecad.document.session import DocumentSession
        with tempfile.TemporaryDirectory() as directory:
            session = sample_session()
            slot = AutosaveSlot(directory,session.document)
            session.edit({"width":25})
            slot.capture(session)
            session.edit({"width":30})
            slot.capture(session)
            dialog = RecoveryDialog(Path(directory),active_path=slot.path)
            try:
                self.assertEqual(dialog.table.rowCount(),2)
                dialog.table.selectRow(0)
                self.assertFalse(dialog.archive_button.isEnabled())
                self.assertTrue(dialog.open_button.isEnabled())
                dialog.active_path = None
                previous = next(i for i,e in enumerate(dialog.entries) if e.previous)
                dialog.table.selectRow(previous)
                dialog.update_buttons()
                self.assertTrue(dialog.archive_button.isEnabled())
                with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.No):
                    dialog.archive_selected()
                self.assertEqual(dialog.table.rowCount(),2)
                with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.Yes):
                    dialog.archive_selected()
                self.assertEqual(dialog.table.rowCount(),1)
                dialog.table.selectRow(0)
                dialog.open_selected()
                copy = DocumentSession.open_copy(dialog.selected_path)
                self.assertTrue(copy.dirty)
                self.assertEqual(copy.document.value("width"),30)
                archived = list((Path(directory)/"archive").glob("slot-*/*.previous"))
                self.assertEqual(len(archived),1)
                self.assertEqual(DocumentSession.open_copy(archived[0]).document.value("width"),25)
            finally:
                dialog.close()
                dialog.deleteLater()
                self.app.processEvents()

    def test_worker_suspends_automatic_render_and_restores_on_cancel(self):
        import time
        from threading import Event
        from PySide6.QtWidgets import QMessageBox
        from goosecad.ui.main_window import MainWindow
        window = MainWindow(autosave_interval=0)
        window.show()
        window.initialize_view()
        self.app.processEvents()
        entered, release = Event(), Event()
        renders = []
        rw = window.scene.window
        observer = rw.AddObserver("StartEvent",lambda *args:renders.append(1))
        edit = window.session.document.edit
        def gated(*args,**kwargs):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("worker gate timeout")
            return edit(*args,**kwargs)
        try:
            row = next(i for i in range(window.parameters.rowCount())
                       if window.parameters.item(i,0).text()=="width")
            window.parameters.item(row,1).setText("25")
            with patch.object(window.session.document,"edit",side_effect=gated):
                window.apply_button.click()
                self.assertTrue(entered.wait(5))
                iren = rw.GetInteractor()
                self.assertFalse(iren.GetEnableRender())
                window.viewport.update()
                window.viewport.repaint()
                iren.Render()
                self.app.processEvents()
                self.assertEqual(renders,[])
                window.cancel_task()
                release.set()
                deadline=time.monotonic()+15
                while window.tasks.busy:
                    self.app.processEvents()
                    if time.monotonic()>deadline:
                        self.fail("worker timeout")
                    time.sleep(.005)
            self.assertTrue(rw.GetInteractor().GetEnableRender())
            self.assertEqual(window.session.document.value("width"),20)
            window.viewport.update()
            self.app.processEvents()
            self.assertTrue(window.apply_button.isEnabled())
        finally:
            release.set()
            rw.RemoveObserver(observer)
            deadline=time.monotonic()+15
            while window.tasks.busy and time.monotonic()<deadline:
                self.app.processEvents()
                time.sleep(.005)
            if not window.tasks.busy:
                with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.Discard):
                    window.close()
                self.app.processEvents()

    def test_new_primitive_protects_unsaved_and_can_edit_save(self):
        import time
        from PySide6.QtWidgets import QMessageBox
        from goosecad.ui.main_window import MainWindow
        from goosecad.ui.primitive_dialog import PrimitiveDialog
        from goosecad.document.primitives import PrimitiveSpec
        from goosecad.document.session import DocumentSession
        window=MainWindow(autosave_interval=0)
        window.show()
        window.initialize_view()
        def finish():
            deadline=time.monotonic()+15
            while window.tasks.busy:
                self.app.processEvents()
                if time.monotonic()>deadline:
                    self.fail("worker timeout")
                time.sleep(.005)
        try:
            dialog=PrimitiveDialog(window)
            dialog.kind.setCurrentIndex(1)
            dialog.inputs["radius"].setValue(5)
            dialog.inputs["height"].setValue(8)
            self.assertEqual(dialog.specification(),PrimitiveSpec("cylinder",(5,8)))
            dialog.deleteLater()
            self.assertTrue(window.request_new_primitive(PrimitiveSpec("cylinder",(5,8))))
            finish()
            self.assertTrue(window.session.dirty)
            self.assertEqual(window.session.visible_bodies,("cylinder",))
            old=window.session
            with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.Cancel):
                self.assertFalse(window.request_new_primitive(PrimitiveSpec("sphere",(4,))))
            self.assertIs(window.session,old)
            row=next(i for i in range(window.parameters.rowCount())
                     if window.parameters.item(i,0).text()=="radius")
            window.parameters.item(row,1).setText("6")
            window.apply_button.click()
            finish()
            self.assertEqual(window.session.document.value("radius"),6)
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/"cylinder.gcad"
                self.assertTrue(window.save_as_path(path))
                self.assertFalse(window.session.dirty)
                self.assertEqual(DocumentSession.open(path).document.value("radius"),6)
                self.assertTrue(window.request_new_primitive(PrimitiveSpec("sphere",(4,))))
                finish()
                self.assertTrue(window.session.dirty)
                self.assertEqual(window.session.visible_bodies,("sphere",))
        finally:
            finish()
            with patch.object(QMessageBox,"question",return_value=QMessageBox.StandardButton.Discard):
                window.close()
            self.app.processEvents()
