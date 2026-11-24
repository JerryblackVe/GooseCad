"""Single-worker document mutation, collected by the session's owning thread.

No Qt or VTK calls in the worker. While busy, callers must not access or
mutate the document/session/scene; document locks may wait for OCCT. A cancel
request is cooperative at DAG checkpoints, not a guaranteed rollback after
publication, and cannot interrupt an OCCT call already executing.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, get_ident


class TaskStateError(RuntimeError):
    pass


class DocumentTasks:
    """Own a reusable worker and at most one uncollected document operation."""

    def __init__(self, session):
        self.session = session
        self._owner = get_ident()
        self._executor = ThreadPoolExecutor(max_workers=1,
                                            thread_name_prefix="goosecad-document")
        self._future = None
        self._cancel = None
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

    def _start(self, method, *args, expected_revision=None):
        self._check()
        if self._future is not None:
            raise TaskStateError("Collect the previous document operation first")
        revision = self.session.document.revision if expected_revision is None else expected_revision
        token = Event()
        future = self._executor.submit(method, *args, expected_revision=revision,
                                       cancelled=token.is_set)
        self._cancel = token
        self._future = future

    def edit(self, changes, *, expected_revision=None):
        self._check()
        if type(changes) is not dict or any(type(k) is not str or
                type(v) not in (int, float) for k, v in changes.items()):
            raise TaskStateError("Expected a numeric parameter dictionary")
        self._start(self.session.document.edit, dict(changes), expected_revision=expected_revision)

    def undo(self):
        self._start(self.session.document.undo)

    def redo(self):
        self._start(self.session.document.redo)

    def request_cancel(self):
        self._check()
        if self._future is None or self._future.done():
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
