import time
import unittest
from threading import Event, get_ident, Thread
from unittest.mock import patch

from goosecad.document.native import NativeDocument, Feature
from goosecad.document.session import DocumentSession
from goosecad.document.tasks import DocumentTasks, TaskStateError
from goosecad.parametric import Cancelled


def session():
    return DocumentSession(NativeDocument(
        {"x": 2, "y": 3, "z": 4}, (Feature("box", "box", ("x", "y", "z")),)))


def collect(tasks):
    deadline = time.monotonic() + 10
    while not tasks.ready:
        if time.monotonic() >= deadline:
            raise AssertionError("worker did not finish")
        time.sleep(.001)
    return tasks.collect()


class DocumentTaskTests(unittest.TestCase):
    def test_edit_undo_redo_and_owner_reconciliation(self):
        current = session()
        tasks = DocumentTasks(current)
        try:
            tasks.edit({"x": 6})
            self.assertTrue(tasks.busy)
            collect(tasks)
            self.assertEqual(current.document.value("x"), 6)
            self.assertTrue(current.dirty)
            tasks.undo()
            collect(tasks)
            self.assertFalse(current.dirty)
            tasks.redo()
            collect(tasks)
            self.assertTrue(current.dirty)
        finally:
            if tasks.busy:
                try:
                    collect(tasks)
                except Exception:
                    pass
            tasks.close()

    def test_cancel_before_publish_preserves_geometry_and_history(self):
        current = session()
        tasks = DocumentTasks(current)
        entered, release = Event(), Event()
        owner = get_ident()
        real = current.document.edit
        before = current.document.to_bytes()
        selection = current.select_body("box")
        def gated(*args, **kwargs):
            self.assertNotEqual(get_ident(), owner)
            entered.set()
            if not release.wait(5):
                raise RuntimeError("test gate timeout")
            return real(*args, **kwargs)
        try:
            with patch.object(current.document, "edit", side_effect=gated):
                tasks.edit({"x": 9})
                self.assertTrue(entered.wait(5))
                self.assertIsNone(tasks.collect())
                with self.assertRaises(TaskStateError):
                    tasks.undo()
                with self.assertRaises(TaskStateError):
                    tasks.close()
                self.assertTrue(tasks.request_cancel())
                release.set()
                with self.assertRaises(Cancelled):
                    collect(tasks)
            self.assertEqual(current.document.to_bytes(), before)
            self.assertEqual(current.document.history_depths, (0, 0))
            self.assertEqual(current.selection, selection)
            self.assertFalse(current.dirty)
        finally:
            release.set()
            if tasks.busy:
                try:
                    collect(tasks)
                except Exception:
                    pass
            tasks.close()

    def test_failed_operation_is_collectable_and_runner_reusable(self):
        current = session()
        tasks = DocumentTasks(current)
        try:
            tasks.edit({"x": 0})
            with self.assertRaises(Exception):
                collect(tasks)
            self.assertFalse(tasks.busy)
            self.assertEqual(current.document.value("x"), 2)
            self.assertEqual(current.document.history_depths, (0, 0))
            tasks.edit({"x": 8})
            collect(tasks)
            self.assertEqual(current.document.value("x"), 8)
        finally:
            if tasks.busy:
                try:
                    collect(tasks)
                except Exception:
                    pass
            tasks.close()

    def test_owner_thread_and_close_contract(self):
        tasks = DocumentTasks(session())
        errors = []
        def wrong_thread():
            try:
                tasks.edit({"x": 9})
            except TaskStateError as exc:
                errors.append(exc)
        thread = Thread(target=wrong_thread)
        thread.start()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        tasks.close()
        with self.assertRaises(TaskStateError):
            tasks.edit({"x": 9})

    def test_async_disk_roundtrip_conflict_and_independent_open(self):
        import tempfile
        from pathlib import Path
        from goosecad.document.native import DiskRevisionConflict
        current = session()
        tasks = DocumentTasks(current)
        try:
            with tempfile.TemporaryDirectory() as root:
                path = Path(root) / "part.gcad"
                tasks.save_as(path)
                self.assertEqual(tasks.kind, "save")
                self.assertFalse(tasks.request_cancel())
                collect(tasks)
                self.assertFalse(current.dirty)
                tasks.edit({"x": 7})
                collect(tasks)
                tasks.save()
                collect(tasks)
                tasks.open(path)
                candidate = collect(tasks)
                self.assertIsNot(candidate, current)
                self.assertEqual(candidate.document.value("x"), 7)
                candidate.edit({"x": 8})
                candidate.save()
                current.edit({"x": 9})
                tasks.save()
                with self.assertRaises(DiskRevisionConflict):
                    collect(tasks)
                self.assertTrue(current.dirty)
                self.assertEqual(DocumentSession.open(path).document.value("x"), 8)
                tasks.open(path, recovery=True)
                recovery = collect(tasks)
                self.assertTrue(recovery.dirty)
                self.assertIsNone(recovery.path)
                self.assertEqual(recovery.document.value("x"), 7)
        finally:
            if tasks.busy:
                try:
                    collect(tasks)
                except Exception:
                    pass
            tasks.close()

    def test_cancel_open_without_changing_active_session(self):
        from pathlib import Path
        current = session()
        tasks = DocumentTasks(current)
        entered, release = Event(), Event()
        def gated(path):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("test gate timeout")
            return session()
        try:
            with patch.object(DocumentSession, "open", side_effect=gated):
                tasks.open(Path("unused.gcad"))
                self.assertTrue(entered.wait(5))
                self.assertTrue(tasks.request_cancel())
                self.assertIsNone(tasks.collect())
                release.set()
                with self.assertRaises(Cancelled):
                    collect(tasks)
            self.assertIs(tasks.session, current)
            self.assertFalse(current.dirty)
        finally:
            release.set()
            if tasks.busy:
                try:
                    collect(tasks)
                except Exception:
                    pass
            tasks.close()
