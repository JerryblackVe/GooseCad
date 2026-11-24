"""Native append/undo/redo vs reconstructing the equivalent complete model."""
import csv
import math
import os
import platform
import statistics
import sys
import tracemalloc
from time import perf_counter_ns

from goosecad.document.native import NativeDocument, Feature
from goosecad.document.primitives import PrimitiveSpec
from goosecad.geometry.kernel import properties


def base(count):
    params={f"r{i}":6+i/10 for i in range(count)}
    features=tuple(Feature(f"s{i}","sphere",(f"r{i}",)) for i in range(count))
    return NativeDocument(params,features)


def sample(count):
    doc=base(count)
    before=doc.to_bytes()
    values=doc.parameter_values()
    features=doc.features
    old_stamp,old_shape=doc.versioned_value("s0")
    spec=PrimitiveSpec("sphere",(7,))
    begin=perf_counter_ns()
    spec.append_to(doc)
    appended=perf_counter_ns()
    assert doc.versioned_value("s0")[0]==old_stamp
    assert doc.value("s0") is old_shape
    assert math.isclose(properties(doc.value("sphere")).volume,4*math.pi*7**3/3,rel_tol=1e-9)
    after=doc.to_bytes()
    begin_undo=perf_counter_ns()
    doc.undo()
    undo=perf_counter_ns()
    assert doc.to_bytes()==before
    begin_redo=perf_counter_ns()
    doc.redo()
    redo=perf_counter_ns()
    assert doc.to_bytes()==after
    assert doc.value("s0") is old_shape
    begin_rebuild=perf_counter_ns()
    rebuilt=NativeDocument({**values,"sphere_radius":7},
                    features+(Feature("sphere","sphere",("sphere_radius",)),))
    rebuild=perf_counter_ns()
    assert rebuilt.to_bytes()==after
    return ((appended-begin)/1e6,(undo-begin_undo)/1e6,
            (redo-begin_redo)/1e6,(rebuild-begin_rebuild)/1e6)


def memory(count):
    doc=base(count)
    tracemalloc.start()
    try:
        PrimitiveSpec("sphere",(7,)).append_to(doc)
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def main(path):
    rows=[]
    for count in (20,100):
        for index in range(13):
            values=sample(count)
            if index>=3:
                rows.append((count,index-3,*values,platform.platform(),
                             platform.processor() or "unknown",os.cpu_count(),
                             sys.version.split()[0]))
        peak=memory(count)
        print(f"structure {count}: Python traced peak append bytes={peak}; excludes OCCT native allocations")
        selected=[r for r in rows if r[0]==count]
        for col,label in ((2,"append"),(3,"undo"),(4,"redo"),(5,"rebuild")):
            values=[r[col] for r in selected]
            p95=statistics.quantiles(values,n=100,method="inclusive")[94]
            print(f"structure {count} {label}: n={len(values)} median={statistics.median(values):.6f} p95={p95:.6f}",flush=True)
    with open(path,"w",encoding="utf-8",newline="") as out:
        writer=csv.writer(out)
        writer.writerow(("existing_bodies","sample","append_ms","undo_ms","redo_ms",
                         "rebuild_ms","platform","cpu","logical_cpus","python"))
        writer.writerows(rows)


if __name__=="__main__":
    main(sys.argv[1])
