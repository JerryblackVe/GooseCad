"""Independent, bounded recovery slots for committed native document state.

A slot never writes to the user's primary path or changes the session's dirty
flag/disk token. Existing native CAS and atomic replacement are reused. Copies
are retained until the user explicitly removes them; no silent eviction.
The recovery root must be a trusted local directory, not a hostile/network FS.
"""
from dataclasses import dataclass
from pathlib import Path
import re
import stat
import os
from tempfile import mkdtemp
from uuid import uuid4
from goosecad.document.native import NativeDocument, save, recovery_path, _sync_dir
from goosecad.document.disk_lock import lock_path, writer_lock


MAX_SLOTS = 128
_NAME = re.compile(r"recovery-[0-9a-f]{32}\.gcad")
_PREVIOUS = '.previous'


class AutosaveError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RecoveryEntry:
    path: Path
    modified_ns: int
    size: int


def _check_root(root):
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise AutosaveError("Recovery root must be a real directory")


def list_recoveries(root):
    root = Path(root)
    _check_root(root)
    if not root.exists():
        return ()
    entries = []
    for path in root.iterdir():
        if not _NAME.fullmatch(path.name):
            continue
        try:
            st = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISREG(st.st_mode):
            entries.append(RecoveryEntry(path, st.st_mtime_ns, st.st_size))
    return tuple(sorted(entries, key=lambda item: (item.modified_ns,item.path.name),
                        reverse=True))


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    path: Path
    primary: Path
    previous: bool
    locked: bool
    size: int
    modified_ns: int
    identity: tuple[int, int, int, int, int]


def _identity(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def recovery_catalog(root):
    """Metadata only; do not evaluate native geometry to populate a dialog."""
    root = Path(root).absolute()
    _check_root(root)
    if not root.exists():
        return ()
    entries = []
    for path in root.iterdir():
        previous = path.name.endswith(_PREVIOUS)
        name = path.name[:-len(_PREVIOUS)] if previous else path.name
        if not _NAME.fullmatch(name):
            continue
        try:
            st = path.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(st.st_mode):
            continue
        primary = root / name
        # A symlink or any other lock entry also counts as locked.
        try:
            lock_path(primary).lstat()
            locked = True
        except FileNotFoundError:
            locked = False
        entries.append(CatalogEntry(path, primary, previous, locked, st.st_size,
                                    st.st_mtime_ns, _identity(st)))
    return tuple(sorted(entries, key=lambda e: (e.modified_ns,e.path.name), reverse=True))


def archive_recovery(root, entry, *, active_path=None):
    """Explicit move of one catalog entry to a unique local archive directory.

    Never deletes file contents or clears writer locks. An idle external slot
    may later detect a missing primary via CAS; this operation is therefore
    only for copies the user explicitly chooses to retire. Metadata identity
    is rechecked under the same cooperative lock as native saves.
    """
    root = Path(root).absolute()
    _check_root(root)
    if type(entry) is not CatalogEntry or entry.primary.parent != root:
        raise AutosaveError("Invalid recovery catalog entry")
    if not _NAME.fullmatch(entry.primary.name):
        raise AutosaveError("Invalid recovery name")
    expected = recovery_path(entry.primary) if entry.previous else entry.primary
    if entry.path != expected:
        raise AutosaveError("Invalid recovery path")
    if active_path is not None and Path(active_path).absolute() == entry.primary:
        raise AutosaveError("Cannot archive the active recovery slot")
    with writer_lock(entry.primary):
        st = entry.path.lstat()
        if not stat.S_ISREG(st.st_mode) or _identity(st) != entry.identity:
            raise AutosaveError("Recovery copy changed; refresh the catalog")
        archive = root / "archive"
        _check_root(archive)
        archive.mkdir(mode=0o700, exist_ok=True)
        _check_root(archive)
        destination_dir = Path(mkdtemp(prefix="slot-", dir=archive))
        destination = destination_dir / entry.path.name
        # Directory created exclusively on this volume, destination absent.
        os.replace(entry.path, destination)
        _sync_dir(destination_dir)
        _sync_dir(archive)
        _sync_dir(root)
        return destination


class AutosaveSlot:
    """One private recovery path per in-memory document; worker-owned capture."""

    def __init__(self, root, document):
        if not isinstance(document, NativeDocument):
            raise AutosaveError("Expected native document")
        self.document = document
        self.root = Path(root).absolute()
        self.path = self.root / f"recovery-{uuid4().hex}.gcad"
        self._disk_revision = None
        self._last_revision = None

    @property
    def last_revision(self):
        return self._last_revision

    def capture(self, session):
        if session.document is not self.document:
            raise AutosaveError("Recovery slot belongs to another document")
        revision = self.document.revision
        if not session.dirty or revision == self._last_revision:
            return None
        if session.path is not None and session.path.absolute() == self.path:
            raise AutosaveError("Recovery path must not be the primary path")
        _check_root(self.root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        _check_root(self.root)
        if self._disk_revision is None and len(list_recoveries(self.root)) >= MAX_SLOTS:
            raise AutosaveError("Recovery directory is full; retain or remove old copies manually")
        # A CAS failure or uncertain durable replace does not advance the token.
        token = save(self.document, self.path, expected_revision=self._disk_revision)
        self._disk_revision = token
        if self.document.revision != revision:
            # Exclusive access is required. Leave the written copy intact but
            # do not claim that the current revision was captured.
            raise AutosaveError("Document changed during recovery capture")
        self._last_revision = revision
        return self.path
