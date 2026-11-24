"""Run in fresh process: PYTHONPATH=src python benchmarks/kernel_bench.py results/run.csv."""
import csv, gc, math, os, platform, statistics, sys, time
from pathlib import Path
from OCP import __version__ as occt_version
from goosecad.geometry.kernel import box, cylinder, sphere, boolean, properties

def main(path):
    a, b = box(10,10,10), box(10,10,10,(5,0,0))
    cases = [('box',lambda:box(10,20,30),6000,False),('cylinder',lambda:cylinder(2,5),20*math.pi,False),('sphere',lambda:sphere(3),36*math.pi,False)]
    for op, v in [('union',1500),('cut',500),('common',500)]:
        for p in [False,True]:
            cases.append((op,lambda op=op,p=p:boolean(op,a,b,parallel=p),v,p))
    rows=[]
    for name, fun, expected, parallel in cases:
        for _ in range(5): fun()
        gc.collect()
        for sample in range(50):
            t=time.perf_counter_ns(); shape=fun(); elapsed=(time.perf_counter_ns()-t)/1e6
            p=properties(shape) # independent verification outside timed call
            if not math.isclose(p.volume,expected,rel_tol=1e-10) or p.solids!=1:
                raise RuntimeError(f'Geometry mismatch: {name}, {p}')
            rows.append([name,parallel,sample,elapsed,p.volume,p.solids,'valid'])
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(['case','parallel','sample','ms','volume_mm3','solids','validation']);w.writerows(rows)
    print(platform.platform(),sys.version.split()[0],occt_version, 'logical_cpu',os.cpu_count())
    for name,_,_,parallel in cases:
        vals=sorted(r[3] for r in rows if r[0]==name and r[1]==parallel)
        print(f'{name:10s} parallel={str(parallel):5s} median={statistics.median(vals):.4f} ms p95={vals[math.ceil(.95*len(vals))-1]:.4f} ms')

if __name__=='__main__': main(Path(sys.argv[1]))
