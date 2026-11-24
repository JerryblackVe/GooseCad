"""Native v2 roundtrip, migration, validation, incremental editing and recovery."""
import json, math, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from goosecad.document import native as n
from goosecad.geometry.kernel import properties
from goosecad.parametric import EvaluationError
from goosecad.document import DocumentError


def model(count=1):
    params={'one':1.,'zero':0.,'three':3.,'four':4.,'height':3.,'angle':math.pi/2,'width':2.}
    sketches=[]; features=[]
    for i in range(count):
        # Shared seed coordinates, independent driving widths.
        width=f'w{i}'; params[width]=2.
        points=tuple(n.PointSpec(p,x,y) for p,x,y in [('a','one','zero'),('b','three','zero'),('c','three','four'),('d','one','four')])
        constraints=(n.ConstraintSpec('anchor','fix','a',targets=('one','zero')),
                     n.ConstraintSpec('ab','horizontal','a','b'),n.ConstraintSpec('bc','vertical','b','c'),
                     n.ConstraintSpec('cd','horizontal','c','d'),n.ConstraintSpec('da','vertical','d','a'),
                     n.ConstraintSpec('width','distance','a','b',(width,)),n.ConstraintSpec('length','distance','a','d',('four',)))
        name=f'sk{i}'; sketches.append(n.SketchSpec(name,points,constraints))
        features.extend([n.Feature(f'e{i}','extrude',(name,'height')),n.Feature(f'r{i}','revolve',(name,'angle'))])
    return n.NativeDocument(params,features,sketches=sketches)


def v1(): return n.NativeDocument({'a':2,'b':3,'c':4},[n.Feature('body','box',('a','b','c'))])

