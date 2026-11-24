import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goosecad.document.native import (
    DiskRevisionConflict, Feature, NativeDocument, load_with_revision, save,
)
from goosecad.document.session import (
    BodySelection, DocumentSession, SessionError, UnsavedChanges,
)
from goosecad.geometry.kernel import GeometryError
from goosecad.view.scene import Scene, Selection


def model():
    return NativeDocument(
        {"x": 2, "y": 3, "z": 4},
        (Feature("box", "box", ("x", "y", "z")),),
    )


class SessionTests(unittest.TestCase):
    def test_save_as_and_reopen(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "part.goosecad"
            session = DocumentSession(model())
            self.assertFalse(session.dirty)
            with self.assertRaises(SessionError):
                session.save()
            session.edit({"x": 6})
            self.assertTrue(session.dirty)
            first = session.save_as(path)
            self.assertEqual(first, session.disk_revision)
            self.assertFalse(session.dirty)
            reopened = session.reopen()
            self.assertEqual(reopened.document.value("box").IsNull(), False)
            self.assertEqual(reopened.document.value("x"), 6)
            self.assertEqual(reopened.disk_revision, first)

    def test_save_and_revision_conflict(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "part.goosecad"
            original = DocumentSession(model())
            original.save_as(path)
            concurrent = DocumentSession.open(path)
            original.edit({"x": 6})
            original.save()
            concurrent.edit({"x": 8})
            with self.assertRaises(DiskRevisionConflict):
                concurrent.save()
            self.assertTrue(concurrent.dirty)
            self.assertEqual(load_with_revision(path)[0].value("x"), 6)

    def test_save_as_refuses_existing_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "other.goosecad"
            path.write_text("important data", encoding="utf-8")
            session = DocumentSession(model())
            with self.assertRaises(DiskRevisionConflict):
                session.save_as(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "important data")
            self.assertIsNone(session.path)

    def test_undo_to_clean_and_redo(self):
        session = DocumentSession(model())
        session.edit({"x": 6})
        self.assertTrue(session.dirty)
        session.undo()
        self.assertFalse(session.dirty)
        session.redo()
        self.assertTrue(session.dirty)

    def test_failed_edit_preserves_selection_and_clean_state(self):
        session = DocumentSession(model())
        selection = session.select_body("box")
        with self.assertRaises(Exception):
            session.edit({"x": 0})
        self.assertEqual(session.selection, selection)
        self.assertFalse(session.dirty)

    def test_stale_selection_invalidated_after_edit(self):
        session = DocumentSession(model())
        selection = session.select_body("box")
        self.assertIsInstance(selection, BodySelection)
        session.document.edit({"x": 7})
        self.assertIsNone(session.selection)
        self.assertIsNotNone(session.select_body("box"))
        session.edit({"x": 9})
        self.assertIsNone(session.selection)

    def test_selection_rejects_parameter(self):
        session = DocumentSession(model())
        with self.assertRaises(SessionError):
            session.select_body("x")

    def test_reopen_requires_discard(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "p.goosecad"
            session = DocumentSession(model())
            session.save_as(path)
            session.edit({"x": 8})
            with self.assertRaises(UnsavedChanges):
                session.reopen()
            fresh = session.reopen(discard_changes=True)
            self.assertEqual(fresh.document.value("x"), 2)
            self.assertEqual(session.document.value("x"), 8)

    def test_recovery_is_unsaved_and_primary_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "p.goosecad"
            session = DocumentSession(model())
            session.save_as(path)
            session.edit({"x": 8})
            session.save()
            recovered = DocumentSession.open_recovery(path)
            self.assertIsNone(recovered.path)
            self.assertEqual(recovered.document.value("x"), 2)
            self.assertEqual(load_with_revision(path)[0].value("x"), 8)

    def test_failed_save_does_not_advance_session_token(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "p.goosecad"
            session = DocumentSession(model())
            old = session.save_as(path)
            session.edit({"x": 9})
            with patch("goosecad.document.session.save", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    session.save()
            self.assertTrue(session.dirty)
            self.assertEqual(session.disk_revision, old)

    def test_wrong_scene_rejected(self):
        one = DocumentSession(model())
        other = DocumentSession(model())
        scene = Scene(other.document, offscreen=True)
        try:
            with self.assertRaises(SessionError):
                one.attach_scene(scene)
            other.attach_scene(scene)
            self.assertIs(other.scene, scene)
            other.detach_scene()
            self.assertIsNone(other.scene)
        finally:
            scene.close()

    def test_scene_refresh_and_selection_freshness(self):
        session = DocumentSession(model())
        scene = Scene(session.document, offscreen=True)
        session.attach_scene(scene)
        try:
            self.assertEqual(session.refresh(["box"]), ("box",))
            self.assertEqual(session.visible_bodies, ("box",))
            self.assertEqual(session.refresh(["box"]), ())
            self.assertFalse(scene.is_current_selection(Selection("box", 999, 0, 0)))
            self.assertFalse(scene.is_current_selection(Selection("box", scene._actors["box"][0].revision, 0, 999)))
            session.edit({"x": 7})
            self.assertEqual(session.refresh(["box"]), ("box",))
            with self.assertRaises(Exception):
                session.refresh(["missing"])
            self.assertEqual(session.visible_bodies, ("box",))
        finally:
            session.detach_scene()
            scene.close()

    def test_direct_document_change_is_not_silently_clean(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "p.goosecad"
            session = DocumentSession(model())
            session.save_as(path)
            session.document.edit({"x": 8})
            self.assertTrue(session.dirty)
            with self.assertRaises(UnsavedChanges):
                session.reopen()
            session.undo()
            self.assertFalse(session.dirty)

    def test_change_during_save_rejects_false_clean_state(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "p.goosecad"
            session = DocumentSession(model())
            session.save_as(path)
            original = save

            def intervene(doc, destination, **options):
                result = original(doc, destination, **options)
                doc.edit({"x": 8})
                return result

            with patch("goosecad.document.session.save", side_effect=intervene):
                with self.assertRaisesRegex(SessionError, "changed during save"):
                    session.save()
            self.assertTrue(session.dirty)
            self.assertEqual(load_with_revision(path)[0].value("x"), 2)
            self.assertEqual(session.document.value("x"), 8)

