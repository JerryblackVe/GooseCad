"""Compare equal-quality display buffers, including cache budget; not FPS."""
import argparse,csv,time
import numpy as np
from goosecad.document.native import NativeDocument,Feature
from goosecad.geometry.mesh import tessellate
from goosecad.geometry.mesh_cache import MeshCache,MeshSettings

def main():
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--repetitions',type=int,default=20);a=p.parse_args()
    if a.repetitions<1:p.error('Positive repetitions required')
    with open(a.output,'w',newline='') as f:
        w=csv.writer(f);w.writerow(['bodies','mode','sample','ms','retained_bytes','triangles'])
        for n in (1,20):
            d=NativeDocument({f'r{i}':5 for i in range(n)},tuple(Feature(f's{i}','sphere',(f'r{i}',)) for i in range(n)))
            c=MeshCache(d);ids=[f's{i}' for i in range(n)];settings=MeshSettings(linear=.05,angular=.3)
            for i in range(-2,a.repetitions):
                d.edit({'r0':5+(i%2)})
                t=time.perf_counter_ns(); direct=[tessellate(d.value(k),linear=settings.linear,angular=settings.angular) for k in ids]; ms=(time.perf_counter_ns()-t)/1e6
                if i>=0:w.writerow([n,'rebuild',i,ms,0,sum(len(m.triangles) for m in direct)])
                for mode in ('selective','warm'):
                    t=time.perf_counter_ns(); snaps=[c.get(k,settings) for k in ids]; ms=(time.perf_counter_ns()-t)/1e6
                    for expected,s in zip(direct,snaps):
                        assert c.is_current(s);np.testing.assert_array_equal(expected.vertices,s.mesh.vertices);np.testing.assert_array_equal(expected.triangles,s.mesh.triangles);assert expected.face_offsets==s.mesh.face_offsets
                    if i>=0:w.writerow([n,mode,i,ms,c.info().bytes,sum(len(s.mesh.triangles) for s in snaps)])
if __name__=='__main__':main()
