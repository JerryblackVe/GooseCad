"""Paired historical/current tessellation comparison; run in a Git checkout.
Baseline source is trusted, versioned project code, never document data.
"""
import argparse
import cProfile
import csv
import pstats
import statistics
import subprocess
import sys
import time
from types import ModuleType
import numpy as np
from mesh_bench import compound
from goosecad.geometry import mesh
from goosecad.geometry.kernel import box, sphere
from OCP.gp import gp_Trsf, gp_Ax2, gp_Pnt, gp_Dir, gp_Ax1, gp_Vec
from OCP.TopLoc import TopLoc_Location


def load(source, name):
    module = ModuleType('goosecad.geometry.' + name)
    module.__package__ = 'goosecad.geometry'
    sys.modules[module.__name__] = module
    exec(compile(source, name + '.py', 'exec'), module.__dict__)
    return module


def profile(source, shape, output):
    # cProfile may under-report native extension calls; stage wall times supplement it.
    replacements = [('        _validate(shape,allow_empty=True)', '        t0=clock()\n        _validate(shape,allow_empty=True)'),
                    ('        copy=BRepBuilderAPI_Copy', '        t1=clock()\n        copy=BRepBuilderAPI_Copy'),
                    ('        chunks=[]', '        t2=clock()\n        chunks=[]'),
                    ('        vertices=np.empty((nv,3)', '        t3=clock()\n        vertices=np.empty((nv,3)'),
                    ('        if not np.isfinite(vertices).all():', '        t4=clock()\n        timings.append([1000*(b-a) for a,b in zip((t0,t1,t2,t3),(t1,t2,t3,t4))])\n        if not np.isfinite(vertices).all():')]
    for old,new in replacements:
        assert source.count(old)==1, old
        source=source.replace(old,new)
    instrumented=load(source,'mesh_review_instrumented')
    instrumented.clock=time.perf_counter
    instrumented.timings=[]
    for _ in range(13): instrumented.tessellate(shape,linear=.05,angular=.3)
    with open(output,'w') as f:
        print('Wall stage medians (ms): validate/faces, copy/mesh, metadata, extraction:', [statistics.median(x) for x in zip(*instrumented.timings[3:])],file=f)
        profiler=cProfile.Profile(timer=time.perf_counter)
        start=time.perf_counter()
        profiler.enable()
        instrumented.tessellate(shape,linear=.05,angular=.3)
        profiler.disable()
        print('Profile wall ms:',(time.perf_counter()-start)*1000,file=f)
        pstats.Stats(profiler,stream=f).sort_stats('cumulative').print_stats(30)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('output')
    p.add_argument('--profile',required=True)
    p.add_argument('--baseline',default='afad1c07f827b899cc9e1fc688a1c0b9f3036632')
    p.add_argument('--repetitions',type=int,default=30)
    a=p.parse_args()
    if a.repetitions<1: p.error('Positive repetitions required')
    source=subprocess.check_output(['git','show',a.baseline+':src/goosecad/geometry/mesh.py'],text=True)
    old=load(source,'mesh_review_baseline')
    big=compound(20)
    profile(source,big,a.profile)
    mirror=gp_Trsf()
    mirror.SetMirror(gp_Ax2(gp_Pnt(0,0,0),gp_Dir(1,0,0)))
    rotation=gp_Trsf()
    rotation.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)),.7)
    rotation.SetTranslationPart(gp_Vec(1,2,3))
    cases=[('box',box(2,3,4)),('sphere',sphere(5)),('20_spheres',big),('mirror',sphere(5,(8,0,0)).Moved(TopLoc_Location(mirror))),('rotation',sphere(5).Moved(TopLoc_Location(rotation)))]
    modes=[('baseline',old.tessellate,{}),('optimized',mesh.tessellate,{}),('optimized_transform',mesh.tessellate,{'_identity_fast':False})]
    with open(a.output,'w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['case','mode','sample','ms','vertices','triangles'])
        for name,shape in cases:
            ref=old.tessellate(shape,linear=.05,angular=.3)
            results={k:[] for k,_,_ in modes}
            for i in range(-3,a.repetitions):
                for k,fn,kwargs in modes[::(-1 if i%2 else 1)]:
                    t=time.perf_counter_ns()
                    out=fn(shape,linear=.05,angular=.3,**kwargs)
                    ms=(time.perf_counter_ns()-t)/1e6
                    np.testing.assert_array_equal(ref.vertices,out.vertices)
                    np.testing.assert_array_equal(ref.triangles,out.triangles)
                    assert ref.face_offsets==out.face_offsets
                    if i>=0:
                        results[k].append(ms)
                        w.writerow([name,k,i,ms,len(out.vertices),len(out.triangles)])
            print(name,{k:(round(statistics.median(v),4),round(float(np.percentile(v,95)),4)) for k,v in results.items()},flush=True)


if __name__=='__main__': main()