class NativeSketchTests(unittest.TestCase):
    def test_roundtrip_both_sweeps(self):
        d=model(); data=d.to_bytes(); e=n.NativeDocument.from_bytes(data)
        self.assertEqual(e.format_version,2); self.assertEqual(e.to_bytes(),data)
        self.assertEqual(e.value('sk0').dof,0)
        self.assertAlmostEqual(properties(e.value('e0')).volume,24)
        self.assertAlmostEqual(properties(e.value('r0')).volume,8*math.pi)
    def test_incremental_width_undo_redo(self):
        d=model(2); other=d.value('e1'); report=d.edit({'w0':4})
        self.assertEqual(set(report.evaluated),{'sk0','e0','r0'}); self.assertIs(other,d.value('e1'))
        self.assertAlmostEqual(properties(d.value('e0')).volume,48,places=5)
        self.assertAlmostEqual(properties(d.value('r0')).volume,24*math.pi,places=5)
        d.undo(); self.assertAlmostEqual(properties(d.value('e0')).volume,24,places=5)
        d.redo(); self.assertAlmostEqual(properties(d.value('e0')).volume,48,places=5)
    def test_sweep_parameter_skips_solver(self):
        d=model(); profile=d.value('sk0'); r=d.edit({'height':-2})
        self.assertEqual(r.evaluated,('e0',)); self.assertIs(d.value('sk0'),profile)
        self.assertAlmostEqual(properties(d.value('e0')).volume,16)
    def test_failed_constraint_rollback(self):
        d=model(); old=d.to_bytes(); solid=d.value('e0'); rev=d.revision
        self.assertRaises(EvaluationError,d.edit,{'w0':0})
        self.assertEqual(d.to_bytes(),old); self.assertEqual(d.revision,rev); self.assertIs(d.value('e0'),solid)
        self.assertRaises(DocumentError,d.undo)
    def test_atomic_multi_edit_failure(self):
        d=model(); old=d.to_bytes(); shape=d.value('e0')
        self.assertRaises(EvaluationError,d.edit,{'height':5,'angle':7})
        self.assertEqual(d.to_bytes(),old); self.assertIs(d.value('e0'),shape)
    def test_v1_bytes_and_explicit_upgrade(self):
        d=v1(); original=b'{"format":"GooseCAD","payload":{"features":[{"dependencies":["a","b","c"],"id":"body","kind":"box"}],"parameters":{"a":2,"b":3,"c":4}},"sha256":"3965ed69d9d80b6d387ae93ba4810310c05f2ce6b642278a420968439dbee7bf","version":1}\n'
        self.assertEqual(d.to_bytes(),original); e=n.NativeDocument.from_bytes(original)
        self.assertEqual(e.format_version,1); self.assertEqual(e.to_bytes(),original)
        u=e.upgraded(); self.assertEqual(u.format_version,2); self.assertEqual(e.format_version,1)
        self.assertAlmostEqual(properties(u.value('body')).volume,24)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m.gcad'; n.save(e,p); self.assertRaises(n.NativeError,n.save,u,p)
            self.assertEqual(p.read_bytes(),original); self.assertFalse(n.recovery_path(p).exists())
            n.save(u,p,allow_upgrade=True); self.assertEqual(n.load(p).format_version,2)
            self.assertEqual(n.recover(p).to_bytes(),original)
            self.assertRaises(n.NativeError,n.save,e,p,allow_upgrade=True)
    def test_roundtrip_edited_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m.gcad'; d=model(); n.save(d,p); d.edit({'w0':3}); n.save(d,p)
            e=n.load(p); self.assertAlmostEqual(properties(e.value('e0')).volume,36,places=5)
            e.edit({'height':2}); e.undo(); self.assertAlmostEqual(properties(e.value('e0')).volume,36,places=5)
            e.redo(); self.assertAlmostEqual(properties(e.value('e0')).volume,24,places=5)
            p.write_bytes(b'bad'); self.assertRaises(n.NativeError,n.load,p)
            self.assertAlmostEqual(properties(n.recover(p).value('e0')).volume,24); self.assertEqual(p.read_bytes(),b'bad')
    def test_replace_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m.gcad'; d=model(); n.save(d,p); old=p.read_bytes(); d.edit({'w0':3}); replace=os.replace
            def fail(src,dst):
                if Path(dst)==p: raise OSError('simulated failure')
                replace(src,dst)
            with patch.object(n.os,'replace',side_effect=fail): self.assertRaises(OSError,n.save,d,p)
            self.assertEqual(p.read_bytes(),old); self.assertEqual(n.recover(p).to_bytes(),old)
            self.assertFalse(list(Path(td).glob('.goosecad-*.tmp')))
    def test_upgrade_failure_preserves_v1(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'v1'; d=v1(); n.save(d,p); old=p.read_bytes()
            with patch.object(n.os,'fsync',side_effect=OSError('simulated failure')):
                self.assertRaises(OSError,n.save,d.upgraded(),p,allow_upgrade=True)
            self.assertEqual(p.read_bytes(),old)
    def test_bad_checksum_and_future_version(self):
        data=model().to_bytes(); self.assertRaises(n.NativeError,n.NativeDocument.from_bytes,data.replace(b'"w0":2.0',b'"w0":5.0'))
        p=json.loads(data)['payload']; self.assertRaises(n.UnsupportedVersion,n.NativeDocument.from_bytes,n._encode(p,3))
    def test_schema_before_evaluation(self):
        for mutate in (lambda p:p['sketches'][0]['points'][0].update(x='e0'),
                       lambda p:p['sketches'][0]['points'].append(p['sketches'][0]['points'][0]),
                       lambda p:p['sketches'][0]['constraints'][0].update(targets=['missing','zero']),
                       lambda p:p['sketches'][0]['constraints'][0].update(kind='eval'),
                       lambda p:p['sketches'][0]['constraints'].append(p['sketches'][0]['constraints'][0]),
                       lambda p:p['features'][0].update(dependencies=['e0','height']),
                       lambda p:p['sketches'][0].update(id='height'),
                       lambda p:p['parameters'].update(w0=-1)):
            p=json.loads(model().to_bytes())['payload']; mutate(p)
            with patch.object(n,'Document',side_effect=AssertionError('must not evaluate')):
                self.assertRaises(n.NativeError,n.NativeDocument.from_bytes,n._encode(p,2))
    def test_bounds_and_v1_rejects_sketch_records(self):
        p=json.loads(model().to_bytes())['payload']; p['sketches'][0]['points']*=100
        self.assertRaises(n.NativeError,n.NativeDocument.from_bytes,n._encode(p,2))
        self.assertRaises(n.NativeError,n.NativeDocument.from_bytes,n._encode(p,1))
    def test_aggregate_limit(self):
        p=json.loads(model().to_bytes())['payload']; p['features']=[]
        original=p['sketches'][0]; p['sketches']=[{**original,'id':f's{i}'} for i in range(6)]
        with patch.object(n,'MAX_SKETCH_ITEMS',30): self.assertRaises(n.NativeError,n.NativeDocument.from_bytes,n._encode(p,2))
    def test_reference_sharing_and_canonical_order(self):
        d=model(); self.assertEqual(d.value('sk0').vertices,((1.,0.),(3.,0.),(3.,4.),(1.,4.)))
        p=json.loads(d.to_bytes())['payload']; p['parameters']=dict(reversed(list(p['parameters'].items())))
        self.assertEqual(n.NativeDocument.from_bytes(n._encode(p,2)).to_bytes(),d.to_bytes())
