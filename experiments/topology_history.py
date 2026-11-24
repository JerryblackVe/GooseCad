"""P0 experiment: operation history is not a persistent naming algorithm."""
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from goosecad.geometry.kernel import box

def faces(s):
    m=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(s,TopAbs_FACE,m)
    return [m.FindKey(i) for i in range(1,m.Extent()+1)]

def run():
    a=box(10,10,10)
    for offset in [2,4,6,11]:
        cutter=box(2,20,20,(offset,-5,-5))
        op=BRepAlgoAPI_Cut(a,cutter)
        if not op.IsDone(): raise RuntimeError('cut failed')
        result=faces(op.Shape());print(f'offset={offset} result_faces={len(result)}')
        for i,f in enumerate(faces(a),1):
            modified=list(op.Modified(f)); generated=list(op.Generated(f)); unchanged=any(f.IsSame(x) for x in result)
            print(f'  input_face={i} modified={len(modified)} generated={len(generated)} deleted={op.IsDeleted(f)} unchanged={unchanged}')
if __name__=='__main__':run()
