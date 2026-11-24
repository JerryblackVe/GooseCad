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
