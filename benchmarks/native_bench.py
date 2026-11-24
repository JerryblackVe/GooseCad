"""Measure encode, reconstruct, durable replacement and load in temp directory."""
import argparse,csv,tempfile
from pathlib import Path
from time import perf_counter_ns
from goosecad.document import native as n
from goosecad.geometry.kernel import properties

def main():
    p=argparse.ArgumentParser(); p.add_argument('output'); p.add_argument('--repetitions',type=int,default=30); a=p.parse_args()
    if a.repetitions<1: p.error('positive repetitions required')
    with tempfile.TemporaryDirectory() as td,open(a.output,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['bodies','mode','sample','elapsed_ns','bytes','valid'])
        for count in (1,20,100):
            d=n.NativeDocument({'x':2,'y':3,'z':4},[n.Feature(f'b{i}','box',('x','y','z')) for i in range(count)])
            path=Path(td)/'model.gcad'; n.save(d,path)
            for i in range(-3,a.repetitions):
                d.edit({'x':2+(i%2)}); data=d.to_bytes()
                for mode,fn in [('encode',d.to_bytes),('decode',lambda:n.NativeDocument.from_bytes(data)),('save',lambda:n.save(d,path)),('load',lambda:n.load(path))]:
                    t=perf_counter_ns(); result=fn(); elapsed=perf_counter_ns()-t
                    if mode=='encode': valid=result==data
                    elif mode=='save': valid=path.read_bytes()==data
                    else: valid=result.to_bytes()==data and abs(properties(result.value(f'b{count-1}')).volume-d.value('x')*12)<1e-8
                    if not valid: raise RuntimeError('invalid roundtrip')
                    if i>=0: w.writerow([count,mode,i,elapsed,len(data),valid])
if __name__=='__main__': main()
