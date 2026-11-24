"""Validated XY profiles, broadphase comparison and actual OCCT sweep latency."""
import argparse,csv
from math import cos,sin,pi
from time import perf_counter_ns
from goosecad.geometry.sweep import validate_polygon,extrude,revolve
from goosecad.geometry.kernel import properties

def main():
    p=argparse.ArgumentParser();p.add_argument('dest');p.add_argument('--repetitions',type=int,default=30);args=p.parse_args()
    with open(args.dest,'w',newline='') as f:
        w=csv.writer(f);w.writerow(['case','vertices','sample','ms'])
        for n in (4,32,128,256):
            pts=tuple((20+10*cos(2*pi*i/n),10*sin(2*pi*i/n)) for i in range(n))
            assert validate_polygon(pts)==validate_polygon(pts,_broadphase=False)
            for name,fn in [('validation_all',lambda:validate_polygon(pts,_broadphase=False)),('validation_bbox',lambda:validate_polygon(pts)),('extrude',lambda:extrude(pts,5))]+([('revolve',lambda:revolve(pts,pi))] if n<=32 else []):
                for _ in range(3):fn()
                for i in range(args.repetitions):
                    t=perf_counter_ns();v=fn();elapsed=(perf_counter_ns()-t)/1e6
                    if name in ('extrude','revolve'):
                        from math import isclose
                        area=n*50*sin(2*pi/n);expected=area*(5 if name=='extrude' else 20*pi)
                        assert isclose(properties(v).volume,expected,rel_tol=1e-8)
                    w.writerow([name,n,i,elapsed])
if __name__=='__main__':main()
