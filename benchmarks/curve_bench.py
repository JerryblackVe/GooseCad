"""Compare bounding-box filtering against exact pair checks; validate outside timing."""
import argparse,csv,math,time
from goosecad.geometry.curves import Curve,make_region,extrude_region,revolve_region
from goosecad.geometry.kernel import properties
from goosecad.document.native import NativeDocument,Feature
from goosecad.document.curve_spec import RegionSpec,CurveSpec

def circle(x,y,r): return (Curve('circle',(x,y,r)),)
def main():
    p=argparse.ArgumentParser(); p.add_argument('output'); p.add_argument('--repetitions',type=int,default=30); a=p.parse_args()
    if a.repetitions<1: p.error('Positive repetitions required')
    with open(a.output,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['case','mode','sample','ms'])
        def sample(case,mode,fn,check):
            for i in range(-5,a.repetitions):
                t=time.perf_counter_ns(); result=fn(); ms=(time.perf_counter_ns()-t)/1e6; check(result)
                if i>=0: w.writerow([case,mode,i,ms])
        for count in (1,8,24):
            loops=(circle(50,0,40),*(circle(30+5*(i%8),-10+5*(i//8),1) for i in range(count)))
            expected=math.pi*(1600-count)
            def check(r): assert math.isclose(r.area,expected,rel_tol=1e-11)
            for broad in (False,True): sample(f'{count}_holes','filtered' if broad else 'exact_pairs',lambda:make_region(loops,_broadphase=broad),check)
        loops=(circle(5,0,2),circle(5,0,1)); r=make_region(loops)
        for name,fn,expected in [('extrude',lambda r:extrude_region(r,3),9*math.pi),('revolve',revolve_region,30*math.pi**2)]:
            def check(s): assert math.isclose(properties(s).volume,expected,rel_tol=1e-10)
            sample(name,'reuse_face',lambda:fn(r),check)
            sample(name,'rebuild_face',lambda:fn(make_region(loops)),check)
        region=RegionSpec('ring',((CurveSpec('circle',('x','y','r')),),(CurveSpec('circle',('x','y','hole')),)))
        d=NativeDocument({'x':5,'y':0,'r':2,'hole':1,'h':3},(Feature('tube','extrude_curves',('ring','h')),),regions=(region,))
        data=d.to_bytes()
        sample('native','decode_rebuild',lambda:NativeDocument.from_bytes(data),lambda e:check_native(e))

def check_native(d): assert math.isclose(properties(d.value('tube')).volume,9*math.pi,rel_tol=1e-10)
if __name__=='__main__': main()
