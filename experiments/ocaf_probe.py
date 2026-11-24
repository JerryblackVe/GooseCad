"""Isolated exploratory probe: may abort on OCP object destruction.
Do not import in the application or execute in normal CI until investigated.
"""
from OCP.TNaming import TNaming_Builder, TNaming_Tool
from OCP.TDF import TDF_Data
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

b = BRepPrimAPI_MakeBox(10,10,10)
b.Build()
d = TDF_Data()
label = d.Root().FindChild(1, True)
n = TNaming_Builder(label)
n.Generated(b.TopFace())
print('OCAF named shape:', n.NamedShape().IsEmpty(),
      TNaming_Tool.GetShape_s(n.NamedShape()).IsSame(b.TopFace()), flush=True)
