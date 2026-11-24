"""Deterministic incremental DAG. Fixed structure; values published transactionally.

Values and callback outputs are borrowed, read-only by contract (including OCCT
shapes). Callbacks must be pure, must not mutate inputs or graph state, and
must not wait on another thread accessing this graph. No parallel execution yet.
"""
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from threading import RLock
from typing import Any


class GraphError(ValueError):
    pass


class EvaluationError(GraphError):
    def __init__(self, node: str):
        self.node = node
        super().__init__(f"Evaluation failed at {node!r}")


class Cancelled(GraphError):
    pass


@dataclass(frozen=True, slots=True)
class Input:
    id: str
    value: Any


@dataclass(frozen=True, slots=True)
class Operation:
    id: str
    dependencies: tuple[str, ...]
    compute: Callable[..., Any]


@dataclass(frozen=True, slots=True)
class UpdateReport:
    revision: int
    changed_inputs: tuple[str, ...]
    evaluated: tuple[str, ...]


class Graph:
    """Fixed DAG, forward references allowed. One serialized writer, atomic reads.

    Every explicit update invalidates its descendants, even for equal values:
    no approximate equality, implicit hashing, or hidden mutable cache keys.
    Structural edits require building a new graph. Cancellation is cooperative
    between operations; callbacks cannot be interrupted mid-computation.
    """
    def __init__(self, nodes: Iterable[Input | Operation]):
        specs = {}
        for node in nodes:
            if not isinstance(node, (Input, Operation)) or not isinstance(node.id, str) or not node.id:
                raise GraphError("Each node needs a nonempty string identifier")
            if node.id in specs:
                raise GraphError(f"Duplicate node: {node.id}")
            if isinstance(node, Operation):
                if not isinstance(node.dependencies, tuple) or not all(isinstance(d, str) for d in node.dependencies) or not callable(node.compute):
                    raise GraphError(f"Invalid operation: {node.id}")
                if len(set(node.dependencies)) != len(node.dependencies):
                    raise GraphError(f"Duplicate dependency: {node.id}")
            specs[node.id] = node
        successors = {name: [] for name in specs}
        indegree = {name: 0 for name in specs}
        for node in specs.values():
            if isinstance(node, Operation):
                for dep in node.dependencies:
                    if dep not in specs:
                        raise GraphError(f"Unknown dependency: {dep}")
                    successors[dep].append(node.id)
                    indegree[node.id] += 1
        ready = deque(n for n in specs if not indegree[n])
        order = []
        while ready:
            name = ready.popleft()
            order.append(name)
            for child in successors[name]:
                indegree[child] -= 1
                if not indegree[child]:
                    ready.append(child)
        if len(order) != len(specs):
            raise GraphError("Circular dependency")
        self._names = tuple(order)
        self._index = {name: i for i, name in enumerate(order)}
        self._successors = tuple(tuple(self._index[c] for c in successors[n]) for n in order)
        self._ops = {self._index[n]: (tuple(self._index[d] for d in s.dependencies), s.compute)
                     for n, s in specs.items() if isinstance(s, Operation)}
        self._op_order = tuple(sorted(self._ops))
        self._inputs = frozenset(self._index[n] for n, s in specs.items() if isinstance(s, Input))
        self._values = [None] * len(order)
        for n, s in specs.items():
            if isinstance(s, Input):
                self._values[self._index[n]] = s.value
        self._lock = RLock()
        self._busy = False
        self._revision = 0
        self.update({}, full=True)

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def value(self, name: str) -> Any:
        with self._lock:
            return self._values[self._index[name]]

    def snapshot(self) -> tuple[int, dict[str, Any]]:
        """Consistent revision and shallow, borrowed read-only values."""
        with self._lock:
            return self._revision, dict(zip(self._names, self._values))

    def update(self, changes: Mapping[str, Any], *, full: bool = False,
               cancelled: Callable[[], bool] | None = None) -> UpdateReport:
        with self._lock:
            if self._busy:
                raise GraphError("Reentrant mutation is forbidden")
            self._busy = True
            try:
                return self._update(changes, full, cancelled)
            finally:
                self._busy = False

    def _update(self, changes, full, cancelled):
        def check_cancel():
            if cancelled is not None and cancelled():
                raise Cancelled("Calculation cancelled before publication")

        staged = {}
        for name, value in changes.items():
            idx = self._index.get(name)
            if idx not in self._inputs:
                raise GraphError(f"Not an input: {name!r}")
            staged[idx] = value
        changed = tuple(self._names[i] for i in sorted(staged))
        check_cancel()
        if full:
            dirty = self._op_order
        else:
            # Only visit descendants, not the entire graph. Iterative for deep DAGs.
            visited = set(staged)
            pending = list(staged)
            dirty = []
            while pending:
                i = pending.pop()
                for child in self._successors[i]:
                    if child not in visited:
                        visited.add(child)
                        pending.append(child)
                        dirty.append(child)
            if len(dirty) == len(self._op_order):
                dirty = self._op_order
            else:
                dirty.sort()
        values = self._values
        for i in dirty:
            check_cancel()
            deps, compute = self._ops[i]
            try:
                if len(deps) == 1:
                    d = deps[0]
                    staged[i] = compute(staged.get(d, values[d]))
                else:
                    staged[i] = compute(*(staged.get(d, values[d]) for d in deps))
            except Exception as exc:
                raise EvaluationError(self._names[i]) from exc
        check_cancel()
        # Prepare report before commit; no user callbacks during publication.
        report = UpdateReport(self._revision + bool(staged), changed, tuple(self._names[i] for i in dirty))
        # Keep replaced values alive until entire publication is visible, avoiding
        # destructor reentry observing a partially updated graph.
        replaced = [values[i] for i in staged]
        for i, value in staged.items():
            values[i] = value
        self._revision = report.revision
        return report
