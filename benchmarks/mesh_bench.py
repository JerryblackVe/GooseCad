"""Display mesh latency; no GPU/FPS claim. Compare same triangle quality."""
import argparse,csv,time,math
import numpy as np
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound
from goosecad.geometry.kernel import box,sphere,properties
from goosecad.geometry.mesh import tessellate

def compound(n):
    b=BRep_Builder(); c=TopoDS_Compound(); b.MakeCompound(c)
    for i in range(n):b.Add(c,sphere(5,(i*15,0,0)))
    return c

def main():
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--repetitions',type=int,default=20);a=p.parse_args()
    if a.repetitions<1:p.error('Positive repetitions required')
    with open(a.output,'w',newline='') as f:
        w=csv.writer(f);w.writerow(['case','mode','sample','ms','vertices','triangles','relative_volume_error','buffer_bytes'])
        for name,s in [('box',box(2,3,4)),('sphere',sphere(5)),('20_spheres',compound(20))]:
            exact=properties(s).volume; ref=None
            for mode,kwargs in [('always_transform',{'_identity_fast':False}),('identity_fast',{}),('parallel',{'parallel':True})]:
                for i in range(-3,a.repetitions):
                    t=time.perf_counter_ns(); m=tessellate(s,linear=.05,angular=.3,**kwargs); ms=(time.perf_counter_ns()-t)/1e6
                    aa,bb,cc=m.vertices[m.triangles].transpose(1,0,2); v=np.einsum('ij,ij->i',aa,np.cross(bb,cc)).sum()/6
                    err=abs(v-exact)/exact; assert err<.03
                    if ref is None:ref=m
                    assert len(ref.triangles)==len(m.triangles)
                    if mode!='parallel': np.testing.assert_array_equal(ref.vertices,m.vertices); np.testing.assert_array_equal(ref.triangles,m.triangles)
                    if i>=0:w.writerow([name,mode,i,ms,len(m.vertices),len(m.triangles),err,m.vertices.nbytes+m.triangles.nbytes])
if __name__=='__main__':main()
