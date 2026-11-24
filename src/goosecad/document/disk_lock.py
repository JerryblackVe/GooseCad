"""Fail-closed cooperative writer lock, using atomic exclusive file creation.

All writers must use this protocol. A killed writer leaves its lock in place:
never auto-steal; manual recovery requires confirming no writer is active.
Trusted local directory only (not a hostile-directory or network-FS guarantee).
"""
from contextlib import contextmanager
import os
from pathlib import Path

LOCK_SUFFIX='.goosecad-lock'

class WriterBusyError(ValueError):
    """Another writer or a stale lock prevents saving."""


def lock_path(path):
    path=Path(path)
    return path.with_name(path.name+LOCK_SUFFIX)


@contextmanager
def writer_lock(path):
    lock=lock_path(path)
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise WriterBusyError('Document writer lock exists; verify no active writer before manual recovery') from exc
    # The exclusive directory entry is the lock, not its contents.
    try:
        identity=os.fstat(fd)
    except BaseException:
        os.close(fd)
        raise
    try:
        # Keep the descriptor open through the critical section, so its inode
        # cannot be recycled while we still own it (on local POSIX filesystems).
        yield
    finally:
        try:
            current=lock.lstat()
            owned=os.path.samestat(identity,current)
        finally:
            os.close(fd)
        if not owned:
            raise WriterBusyError('Writer lock was replaced externally; refusing to remove it')
        lock.unlink()
