"""Compare current save with an isolated benchmark-only bypass of cooperative lock.
No concurrent writer; do not use the bypass in production. Check bytes outside timing.
"""
import argparse,csv,tempfile
from contextlib import nullcontext
from pathlib import Path
from time import perf_counter_ns
from unittest.mock import patch
from goosecad.document import native as n
from goosecad.document.disk_lock import writer_lock


def main():
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--repetitions',type=int,default=50);a=p.parse_args()
    if a.repetitions<1:p.error('positive repetitions required')
    with tempfile.TemporaryDirectory() as td,open(a.output,'w',newline='',encoding='utf-8') as f:
        path=Path(td)/'m.gcad';w=csv.writer(f);w.writerow(['mode','sample','elapsed_ns','valid'])
        d=n.NativeDocument({'r':2},[n.Feature('s','sphere',('r',))]);token=n.save(d,path)
        for i in range(-5,a.repetitions):
            # Interleave modes to reduce drift. Each writes the same size document.
            for mode in ('no_lock','locked','checked','lock_only'):
                d.edit({'r':2+i%2}); data=d.to_bytes()
                if mode=='lock_only':
                    t=perf_counter_ns()
                    with writer_lock(path): pass
                    elapsed=perf_counter_ns()-t;valid=not n.lock_path(path).exists()
                else:
                    with patch.object(n,'writer_lock',nullcontext) if mode=='no_lock' else nullcontext():
                        t=perf_counter_ns();token=n.save(d,path,**({'expected_revision':token} if mode=='checked' else {}));elapsed=perf_counter_ns()-t
                    valid=path.read_bytes()==data and not n.lock_path(path).exists()
                if not valid: raise RuntimeError('invalid save or lock')
                if i>=0:w.writerow([mode,i,elapsed,valid])
if __name__=='__main__':main()
