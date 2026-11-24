"""Software or hardware render backend as reported by VTK, not desktop FPS."""
import argparse,csv,time
from goosecad.document.native import NativeDocument,Feature
from goosecad.view.scene import Scene

def main():
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--repetitions',type=int,default=10);a=p.parse_args()
    if a.repetitions<1:p.error('Positive repetitions required')
    with open(a.output,'w',newline='') as f:
        w=csv.writer(f);w.writerow(['bodies','mode','sample','ms','updated','backend'])
        for n in (1,20):
            d=NativeDocument({f'r{i}':5+i*.1 for i in range(n)},tuple(Feature(f's{i}','sphere',(f'r{i}',)) for i in range(n)))
            s=Scene(d,offscreen=True,size=(640,480));ids=[f's{i}' for i in range(n)]
            try:
                s.refresh(ids);s.fit();s.render();backend=s.window.GetClassName();print(backend,flush=True)
                print('\n'.join(x for x in s.window.ReportCapabilities().splitlines() if 'OpenGL renderer' in x or 'OpenGL vendor' in x),flush=True)
                for i in range(-2,a.repetitions):
                    d.edit({'r0':5+(i%2)});t=time.perf_counter_ns();changed=s.refresh(ids);ms=(time.perf_counter_ns()-t)/1e6;assert changed==('s0',)
                    if i>=0:w.writerow([n,'selective_refresh',i,ms,len(changed),backend])
                    t=time.perf_counter_ns();changed=s.refresh(ids);ms=(time.perf_counter_ns()-t)/1e6;assert not changed
                    if i>=0:w.writerow([n,'warm_refresh',i,ms,len(changed),backend])
                    s.orbit(3,0);t=time.perf_counter_ns();s.render();ms=(time.perf_counter_ns()-t)/1e6
                    if i>=0:w.writerow([n,'render',i,ms,0,backend])
            finally:s.close()
if __name__=='__main__':main()
