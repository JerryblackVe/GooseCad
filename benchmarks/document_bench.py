"""Bounded parameter-history overhead, no geometry copies; paired scalar models."""
import argparse,csv
from time import perf_counter_ns
from goosecad.document import Document
from goosecad.parametric import Graph, Input, Operation


def main():
    p=argparse.ArgumentParser(); p.add_argument('output'); p.add_argument('--repetitions',type=int,default=100); a=p.parse_args()
    if a.repetitions<1: p.error('positive repetitions required')
    with open(a.output,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['history_limit','mode','sample','elapsed_ns','evaluated','valid'])
        for limit in (10,100,1000):
            nodes=[Input('x',0),Operation('y',('x',),lambda x:x+1)]; d=Document(nodes,history_limit=limit); g=Graph(nodes)
            for i in range(limit): d.edit({'x':i+1})
            for i in range(-10,a.repetitions):
                val=limit+i+20
                for mode,fn,target in [('graph',lambda:g.update({'x':val}),g),('edit',lambda:d.edit({'x':val}),d),('undo',d.undo,d),('redo',d.redo,d)]:
                    old=target.value('x'); t=perf_counter_ns(); r=fn(); elapsed=perf_counter_ns()-t
                    expected=old if mode=='undo' else val
                    if mode=='undo': expected=prior
                    if target.value('x')!=expected or target.value('y')!=expected+1 or r.evaluated!=('y',): raise RuntimeError('invalid result')
                    if mode=='edit': prior=old
                    if i>=0: w.writerow([limit,mode,i,elapsed,len(r.evaluated),True])

if __name__=='__main__': main()
