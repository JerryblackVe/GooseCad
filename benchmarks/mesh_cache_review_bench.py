"""Paired cache regression after GC-MESH-01 review; run in a Git checkout."""
import argparse
import csv
import statistics
import subprocess
import time
from unittest.mock import patch

import numpy as np

from mesh_review_bench import load
from goosecad.document.native import Feature, NativeDocument
from goosecad.geometry import mesh, mesh_cache
from goosecad.geometry.mesh_cache import MeshCache, MeshSettings


def model(n):
    ids = [f's{i}' for i in range(n)]
    doc = NativeDocument({f'r{i}': 5 for i in range(n)},
                         tuple(Feature(k, 'sphere', (f'r{i}',)) for i, k in enumerate(ids)))
    return doc, MeshCache(doc), ids


def equal(a, b):
    np.testing.assert_array_equal(a.vertices, b.vertices)
    np.testing.assert_array_equal(a.triangles, b.triangles)
    assert a.face_offsets == b.face_offsets


def measure(doc, cache, ids, settings, fn, radius):
    doc.edit({'r0': radius})
    t = time.perf_counter_ns()
    direct = [fn(doc.value(k), linear=settings.linear, angular=settings.angular) for k in ids]
    elapsed = {'rebuild': (time.perf_counter_ns()-t)/1e6}
    snapshots = {}
    with patch.object(mesh_cache, 'tessellate', fn):
        for mode in ('selective', 'warm'):
            t = time.perf_counter_ns()
            snaps = [cache.get(k, settings) for k in ids]
            elapsed[mode] = (time.perf_counter_ns()-t)/1e6
            snapshots[mode] = snaps
            for expected, snap in zip(direct, snaps):
                assert cache.is_current(snap)
                equal(expected, snap.mesh)
    assert all(a is b for a, b in zip(snapshots['selective'], snapshots['warm']))
    return elapsed, direct, cache.info().bytes


def main():
    p = argparse.ArgumentParser()
    p.add_argument('output')
    p.add_argument('--baseline', default='afad1c07f827b899cc9e1fc688a1c0b9f3036632')
    p.add_argument('--repetitions', type=int, default=20)
    a = p.parse_args()
    if a.repetitions < 1:
        p.error('Positive repetitions required')
    source = subprocess.check_output(['git', 'show', a.baseline+':src/goosecad/geometry/mesh.py'], text=True)
    old = load(source, 'mesh_cache_review_baseline')
    modes = [('baseline', old.tessellate), ('optimized', mesh.tessellate)]
    settings = MeshSettings(linear=.05, angular=.3)
    with open(a.output, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['bodies', 'implementation', 'mode', 'sample', 'ms', 'retained_bytes', 'triangles'])
        for n in (1, 20):
            states = {label: model(n) for label, _ in modes}
            measurements = {}
            for i in range(-3, a.repetitions):
                direct = {}
                for label, fn in modes[::(-1 if i%2 else 1)]:
                    elapsed, meshes, cost = measure(*states[label], settings, fn, 5+(i%2))
                    direct[label] = meshes
                    if i >= 0:
                        for mode, ms in elapsed.items():
                            measurements.setdefault((label, mode), []).append(ms)
                            w.writerow([n, label, mode, i, ms, cost, sum(len(m.triangles) for m in meshes)])
                for x, y in zip(direct['baseline'], direct['optimized']):
                    equal(x, y)
            print(n, {k: (round(statistics.median(v), 5), round(float(np.percentile(v,95)), 5)) for k,v in measurements.items()}, flush=True)


if __name__ == '__main__':
    main()
