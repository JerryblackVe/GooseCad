"""Run python -m goosecad.view [document.gcad body ...].
Mouse trackball orbit/pan/zoom; R fit, P select at cursor, Q quit.
"""
import argparse
from vtkmodules.vtkRenderingCore import vtkRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from goosecad.document.native import NativeDocument,Feature,load
from .scene import Scene

def main():
    p=argparse.ArgumentParser(description='GooseCAD experimental VTK viewer');p.add_argument('document',nargs='?');p.add_argument('bodies',nargs='*');a=p.parse_args()
    if a.document:
        if not a.bodies:p.error('Specify one or more body IDs')
        d=load(a.document);bodies=a.bodies
    else:
        d=NativeDocument({'x':10,'y':8,'z':5},(Feature('box','box',('x','y','z')),));bodies=['box']
    s=Scene(d);s.refresh(bodies);s.fit();s.orbit(30,20)
    i=vtkRenderWindowInteractor();i.SetRenderWindow(s.window);style=vtkInteractorStyleTrackballCamera();i.SetInteractorStyle(style)
    def key(obj,event):
        if obj.GetKeySym().lower()=='p':
            hit=s.select(*obj.GetEventPosition());print(hit,flush=True);s.render()
    i.AddObserver('KeyPressEvent',key);s.render();i.Initialize()
    try:i.Start()
    finally:s.close()
if __name__=='__main__':main()
