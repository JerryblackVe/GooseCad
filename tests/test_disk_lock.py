"""Exercise cooperative save conflicts, including an independent spawned writer."""
import multiprocessing as mp
import os,tempfile,unittest
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch
from goosecad.document import native as n
from goosecad.geometry.kernel import properties


def doc(value=2): return n.NativeDocument({'x':value},[n.Feature('s','sphere',('x',))])


def hold_writer(path,entered,release):
    original=n._atomic
    def wait_before_write(p,data):
        entered.set()
        if not release.wait(15): raise RuntimeError('test synchronization timeout')
        original(p,data)
    with patch.object(n,'_atomic',side_effect=wait_before_write): n.save(doc(3),path)


def kill_writer(path):
    with patch.object(n,'_atomic',side_effect=lambda *args:os._exit(73)):
        n.save(doc(3),path)


def crash_at_replace(path, phase, updating):
    """Hard process exit; no Python finally or lock cleanup runs."""
    original = os.replace
    path = Path(path)
    previous = n.recovery_path(path)
    def replace(source, destination):
        target = Path(destination)
        if phase == "before_primary" and target == path:
            os._exit(74)
        original(source, destination)
        if phase == "after_previous" and target == previous:
            os._exit(74)
        if phase == "after_primary" and target == path:
            os._exit(74)
    expected = n.load_with_revision(path)[1] if updating else None
    with patch.object(n.os, "replace", side_effect=replace):
        n.save(doc(3), path, expected_revision=expected)


def run_crash(path, phase, updating):
    worker = mp.get_context("spawn").Process(
        target=crash_at_replace, args=(path, phase, updating))
    worker.start()
    try:
        worker.join(30)
        if worker.is_alive():
            raise AssertionError("crash worker timeout")
        if worker.exitcode != 74:
            raise AssertionError(f"unexpected worker exit {worker.exitcode}")
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(10)
        worker.close()


