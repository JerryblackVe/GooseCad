"""Bounded parameter and append-only structural history; no disk persistence.

Inputs are immutable JSON scalar values. Computed objects remain borrowed,
read-only by contract. The document exclusively owns its graph. Undo/redo
recompute affected nodes rather than keeping copies of large B-Rep results.
"""
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from threading import RLock
from typing import Any

from goosecad.parametric import Graph, Input, Operation, UpdateReport

Scalar = int | float | str | bool | None


class DocumentError(ValueError):
    pass


class RevisionConflict(DocumentError):
    pass


def _scalar(value: Any) -> Scalar:
    if type(value) not in (int, float, str, bool, type(None)):
        raise DocumentError("Document parameters must be immutable JSON scalars")
    if type(value) is float and not isfinite(value):
        raise DocumentError("Nonfinite parameter")
    return value


@dataclass(frozen=True, slots=True)
class _Patch:
    before: dict[str, Scalar]
    after: dict[str, Scalar]


@dataclass(frozen=True, slots=True)
class _StructurePatch:
    before: tuple[Input | Operation, ...]
    after: tuple[Input | Operation, ...]


@dataclass(frozen=True, slots=True)
class DocumentSnapshot:
    revision: int
    values: dict[str, Any]
    undo_depth: int
    redo_depth: int


class Document:
    def __init__(self, nodes: Iterable[Input | Operation], *, history_limit: int = 100):
        if type(history_limit) is not int or history_limit < 0:
            raise DocumentError("History limit must be a nonnegative integer")
        nodes = tuple(nodes)
        self._nodes = nodes
        self._inputs = frozenset(n.id for n in nodes if isinstance(n, Input))
        for n in nodes:
            if isinstance(n, Input): _scalar(n.value)
        self._graph = Graph(nodes)
        self._limit = history_limit
        self._undo: tuple[_Patch | _StructurePatch, ...] = ()
        self._redo: tuple[_Patch | _StructurePatch, ...] = ()
        self._lock = RLock()
        self._busy = False

    @property
    def revision(self) -> int:
        with self._lock: return self._graph.revision

    def value(self, name: str) -> Any:
        with self._lock: return self._graph.value(name)

    def versioned_value(self, name: str) -> tuple[int, Any]:
        with self._lock: return self._graph.versioned_value(name)

    @property
    def history_depths(self) -> tuple[int, int]:
        """Avoid copying the graph or geometry merely to enable UI actions."""
        with self._lock:
            return len(self._undo), len(self._redo)

    @property
    def nodes(self):
        with self._lock:
            return self._nodes

    def _replace_structure(self, nodes, undo, redo, cancelled):
        self._busy = True
        try:
            graph = self._graph._reconfigure(nodes, cancelled=cancelled)
            inputs = frozenset(n.id for n in nodes if isinstance(n, Input))
            old_ids = {v.id for v in self._nodes}
            added = tuple(n for n in nodes if n.id not in old_ids)
            report = UpdateReport(graph.revision,
                                  tuple(n.id for n in added if isinstance(n, Input)),
                                  tuple(n.id for n in added if isinstance(n, Operation)))
            self._graph, self._nodes, self._inputs = graph, nodes, inputs
            self._undo, self._redo = undo, redo
            return report
        finally:
            self._busy = False

    def append(self, nodes, *, expected_revision=None, cancelled=None):
        """Append definitions as one transaction; no arbitrary deletion/rewrite."""
        with self._lock:
            self._check(expected_revision)
            self._busy = True
            try:
                extra = tuple(nodes)
                if not extra:
                    raise DocumentError("Expected appended nodes")
                for node in extra:
                    if isinstance(node, Input):
                        _scalar(node.value)
                after = self._nodes + extra
                patch = _StructurePatch(self._nodes, after)
                undo = (*self._undo, patch)[-self._limit:] if self._limit else ()
                return self._replace_structure(after, undo, (), cancelled)
            finally:
                self._busy = False

    def snapshot(self) -> DocumentSnapshot:
        with self._lock:
            revision, values = self._graph.snapshot()
            return DocumentSnapshot(revision, values, len(self._undo), len(self._redo))

    def _check(self, expected_revision: int | None):
        if self._busy: raise DocumentError("Reentrant document mutation")
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision != self._graph.revision):
            raise RevisionConflict("Document revision changed")

    def _apply(self, changes, undo, redo, cancelled):
        # History tuples prepared before graph publication. No further computation
        # or external callback between graph commit and history publication.
        self._busy = True
        try:
            report = self._graph.update(changes, cancelled=cancelled)
            self._undo, self._redo = undo, redo
            return report
        finally:
            self._busy = False

    def edit(self, changes: Mapping[str, Scalar], *, expected_revision: int | None = None,
             cancelled: Callable[[], bool] | None = None) -> UpdateReport:
        with self._lock:
            self._check(expected_revision)
            # A Mapping may execute user code during iteration. Reject reentrant
            # mutation from the beginning of validation, not just during evaluation.
            self._busy = True
            try:
                after = dict(changes)
                before = {}
                for name, value in after.items():
                    if type(name) is not str or name not in self._inputs:
                        raise DocumentError(f"Not an input: {name!r}")
                    _scalar(value)
                    before[name] = self._graph.value(name)
                if not after:
                    return self._apply({}, self._undo, self._redo, cancelled)
                # Explicit edits (even identical values) are recorded, as in Graph.
                undo = (*self._undo, _Patch(before, after))[-self._limit:] if self._limit else ()
                return self._apply(after, undo, (), cancelled)
            finally:
                self._busy = False

    def undo(self, *, expected_revision: int | None = None, cancelled: Callable[[], bool] | None = None) -> UpdateReport:
        with self._lock:
            self._check(expected_revision)
            if not self._undo: raise DocumentError("Nothing to undo")
            patch = self._undo[-1]
            if isinstance(patch, _StructurePatch):
                return self._replace_structure(patch.before, self._undo[:-1], (*self._redo, patch), cancelled)
            return self._apply(patch.before, self._undo[:-1], (*self._redo, patch), cancelled)

    def redo(self, *, expected_revision: int | None = None, cancelled: Callable[[], bool] | None = None) -> UpdateReport:
        with self._lock:
            self._check(expected_revision)
            if not self._redo: raise DocumentError("Nothing to redo")
            patch = self._redo[-1]
            if isinstance(patch, _StructurePatch):
                return self._replace_structure(patch.after, (*self._undo, patch), self._redo[:-1], cancelled)
            return self._apply(patch.after, (*self._undo, patch), self._redo[:-1], cancelled)
