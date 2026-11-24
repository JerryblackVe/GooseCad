"""ctypes overhead experiment, scalar payload; no OCCT or Goose involved."""
import ctypes as c
import csv
import sys
from time import perf_counter_ns

def main(lib, dest):
    p=c.CDLL(lib); u=c.c_uint64; d=c.c_double
    p.gc_probe_create.argtypes=[d,c.POINTER(u)]; p.gc_probe_create.restype=c.c_int32
    p.gc_probe_release.argtypes=[u]; p.gc_probe_release.restype=c.c_int32
    p.gc_probe_values.argtypes=[c.POINTER(u),c.c_size_t,c.POINTER(d)]; p.gc_probe_values.restype=c.c_int32
    n=256; handle=u(); assert p.gc_probe_create(42,c.byref(handle))==0
    ids=(u*n)(*([handle.value]*n)); out=(d*n)(); single=(u*1)(handle.value); one=(d*1)()
    def scalar():
        for _ in range(n):
            if p.gc_probe_values(single,1,one)!=0: raise RuntimeError('ABI failure')
        assert one[0]==42
    def batch():
        assert p.gc_probe_values(ids,n,out)==0
        assert out[-1]==42 and out[0]==42
    try:
        with open(dest,'w',newline='') as f:
            w=csv.writer(f); w.writerow(['case','sample','ms'])
            for name,func in [('scalar_256',scalar),('batch_256',batch)]:
                for _ in range(10): func()
                for i in range(100):
                    t=perf_counter_ns();func();w.writerow([name,i,(perf_counter_ns()-t)/1e6])
    finally: assert p.gc_probe_release(handle)==0
if __name__=='__main__': main(*sys.argv[1:])
