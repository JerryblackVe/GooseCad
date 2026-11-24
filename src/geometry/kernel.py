"""Experimental exact B-Rep adapter, dimensions in mm."""
import math
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone

def positive(*values):
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Dimensions must be finite and positive')

def checked(shape):
    if shape.IsNull() or not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError('Invalid B-Rep')
    return shape

def box(x,y,z):
    positive(x,y,z)
    return checked(BRepPrimAPI_MakeBox(x,y,z).Shape())

def cylinder(r,h):
    positive(r,h)
    return checked(BRepPrimAPI_MakeCylinder(r,h).Shape())

def boolean(a,b,operation):
    algo={'cut':BRepAlgoAPI_Cut,'union':BRepAlgoAPI_Fuse,'intersection':BRepAlgoAPI_Common}[operation](a,b)
    algo.Build()
    if not algo.IsDone(): raise RuntimeError('Boolean failed')
    return checked(algo.Shape())

def volume(shape):
    props=GProp_GProps(); BRepGProp.VolumeProperties_s(shape,props)
    return props.Mass()

def export_step(shape,path):
    writer=STEPControl_Writer()
    if writer.Transfer(checked(shape),STEPControl_AsIs)!=IFSelect_RetDone or writer.Write(str(path))!=IFSelect_RetDone:
        raise IOError('STEP export failed')
