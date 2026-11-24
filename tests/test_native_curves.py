import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from goosecad.document import native as n
from goosecad.document.curve_spec import CurveSpec,RegionSpec
from goosecad.geometry.kernel import properties
from goosecad.parametric.dag import EvaluationError


def model():
    region=RegionSpec('ring',((CurveSpec('circle',('x','y','r')),),(CurveSpec('circle',('x','y','hole')),)))
    features=(n.Feature('tube','extrude_curves',('ring','h')),n.Feature('torus','revolve_curves',('ring','angle')),n.Feature('other','sphere',('s',)))
    return n.NativeDocument({'x':5,'y':0,'r':2,'hole':1,'h':3,'angle':2*math.pi,'s':2},features,regions=(region,))

class NativeCurveTests(unittest.TestCase):
    def test_roundtrip_and_exact_bytes(self):
        d=model(); data=d.to_bytes(); e=n.NativeDocument.from_bytes(data)
        self.assertEqual(e.format_version,3); self.assertEqual(e.to_bytes(),data)
        self.assertAlmostEqual(properties(e.value('tube')).volume,9*math.pi,places=9)
        self.assertAlmostEqual(properties(e.value('torus')).volume,30*math.pi**2,places=8)
    def test_incremental_and_history(self):
        d=model(); other=d.value('other'); d.edit({'hole':.5})
        self.assertIs(d.value('other'),other)
        self.assertAlmostEqual(properties(d.value('tube')).volume,11.25*math.pi,places=9)
        d.undo(); self.assertAlmostEqual(properties(d.value('tube')).volume,9*math.pi,places=9)
        d.redo(); self.assertAlmostEqual(properties(d.value('tube')).volume,11.25*math.pi,places=9)
    def test_rollback(self):
        d=model(); data=d.to_bytes(); old=d.value('tube'); revision=d.revision
        with self.assertRaises(EvaluationError): d.edit({'hole':3})
        self.assertEqual(data,d.to_bytes()); self.assertIs(old,d.value('tube')); self.assertEqual(revision,d.revision)
    def test_save_recover_and_stale(self):
        d=model()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.gcad'; token=n.save(d,p,expected_revision=None)
            d.edit({'h':4}); new=n.save(d,p,expected_revision=token)
            self.assertAlmostEqual(properties(n.recover(p).value('tube')).volume,9*math.pi,places=9)
            self.assertEqual(n.load_with_revision(p)[1],new)
            before=p.read_bytes(); previous=n.recovery_path(p).read_bytes()
            with self.assertRaises(n.DiskRevisionConflict): n.save(d,p,expected_revision=token)
            self.assertEqual(p.read_bytes(),before); self.assertEqual(n.recovery_path(p).read_bytes(),previous)
    def test_migration_and_downgrade(self):
        v1=n.NativeDocument({'r':2},(n.Feature('s','sphere',('r',)),)); v2=v1.upgraded(); v3=v2.upgraded()
        self.assertEqual([v1.format_version,v2.format_version,v3.format_version],[1,2,3])
        for d in (v1,v2): self.assertEqual(n.NativeDocument.from_bytes(d.to_bytes()).to_bytes(),d.to_bytes())
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; token=n.save(v2,p,expected_revision=None)
            with self.assertRaises(n.NativeError): n.save(v3,p,expected_revision=token)
            token=n.save(v3,p,expected_revision=token,allow_upgrade=True)
            self.assertEqual(n.recover(p).format_version,2)
            with self.assertRaises(n.NativeError): n.save(v2,p,expected_revision=token,allow_upgrade=True)
    def test_invalid_records_before_native(self):
        data=json.loads(model().to_bytes())['payload']
        data['regions'][0]['loops'][0][0]['coordinates'][0]='missing'
        with patch('goosecad.document.curve_spec.make_region',side_effect=AssertionError('native invoked')):
            with self.assertRaises(n.NativeError): n.NativeDocument.from_bytes(n._encode(data,3))
    def test_wrong_profile_type(self):
        data=json.loads(model().to_bytes())['payload']; data['features'][0]['kind']='extrude'
        with self.assertRaises(n.NativeError): n.NativeDocument.from_bytes(n._encode(data,3))
    def test_reuse_validated_region(self):
        d=model(); r=d.value('ring'); d.edit({'h':4}); self.assertIs(r,d.value('ring'))
        d.edit({'hole':.5}); self.assertIsNot(r,d.value('ring'))
