"""Experimental single-threaded incremental DAG with atomic cache publication."""
from collections import defaultdict, deque
from dataclasses import dataclass

@dataclass(frozen=True)
class Node:
    dependencies: tuple
    compute: object

class EvaluationCancelled(RuntimeError):
    """Cooperative cancellation; staged results are not published."""

class Graph:
    def __init__(self):
        self._nodes = {}
        self._order = {}
        self._children = defaultdict(set)
        self._cache = {}
        self._dirty = set()
    def add(self, key, dependencies, compute):
        dependencies = tuple(dependencies)
        if key in self._nodes or any(d not in self._nodes for d in dependencies):
            raise ValueError('Duplicate node or unknown dependency')
        self._order[key] = len(self._nodes)
        self._nodes[key] = Node(dependencies, compute)
        for dep in dependencies:
            self._children[dep].add(key)
        self._dirty.add(key)
    def replace_compute(self, key, compute):
        node = self._nodes[key]
        self._nodes[key] = Node(node.dependencies, compute)
        queue = deque([key]); seen = {key}
        while queue:
            item = queue.popleft(); self._dirty.add(item)
            for child in self._children[item] - seen:
                seen.add(child); queue.append(child)
    def evaluate(self, cancelled=None):
        staged = {}; executed = []
        # Add only permits existing parents, so insertion order is topological.
        # Sort dirty keys only; avoid scanning independent clean nodes.
        for key in sorted(self._dirty, key=self._order.__getitem__):
            if cancelled is not None and cancelled():
                raise EvaluationCancelled()
            node = self._nodes[key]
            args = [staged[d] if d in staged else self._cache[d] for d in node.dependencies]
            staged[key] = node.compute(*args); executed.append(key)
        if cancelled is not None and cancelled():
            raise EvaluationCancelled()
        self._cache.update(staged)
        self._dirty.difference_update(staged)
        return tuple(executed)
    def value(self, key):
        if key in self._dirty:
            raise RuntimeError('Value is invalidated')
        return self._cache[key]
