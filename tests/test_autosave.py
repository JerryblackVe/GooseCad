import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goosecad.document.native import Feature, NativeDocument, DiskRevisionConflict
from goosecad.document.session import DocumentSession
from goosecad.document.autosave import AutosaveSlot, AutosaveError, list_recoveries


def sample():
    return DocumentSession(NativeDocument({"x": 2, "y": 3, "z": 4},
        (Feature("box", "box", ("x", "y", "z")),)))


class AutosaveTests(unittest.TestCase):
    def test_capture_independent_and_recover_as_unsaved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "part.gcad"
            session = sample()
            session.save_as(primary)
            original_token = session.disk_revision
            slot = AutosaveSlot(root / "recovery", session.document)
            self.assertIsNone(slot.capture(session))
            self.assertFalse(slot.root.exists())
            session.edit({"x": 6})
            self.assertEqual(slot.capture(session), slot.path)
            self.assertEqual(session.disk_revision, original_token)
            self.assertTrue(session.dirty)
            self.assertEqual(DocumentSession.open(primary).document.value("x"), 2)
            self.assertIsNone(slot.capture(session))
            self.assertEqual([e.path for e in list_recoveries(slot.root)], [slot.path])
            recovered = DocumentSession.open_copy(slot.path)
            self.assertTrue(recovered.dirty)
            self.assertIsNone(recovered.path)
            self.assertEqual(recovered.document.value("x"), 6)
            session.edit({"x": 8})
            slot.capture(session)
            self.assertEqual(DocumentSession.open_copy(slot.path).document.value("x"), 8)
            self.assertEqual(DocumentSession.open_recovery(slot.path).document.value("x"), 6)

    def test_conflict_and_failure_do_not_advance_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            session = sample()
            slot = AutosaveSlot(directory, session.document)
            session.edit({"x": 6})
            slot.capture(session)
            old_revision = slot.last_revision
            outsider = DocumentSession.open(slot.path)
            outsider.edit({"x": 7})
            outsider.save()
            session.edit({"x": 8})
            with self.assertRaises(DiskRevisionConflict):
                slot.capture(session)
            self.assertEqual(slot.last_revision, old_revision)
            self.assertTrue(session.dirty)
            self.assertEqual(DocumentSession.open(slot.path).document.value("x"), 7)
            with patch("goosecad.document.autosave.save", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    slot.capture(session)
            self.assertEqual(slot.last_revision, old_revision)

    def test_slot_identity_and_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            session = sample()
            slot = AutosaveSlot(directory, session.document)
            with self.assertRaises(AutosaveError):
                slot.capture(sample())
            session.edit({"x": 9})
            with patch("goosecad.document.autosave.MAX_SLOTS", 0):
                with self.assertRaises(AutosaveError):
                    slot.capture(session)
            self.assertFalse(slot.path.exists())
            self.assertTrue(session.dirty)
