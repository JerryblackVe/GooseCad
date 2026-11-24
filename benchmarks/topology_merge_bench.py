"""Measure batch merge resolution and semantic reference restoration."""
import csv
import json
import statistics
import sys
from time import perf_counter_ns
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from goosecad.geometry.topology import HistoryResolver, Reference, Status, box_roles


def main(path):
    a, b = BRepPrimAPI_MakeBox(10,10,10), BRepPrimAPI_MakeBox(gp_Pnt(10,0,0),10,10,10)
    a.Build(); b.Build()
    op = BRepAlgoAPI_Fuse(a.Shape(), b.Shape()); op.SimplifyResult(True, True)
    r = HistoryResolver(op)
    sources = {'a': box_roles(a)['z+'], 'b': box_roles(b)['z+']}
    features = {'a': box_roles(a)}
    record = json.dumps(Reference('a','z+').to_record())
    def merge():
        result = r.resolve_many(sources)
        assert all(x.status == Status.MERGED for x in result.values())
    def restore():
        result = Reference.from_record(json.loads(record)).bind(features)
        assert result.status == Status.RESOLVED
    with open(path,'w',newline='') as f:
        w = csv.writer(f,lineterminator='\n'); w.writerow(['case','sample','ms'])
        for name, run in [('merge_two_faces',merge),('restore_reference',restore)]:
            for _ in range(10): run()
            times=[]
            for i in range(100):
                t=perf_counter_ns(); run(); dt=(perf_counter_ns()-t)/1e6
                times.append(dt); w.writerow([name,i,dt])
            print(name, statistics.median(times), sorted(times)[94], statistics.stdev(times))

if __name__=='__main__': main(sys.argv[1])
