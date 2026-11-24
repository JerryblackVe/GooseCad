"""Reproducible paired full/incremental updates; graph construction excluded."""
import argparse
import csv
from time import perf_counter_ns
from goosecad.parametric import Graph, Input, Operation
from goosecad.geometry.kernel import box, properties


def branches(n):
    nodes=[]
    for i in range(n):
        nodes += [Input(f'p{i}',1),Operation(f'f{i}',(f'p{i}',),lambda x:x+1)]
    return Graph(nodes), 'p0', 'f0', lambda x:x+1, n


def chain(n):
    return Graph([Input('p',1)]+[Operation(f'f{i}',('p' if i==0 else f'f{i-1}',),lambda x:x+1) for i in range(n)]), 'p', f'f{n-1}', lambda x:x+n, n


def geometry(n):
    nodes=[]
    for i in range(n):
        nodes += [Input(f'p{i}',1),Operation(f'b{i}',(f'p{i}',),lambda x:box(x,2,3)),Operation(f'f{i}',(f'b{i}',),lambda b:properties(b).volume)]
    return Graph(nodes), 'p0','f0',lambda x:x*6,n*2


def main():
    p=argparse.ArgumentParser(); p.add_argument('output'); p.add_argument('--repetitions',type=int,default=50); args=p.parse_args()
    if args.repetitions<1: p.error('positive repetitions required')
    with open(args.output,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['case','size','mode','sample','elapsed_ns','evaluated','expected','valid'])
        for label,factory,n in [('branches',branches,100),('branches',branches,1000),('branches',branches,10000),('chain',chain,10000),('occt',geometry,20)]:
            g,source,target,expected,all_ops=factory(n)
            for i in range(-5,args.repetitions):
                for mode in ('incremental','full') if i%2 else ('full','incremental'):
                    value=2+(i%7); start=perf_counter_ns(); r=g.update({source:value},full=mode=='full'); dt=perf_counter_ns()-start
                    want=all_ops if mode=='full' or label=='chain' else (2 if label=='occt' else 1)
                    if abs(g.value(target)-expected(value))>1e-8 or len(r.evaluated)!=want: raise RuntimeError('incorrect result or invalidation')
                    if i>=0: w.writerow([label,n,mode,i,dt,len(r.evaluated),expected(value),True])

if __name__=='__main__': main()
