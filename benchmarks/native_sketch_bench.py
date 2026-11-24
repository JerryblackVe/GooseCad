"""Native v2 end-to-end timings; analytic volumes and exact dependency set checked outside timing."""
import argparse,csv,math,tempfile
from pathlib import Path
from time import perf_counter_ns
from goosecad.document import native as n
from goosecad.geometry.kernel import properties


def model(count):
    params={'one':1.,'zero':0.,'three':3.,'four':4.,'height':3.,'angle':math.pi/2}
    sketches=[]; features=[]
    points=tuple(n.PointSpec(p,x,y) for p,x,y in [('a','one','zero'),('b','three','zero'),('c','three','four'),('d','one','four')])
    for i in range(count):
        width=f'w{i}'; params[width]=2.; name=f'sk{i}'
        constraints=(n.ConstraintSpec('anchor','fix','a',targets=('one','zero')),
                     n.ConstraintSpec('ab','horizontal','a','b'),n.ConstraintSpec('bc','vertical','b','c'),
                     n.ConstraintSpec('cd','horizontal','c','d'),n.ConstraintSpec('da','vertical','d','a'),
                     n.ConstraintSpec('width','distance','a','b',(width,)),n.ConstraintSpec('length','distance','a','d',('four',)))
        sketches.append(n.SketchSpec(name,points,constraints))
        features.extend([n.Feature(f'e{i}','extrude',(name,'height')),n.Feature(f'r{i}','revolve',(name,'angle'))])
    return n.NativeDocument(params,features,sketches=sketches)


def run(output,reps):
    with tempfile.TemporaryDirectory() as td,open(output,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['sketches','mode','sample','elapsed_ns','bytes','evaluated','valid'])
        for count in (1,10,50):
            d=model(count); path=Path(td)/'m.gcad'; n.save(d,path)
            for i in range(-3,reps):
                width=2.+(i%2); other=d.value('e1') if count>1 else None
                t=perf_counter_ns(); report=d.edit({'w0':width}); elapsed=perf_counter_ns()-t
                data=d.to_bytes(); valid=set(report.evaluated)=={'sk0','e0','r0'} and abs(properties(d.value('e0')).volume-12*width)<1e-6
                if count>1: valid=valid and other is d.value('e1')
                if not valid: raise RuntimeError('invalid incremental result')
                if i>=0: w.writerow([count,'incremental',i,elapsed,len(data),len(report.evaluated),valid])
                for mode,fn in [('encode',d.to_bytes),('rebuild',lambda:n.NativeDocument.from_bytes(data)),('save',lambda:n.save(d,path)),('load',lambda:n.load(path))]:
                    t=perf_counter_ns(); r=fn(); elapsed=perf_counter_ns()-t
                    if mode=='encode': valid=r==data
                    elif mode=='save': valid=path.read_bytes()==data
                    else:
                        valid=r.to_bytes()==data and abs(properties(r.value('e0')).volume-12*width)<1e-6 and abs(properties(r.value('r0')).volume-math.pi*((1+width)**2-1))<1e-6
                        if count>1: valid=valid and abs(properties(r.value('e1')).volume-24)<1e-6
                    if not valid: raise RuntimeError('invalid '+mode)
                    if i>=0: w.writerow([count,mode,i,elapsed,len(data),3*count if mode in ('rebuild','load') else '',valid])
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('output'); p.add_argument('--repetitions',type=int,default=20); a=p.parse_args()
    if a.repetitions<1:p.error('positive repetitions required')
    run(a.output,a.repetitions)
