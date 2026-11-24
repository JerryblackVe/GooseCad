"""Measure indexed history resolution, excluding Boolean construction."""
import csv, statistics, time, sys
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from goosecad.geometry.kernel import box
from goosecad.geometry.topology import HistoryResolver, box_roles, Status

def main(path):
    b=BRepPrimAPI_MakeBox(10,10,10); b.Build()
    roles=box_roles(b); op=BRepAlgoAPI_Cut(b.Shape(),box(2,20,20,(4,-5,-5)))
    r=HistoryResolver(op)
    def run():
        results=[r.resolve(s) for s in roles.values()]
        assert sum(x.status==Status.AMBIGUOUS for x in results)==4
    for _ in range(10): run()
    vals=[]
    for i in range(100):
        t=time.perf_counter_ns(); run(); vals.append((time.perf_counter_ns()-t)/1e6)
    with open(path,'w',newline='') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(['sample','ms','faces','validation']);w.writerows((i,v,6,'valid') for i,v in enumerate(vals))
    print(f'median_ms={statistics.median(vals):.6f} p95_ms={sorted(vals)[94]:.6f}')
if __name__=='__main__': main(sys.argv[1])
