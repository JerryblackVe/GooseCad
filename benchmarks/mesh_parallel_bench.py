"""Paired serial/parallel threshold experiment, same output geometry and quality."""
import argparse
import csv
import statistics
import time
import numpy as np
from mesh_bench import compound
from goosecad.geometry.mesh import tessellate, _faces
from goosecad.geometry.kernel import box, sphere, properties


def signed_volume(m):
    a,b,c=m.vertices[m.triangles].transpose(1,0,2)
    return np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6


def main():
    p=argparse.ArgumentParser()
    p.add_argument('output')
    p.add_argument('--repetitions',type=int,default=20)
    a=p.parse_args()
    if a.repetitions<1: p.error('Positive repetitions required')
    cases=[('box',box(2,3,4)),('sphere',sphere(5))]+[(f'{n}_spheres',compound(n)) for n in (5,10,20)]
    with open(a.output,'w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['case','faces','parallel','sample','ms','vertices','triangles','signed_volume'])
        for name,shape in cases:
            faces=_faces(shape).Extent()
            exact=properties(shape).volume
            ref=tessellate(shape,linear=.05,angular=.3)
            ref_v=signed_volume(ref)
            assert abs(ref_v-exact)<exact*.03
            times={False:[],True:[]}
            for i in range(-3,a.repetitions):
                for parallel in ([False,True] if i%2 else [True,False]):
                    start=time.perf_counter_ns()
                    m=tessellate(shape,linear=.05,angular=.3,parallel=parallel)
                    elapsed=(time.perf_counter_ns()-start)/1e6
                    v=signed_volume(m)
                    assert m.vertices.shape==ref.vertices.shape and m.triangles.shape==ref.triangles.shape
                    assert m.face_offsets==ref.face_offsets and abs(v-ref_v)<=exact*1e-10
                    np.testing.assert_allclose(m.vertices[np.lexsort(m.vertices.T[::-1])],ref.vertices[np.lexsort(ref.vertices.T[::-1])],rtol=0,atol=1e-10)
                    if i>=0:
                        times[parallel].append(elapsed)
                        w.writerow([name,faces,parallel,i,elapsed,len(m.vertices),len(m.triangles),v])
            print(name,{k:(round(statistics.median(v),4),round(float(np.percentile(v,95)),4)) for k,v in times.items()},flush=True)


if __name__=='__main__': main()