class DiskLockTests(unittest.TestCase):
    def test_revision_matches_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; token=n.save(doc(),p,expected_revision=None)
            self.assertEqual(token,sha256(p.read_bytes()).hexdigest()); d,read=n.load_with_revision(p)
            self.assertEqual(read,token); d.edit({'x':3}); token2=n.save(d,p,expected_revision=read)
            self.assertNotEqual(token2,token); self.assertEqual(n.recover(p).value('x'),2)
    def test_stale_writer_does_not_touch_primary_or_previous(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; t=n.save(doc(),p); n.save(doc(3),p,expected_revision=t)
            before=p.read_bytes(); previous=n.recovery_path(p).read_bytes()
            self.assertRaises(n.DiskRevisionConflict,n.save,doc(4),p,expected_revision=t)
            self.assertEqual(p.read_bytes(),before); self.assertEqual(n.recovery_path(p).read_bytes(),previous)
            self.assertFalse(n.lock_path(p).exists())
    def test_new_or_deleted_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; t=n.save(doc(),p,expected_revision=None)
            self.assertRaises(n.DiskRevisionConflict,n.save,doc(3),p,expected_revision=None)
            p.unlink(); self.assertRaises(n.DiskRevisionConflict,n.save,doc(),p,expected_revision=t)
            self.assertFalse(p.exists()); self.assertFalse(n.lock_path(p).exists())
    def test_invalid_revision_token(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'
            for v in ('x','F'*64,True,12):self.assertRaises(n.NativeError,n.save,doc(),p,expected_revision=v)
            self.assertFalse(p.exists()); self.assertFalse(n.lock_path(p).exists())
    def test_lock_reserved_and_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; lock=n.lock_path(p); lock.write_bytes(b'other writer')
            self.assertRaises(n.WriterBusyError,n.save,doc(),p)
            self.assertRaises(n.NativeError,n.save,doc(),lock); self.assertEqual(lock.read_bytes(),b'other writer')
    def test_release_after_write_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; n.save(doc(),p); old=p.read_bytes()
            with patch.object(n.os,'fsync',side_effect=OSError('injected')):self.assertRaises(OSError,n.save,doc(3),p)
            self.assertFalse(n.lock_path(p).exists()); self.assertEqual(p.read_bytes(),old)
            n.save(doc(3),p); self.assertEqual(n.load(p).value('x'),3)
    def test_spawned_writer_excludes_second_process(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; n.save(doc(),p); old=p.read_bytes(); ctx=mp.get_context('spawn'); entered=ctx.Event(); release=ctx.Event()
            worker=ctx.Process(target=hold_writer,args=(p,entered,release)); worker.start()
            try:
                self.assertTrue(entered.wait(15)); self.assertRaises(n.WriterBusyError,n.save,doc(4),p)
                self.assertEqual(p.read_bytes(),old); self.assertFalse(n.recovery_path(p).exists())
            finally:
                release.set(); worker.join(20)
                if worker.is_alive():worker.terminate();worker.join()
            self.assertEqual(worker.exitcode,0); self.assertEqual(n.load(p).value('x'),3); self.assertFalse(n.lock_path(p).exists())
    def test_crashed_writer_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; n.save(doc(),p); old=p.read_bytes(); worker=mp.get_context('spawn').Process(target=kill_writer,args=(p,));worker.start();worker.join(20)
            if worker.is_alive():worker.terminate();worker.join();self.fail('worker timeout')
            self.assertEqual(worker.exitcode,73); self.assertEqual(p.read_bytes(),old); self.assertTrue(n.lock_path(p).exists())
            self.assertRaises(n.WriterBusyError,n.save,doc(4),p)
            # Controlled test: we KNOW the writer terminated; explicit manual recovery.
            n.lock_path(p).unlink(); n.save(doc(4),p); self.assertEqual(n.load(p).value('x'),4)
    def test_v2_revision_and_migration(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; t=n.save(doc(),p); d,read=n.load_with_revision(p); self.assertEqual(t,read)
            u=d.upgraded(); t2=n.save(u,p,expected_revision=t,allow_upgrade=True)
            self.assertEqual(n.load_with_revision(p)[1],t2); self.assertEqual(n.recover(p).format_version,1)
            self.assertRaises(n.DiskRevisionConflict,n.save,u,p,expected_revision=t)
    def test_external_byte_change_conflicts_even_same_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; t=n.save(doc(),p); d,read=n.load_with_revision(p)
            p.write_bytes(p.read_bytes()+b'\n'); self.assertEqual(n.load(p).value('x'),2)
            self.assertRaises(n.DiskRevisionConflict,n.save,d,p,expected_revision=read)
            self.assertFalse(n.recovery_path(p).exists())
    def test_existing_lock_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m'; target=Path(td)/'target'; target.write_bytes(b'keep')
            try: n.lock_path(p).symlink_to(target)
            except OSError: self.skipTest('Symlink unavailable on this host')
            self.assertRaises(n.WriterBusyError,n.save,doc(),p); self.assertEqual(target.read_bytes(),b'keep');self.assertTrue(n.lock_path(p).is_symlink())
    def test_replaced_lock_not_removed(self):
        from goosecad.document.disk_lock import writer_lock
        if os.name!='posix':self.skipTest('POSIX open-inode replacement test')
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m';lock=n.lock_path(p)
            with self.assertRaises(n.WriterBusyError):
                with writer_lock(p):
                    lock.unlink();lock.write_bytes(b'other lock')
            self.assertEqual(lock.read_bytes(),b'other lock')

    def test_crash_matrix_existing_primary(self):
        for phase, expected_value in (("after_previous",2),("before_primary",2),
                                      ("after_primary",3)):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "part.gcad"
                n.save(doc(1), path)
                n.save(doc(2), path)
                old = path.read_bytes()
                run_crash(path, phase, True)
                self.assertTrue(n.lock_path(path).is_file())
                self.assertEqual(n.load(path).value("x"), expected_value)
                self.assertEqual(n.recovery_path(path).read_bytes(), old)
                self.assertEqual(n.recover(path).value("x"),2)
                primary = path.read_bytes()
                self.assertRaises(n.WriterBusyError,n.save,doc(4),path)
                self.assertEqual(path.read_bytes(), primary)
                # Copy recovery without changing the locked original.
                copy = Path(td) / "recovered.gcad"
                n.save(n.recover(path),copy,expected_revision=None)
                self.assertEqual(n.load(copy).value("x"),2)
                self.assertEqual(path.read_bytes(),primary)
                self.assertTrue(n.lock_path(path).exists())

    def test_crash_matrix_first_save(self):
        for phase, exists in (("before_primary",False),("after_primary",True)):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "new.gcad"
                run_crash(path,phase,False)
                self.assertEqual(path.exists(),exists)
                self.assertFalse(n.recovery_path(path).exists())
                self.assertTrue(n.lock_path(path).is_file())
                self.assertRaises(n.WriterBusyError,n.save,doc(4),path)
                if exists:
                    self.assertEqual(n.load(path).value("x"),3)

    def test_crash_autosave_slot_does_not_modify_original(self):
        from goosecad.document.session import DocumentSession
        from goosecad.document.autosave import AutosaveSlot, list_recoveries
        for phase, expected_value in (("before_primary",2),("after_primary",3)):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                original = root / "original.gcad"
                session = DocumentSession(doc(1))
                session.save_as(original)
                original_bytes = original.read_bytes()
                session.edit({"x":2})
                slot = AutosaveSlot(root / "recovery",session.document)
                slot.capture(session)
                run_crash(slot.path,phase,True)
                self.assertEqual(original.read_bytes(),original_bytes)
                self.assertEqual(n.load(original).value("x"),1)
                self.assertTrue(session.dirty)
                entries = list_recoveries(slot.root)
                self.assertEqual(len(entries),1)
                recovered = DocumentSession.open_copy(entries[0].path)
                self.assertEqual(recovered.document.value("x"),expected_value)
                self.assertIsNone(recovered.path)
                self.assertTrue(recovered.dirty)
                self.assertEqual(n.recover(slot.path).value("x"),2)
                self.assertTrue(n.lock_path(slot.path).exists())
                session.edit({"x":4})
                self.assertRaises(n.WriterBusyError,slot.capture,session)
                self.assertEqual(original.read_bytes(),original_bytes)
