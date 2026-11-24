"""Single-worker document mutation, collected by the session's owning thread.

No Qt or VTK calls in the worker. While busy, callers must not access or
mutate the document/session/scene; document locks may wait for OCCT. A cancel
request is cooperative at DAG checkpoints, not a guaranteed rollback after
publication, and cannot interrupt an OCCT call already executing.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, get_ident
from pathlib import Path
from dataclasses import dataclass, replace

from goosecad.document.session import DocumentSession
from goosecad.parametric import Cancelled
from goosecad.view.preparation import DisplayConfig, MeshRequest, PreparedMeshes
from goosecad.document.autosave import AutosaveSlot
from goosecad.document.primitives import PrimitiveSpec


class TaskStateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LoadedView:
    session: DocumentSession
    prepared: PreparedMeshes


@dataclass(frozen=True, slots=True)
class MutationDisplay:
    report: object
    prepared: PreparedMeshes | None
    display_error: Exception | None = None


class DocumentTasks:
    """Own a reusable worker and at most one uncollected document operation."""

    def __init__(self, session, *, notify=None):
        self.session = session
        self._notify = notify
        self._owner = get_ident()
        self._executor = ThreadPoolExecutor(max_workers=1,
                                            thread_name_prefix="goosecad-document")
        self._future = None
        self._cancel = None
        self._kind = None
        self._closed = False

    def _check(self):
        if get_ident() != self._owner:
            raise TaskStateError("DocumentTasks must be controlled by its owning thread")
        if self._closed:
            raise TaskStateError("DocumentTasks is closed")

    @property
    def busy(self):
        self._check()
        return self._future is not None

    @property
    def ready(self):
        self._check()
        return self._future is not None and self._future.done()

    @property
    def kind(self):
        self._check()
        return self._kind

    @property
    def can_cancel(self):
        self._check()
        return self._cancel is not None and self._future is not None and not self._future.done()

    def _idle(self):
        self._check()
        if self._future is not None:
            raise TaskStateError("Collect the previous document operation first")

    def _submit(self, kind, method, args, *, token=None, kwargs=None):
        self._idle()
        self._future = self._executor.submit(method, *args, **(kwargs or {}))
        self._cancel = token
        self._kind = kind
        if self._notify is not None:
            self._future.add_done_callback(self._notify_done)

    def _notify_done(self, future):
        # May run on the worker or synchronously if already finished.
        # Callback must only enqueue a notification; it must not collect.
        self._notify()

    def _start(self, method, *args, expected_revision=None, display_request=None):
        self._idle()
        revision = self.session.document.revision if expected_revision is None else expected_revision
        token = Event()
        kwargs = {"expected_revision": revision, "cancelled": token.is_set}
        if display_request is None:
            self._submit("mutation", method, args, token=token, kwargs=kwargs)
            return
        if (type(display_request) is not MeshRequest
                or display_request.document is not self.session.document
                or display_request.revision != self.session.document.revision):
            raise TaskStateError("Invalid or stale display request")

        def mutate_and_prepare():
            # Failure before commit is propagated normally. Display failure
            # after commit is a distinct outcome; never promise a rollback.
            report = method(*args, **kwargs)
            try:
                plan = replace(display_request, revision=report.revision)
                prepared = plan.prepare(cancelled=token.is_set)
            except Exception as exc:
                return MutationDisplay(report, None, exc.with_traceback(None))
            return MutationDisplay(report, prepared)

        self._submit("mutation_display", mutate_and_prepare, (), token=token)

    def edit(self, changes, *, expected_revision=None, display_request=None):
        self._check()
        if type(changes) is not dict or any(type(k) is not str or
                type(v) not in (int, float) for k, v in changes.items()):
            raise TaskStateError("Expected a numeric parameter dictionary")
        self._start(self.session.document.edit, dict(changes),
                    expected_revision=expected_revision, display_request=display_request)

    def undo(self, *, display_request=None):
        self._start(self.session.document.undo, display_request=display_request)

    def redo(self, *, display_request=None):
        self._start(self.session.document.redo, display_request=display_request)

    def open(self, path, *, recovery=False, recovery_copy=False, display_config=None):
        """Load an independent candidate. Never replace the active session here."""
        self._idle()
        source = Path(path)
        if recovery and recovery_copy:
            raise TaskStateError('Ambiguous recovery source')
        if display_config is not None and type(display_config) is not DisplayConfig:
            raise TaskStateError('Invalid initial display configuration')
        token = Event()
        def load_candidate():
            if token.is_set():
                raise Cancelled("Opening cancelled")
            loader = (DocumentSession.open_recovery if recovery else
                      DocumentSession.open_copy if recovery_copy else DocumentSession.open)
            candidate = loader(source)
            if token.is_set():
                raise Cancelled("Opening cancelled")
            if display_config is not None:
                prepared = display_config.initial_request(candidate.document).prepare(cancelled=token.is_set)
                return LoadedView(candidate, prepared)
            return candidate
        self._submit("recovery" if recovery or recovery_copy else "open", load_candidate, (), token=token)

    def create_primitive(self, spec, *, display_config):
        self._idle()
        if type(spec) is not PrimitiveSpec or type(display_config) is not DisplayConfig:
            raise TaskStateError("Invalid new primitive request")
        token = Event()
        def create_candidate():
            if token.is_set():
                raise Cancelled("Creation cancelled")
            candidate = DocumentSession.new(spec.build())
            if token.is_set():
                raise Cancelled("Creation cancelled")
            prepared = display_config.initial_request(candidate.document).prepare(cancelled=token.is_set)
            return LoadedView(candidate,prepared)
        self._submit("new",create_candidate,(),token=token)

    def prepare_meshes(self, request):
        self._idle()
        if request.document is not self.session.document:
            raise TaskStateError("Mesh request belongs to another document")
        token = Event()
        self._submit("mesh", request.prepare, (), token=token,
                     kwargs={"cancelled": token.is_set})

    def save(self):
        """Exclusive session access; retain the existing disk CAS semantics.

        No cancellation of a disk transaction: a durable replace may already
        have happened when cancellation is requested.
        """
        self._submit("save", self.session.save, ())

    def save_as(self, path):
        self._idle()
        self._submit("save", self.session.save_as, (Path(path),))

    def autosave(self, slot):
        self._idle()
        if not isinstance(slot, AutosaveSlot) or slot.document is not self.session.document:
            raise TaskStateError("Invalid autosave slot")
        self._submit("autosave", slot.capture, (self.session,))

    def request_cancel(self):
        self._check()
        if not self.can_cancel:
            return False
        self._cancel.set()
        return True

    def collect(self):
        """Never wait for the worker. Return None if still running or idle.

        Reconcile the session dirty flag on its owner after publication. A
        worker error is raised here; on DAG cancellation there is no change.
        """
        self._check()
        if not self.ready:
            return None
        future = self._future
        self._future = self._cancel = None
        self._kind = None
        try:
            return future.result()
        finally:
            # Trigger the existing revision observer without touching VTK.
            self.session.dirty

    def close(self):
        self._check()
        if self._future is not None:
            raise TaskStateError("Collect the document operation before closing")
        self._executor.shutdown(wait=True)
        self._closed = True
