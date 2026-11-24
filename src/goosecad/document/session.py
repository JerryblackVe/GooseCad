"""Document/view session controller for a future desktop user interface.

This module has no GUI toolkit dependency. A session owns one NativeDocument,
retains the exact disk revision token, and never overwrites a changed file
silently. The viewer is optional and remains owned by its creating thread.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from OCP.TopoDS import TopoDS_Shape
from goosecad.document.native import NativeDocument, load_with_revision, recover, save
from goosecad.view.scene import Scene, Selection


class SessionError(RuntimeError):
    pass


class UnsavedChanges(SessionError):
    pass


@dataclass(frozen=True, slots=True)
class BodySelection:
    body: str
    revision: int


class DocumentSession:
    """One in-memory document and its optimistic disk-save boundary.

    Undo/redo history belongs to NativeDocument and is not written to disk.
    A failed save retains the old token and dirty flag: an error can happen
    after a durable replace, so the user must explicitly reopen/reconcile.
    """

    def __init__(self, document, *, path=None, disk_revision=None):
        if not isinstance(document, NativeDocument):
            raise SessionError("Expected a NativeDocument")
        if disk_revision is not None and (
            type(disk_revision) is not str
            or len(disk_revision) != 64
            or any(c not in "0123456789abcdef" for c in disk_revision)
        ):
            raise SessionError("Invalid disk revision")
        if path is None and disk_revision is not None:
            raise SessionError("A disk revision requires a file path")
        self.document = document
        self.path = Path(path) if path is not None else None
        self.disk_revision = disk_revision
        self._clean_bytes = document.to_bytes()
        self._dirty = False
        self._requires_save = False
        self._observed_revision = document.revision
        self._scene = None
        self._visible = ()
        self._selection = None

    @classmethod
    def new(cls, document):
        """New user-authored data must be explicitly saved or discarded."""
        session = cls(document)
        session._requires_save = True
        return session

    @classmethod
    def open(cls, path):
        document, token = load_with_revision(path)
        return cls(document, path=path, disk_revision=token)

    @classmethod
    def open_recovery(cls, path):
        """Open the .previous file as an unsaved document, never as primary."""
        session = cls(recover(path))
        # Recovered data must be explicitly saved or discarded even if its
        # parameters were never edited after opening.
        session._requires_save = True
        return session

    @classmethod
    def open_copy(cls, path):
        """Read a native snapshot as an untitled, unsaved recovery document."""
        document, _ = load_with_revision(path)
        session = cls(document)
        session._requires_save = True
        return session

    @property
    def dirty(self):
        if self.document.revision != self._observed_revision:
            self._mutated()
        return self._dirty or self._requires_save

    @property
    def scene(self):
        return self._scene

    @property
    def visible_bodies(self):
        return self._visible

    @property
    def selection(self):
        selected = self._selection
        if type(selected) is BodySelection:
            if self.document.versioned_value(selected.body)[0] == selected.revision:
                return selected
        elif type(selected) is Selection and self._scene is not None:
            if self._scene.is_current_selection(selected):
                return selected
        self._selection = None
        return None

    def _mutated(self):
        self._dirty = self.document.to_bytes() != self._clean_bytes
        self._observed_revision = self.document.revision
        self._selection = None

    def edit(self, changes, *, expected_revision=None):
        result = self.document.edit(changes, expected_revision=expected_revision)
        self._mutated()
        return result

    def undo(self, *, expected_revision=None):
        result = self.document.undo(expected_revision=expected_revision)
        self._mutated()
        return result

    def redo(self, *, expected_revision=None):
        result = self.document.redo(expected_revision=expected_revision)
        self._mutated()
        return result

    def save(self, *, allow_upgrade=False):
        if self.path is None:
            raise SessionError("Use save_as for an unnamed document")
        token = save(self.document, self.path,
                     expected_revision=self.disk_revision,
                     allow_upgrade=allow_upgrade)
        self.disk_revision = token
        current = self.document.to_bytes()
        if sha256(current).hexdigest() != token:
            # A caller bypassed the session and mutated the document during save.
            # Re-read only this exceptional path to avoid lying about the saved state.
            disk_doc, disk_token = load_with_revision(self.path)
            if disk_token != token:
                self._dirty = True
                raise SessionError("Disk changed again during save; reconcile before editing")
            self._clean_bytes = disk_doc.to_bytes()
            self._dirty = current != self._clean_bytes
            self._observed_revision = self.document.revision
            raise SessionError("Document changed during save; reconcile local edits")
        self._clean_bytes = current
        self._dirty = False
        self._observed_revision = self.document.revision
        return token

    def save_as(self, path):
        """Create a new primary only; never replace an existing destination."""
        destination = Path(path)
        if self.path is not None and destination == self.path:
            raise SessionError("Use save for the current document")
        token = save(self.document, destination, expected_revision=None)
        self.path = destination
        self.disk_revision = token
        self._requires_save = False
        current = self.document.to_bytes()
        if sha256(current).hexdigest() != token:
            disk_doc, disk_token = load_with_revision(destination)
            if disk_token != token:
                self._dirty = True
                raise SessionError("Disk changed again during save-as")
            self._clean_bytes = disk_doc.to_bytes()
            self._dirty = current != self._clean_bytes
            self._observed_revision = self.document.revision
            raise SessionError("Document changed during save-as; reconcile local edits")
        self._clean_bytes = current
        self._dirty = False
        self._observed_revision = self.document.revision
        return token

    def reopen(self, *, discard_changes=False):
        """Return an independent session; leave this one untouched on failure."""
        if self.path is None:
            raise SessionError("Unnamed document has no primary to reopen")
        if self.dirty and not discard_changes:
            raise UnsavedChanges("Unsaved modifications require explicit discard")
        return self.open(self.path)

    def select_body(self, body):
        if type(body) is not str:
            raise SessionError("Body identifier must be a string")
        revision, value = self.document.versioned_value(body)
        if not isinstance(value, TopoDS_Shape):
            raise SessionError("Selection requires a B-Rep body")
        self._selection = BodySelection(body, revision)
        return self._selection

    def attach_scene(self, scene):
        if not isinstance(scene, Scene) or scene.document is not self.document:
            raise SessionError("Scene belongs to a different document")
        if self._scene is not None and self._scene is not scene:
            raise SessionError("Detach the previous scene first")
        self._scene = scene

    def detach_scene(self):
        """The caller is responsible for closing its VTK scene."""
        self._scene = None
        self._visible = ()
        self._selection = None

    def refresh(self, bodies):
        if self._scene is None:
            raise SessionError("No scene attached")
        bodies = tuple(bodies)
        changed = self._scene.refresh(bodies)
        self._visible = bodies
        self._selection = None
        return changed

    def publish_refresh(self, prepared):
        if self._scene is None:
            raise SessionError("No scene attached")
        changed = self._scene.publish(prepared)
        self._visible = prepared.request.bodies
        self._selection = None
        return changed

    def select_at(self, x, y):
        if self._scene is None:
            raise SessionError("No scene attached")
        self._selection = self._scene.select(x, y)
        return self.selection
