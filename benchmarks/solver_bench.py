"""Partitioned vs dense solver with one BLAS thread (set before importing numpy)."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
import argparse,csv
from time import perf_counter_ns
from goosecad.constraints import Constraint as C,solve

def main():
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--repetitions',type=int,default=30);a=p.parse_args()
    if a.repetitions<1:p.error('positive repetitions required')
    with open(a.output,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['groups','mode','sample','elapsed_ns','dof','residual_mm','valid'])
        for groups in (1,10,50):
            points={f'p{i}':(i,i+1) for i in range(2*groups)}; cs=[C('horizontal',f'p{i}',f'p{i+1}') for i in range(0,2*groups,2)]
            for i in range(-3,a.repetitions):
                results=[]
                for mode,part in [('dense',False),('partitioned',True)]:
                    t=perf_counter_ns();r=solve(points,cs,partition=part);elapsed=perf_counter_ns()-t
                    valid=r.status=='solved' and r.dof==3*groups and r.max_residual<=1e-7
                    if not valid:raise RuntimeError('invalid solution')
                    results.append(r)
                    if i>=0:w.writerow([groups,mode,i,elapsed,r.dof,r.max_residual,valid])
                if any(abs(x-y)>1e-8 for k in points for x,y in zip(results[0].points[k],results[1].points[k])):raise RuntimeError('partition mismatch')
if __name__=='__main__': main()
