import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from goosecad.document import native as n
from goosecad.geometry.kernel import properties


def model():
    return n.NativeDocument({'x':2,'y':3,'z':4},[n.Feature('body','box',('x','y','z'))])

class NativeTests(unittest.TestCase):
    def test_roundtrip(self):
        d=model(); d.edit({'x':5}); a=d.to_bytes(); e=n.NativeDocument.from_bytes(a)
        self.assertEqual(a,e.to_bytes()); self.assertAlmostEqual(properties(e.value('body')).volume,60)
        e.edit({'x':6}); e.undo(); self.assertEqual(e.value('x'),5)
    def test_checksum(self):
        a=model().to_bytes().replace(b'"x":2',b'"x":9'); self.assertRaises(n.NativeError,n.NativeDocument.from_bytes,a)
    def test_version(self):
        a=model().to_bytes().replace(b'"version":1',b'"version":2'); self.assertRaises(n.UnsupportedVersion,n.NativeDocument.from_bytes,a)
    def test_malformed(self):
        for a in (b'{',b'\xff',b'{"format":"GooseCAD","format":"GooseCAD"}',b'{"x":NaN}',b'['*2000,b' '* (n.MAX_BYTES+1)):
            with self.subTest(a=a[:20]): self.assertRaises(n.NativeError,n.NativeDocument.from_bytes,a)
    def test_invalid_specs(self):
        for features in ([n.Feature('body','exec',())],[n.Feature('body','box',('x','y','missing'))],[n.Feature('body','box',('x','y'))],[n.Feature('x','sphere',('y',))],[n.Feature('a','union',('b','c')),n.Feature('b','union',('a','c')),n.Feature('c','sphere',('x',))]):
            with self.subTest(features=features): self.assertRaises(n.NativeError,n.NativeDocument,{'x':2,'y':3},features)
    def test_invalid_parameters(self):
        for v in (True,float('nan'),float('inf'),1e7,{},'2'):
            self.assertRaises(n.NativeError,n.NativeDocument,{'x':v})
            self.assertRaises(n.NativeError,model().edit,{'x':v})
    def test_node_limit(self):
        self.assertRaises(n.NativeError,n.NativeDocument,{f'x{i}':1 for i in range(n.MAX_NODES+1)})
    def test_previous_and_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.gcad'; d=model(); n.save(d,p); d.edit({'x':5}); n.save(d,p)
            self.assertEqual(n.load(p).value('x'),5); self.assertEqual(n.recover(p).value('x'),2)
            p.write_bytes(b'broken'); self.assertRaises(n.NativeError,n.load,p)
            self.assertEqual(n.recover(p).value('x'),2); self.assertEqual(p.read_bytes(),b'broken')
            self.assertRaises(n.NativeError,n.save,d,p); self.assertEqual(p.read_bytes(),b'broken')
    def test_replace_failure_preserves_primary(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.gcad'; d=model(); n.save(d,p); old=p.read_bytes(); d.edit({'x':5}); replace=os.replace
            def fail(src,dst):
                if Path(dst)==p: raise OSError('injected replace failure')
                replace(src,dst)
            with patch.object(n.os,'replace',side_effect=fail): self.assertRaises(OSError,n.save,d,p)
            self.assertEqual(p.read_bytes(),old); self.assertEqual(n.recover(p).value('x'),2)
            self.assertFalse(list(Path(td).glob('.goosecad-*.tmp')))
    def test_fsync_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.gcad'; d=model(); n.save(d,p); old=p.read_bytes()
            with patch.object(n.os,'fsync',side_effect=OSError('disk error')): self.assertRaises(OSError,n.save,d,p)
            self.assertEqual(p.read_bytes(),old); self.assertFalse(list(Path(td).glob('.goosecad-*.tmp')))
    def test_directory_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertRaises(n.NativeError,n.save,model(),Path(td))
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; target=Path(td)/'target'; target.write_bytes(b'private')
            try: p.symlink_to(target)
            except OSError: self.skipTest('Symlink unavailable on this host')
            self.assertRaises(n.NativeError,n.save,model(),p); self.assertEqual(target.read_bytes(),b'private')
    def test_failed_rebuild_no_disk_change(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; data=n._encode({'parameters':{'x':-1},'features':[{'id':'s','kind':'sphere','dependencies':['x']}]}); p.write_bytes(data)
            self.assertRaises(ValueError,n.load,p); self.assertEqual(p.read_bytes(),data)
    def test_boolean_roundtrip(self):
        d=n.NativeDocument({'x':2,'y':3,'z':4,'r':1},[n.Feature('b','box',('x','y','z')),n.Feature('s','sphere',('r',)),n.Feature('cut','cut',('b','s'))])
        e=n.NativeDocument.from_bytes(d.to_bytes())
        self.assertAlmostEqual(properties(e.value('cut')).volume,properties(d.value('cut')).volume)
    def test_future_primary_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; data=model().to_bytes().replace(b'"version":1',b'"version":2'); p.write_bytes(data)
            self.assertRaises(n.UnsupportedVersion,n.save,model(),p); self.assertEqual(p.read_bytes(),data)
    def test_post_replace_sync_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; d=model(); n.save(d,p); d.edit({'x':5})
            with patch.object(n,'_sync_dir',side_effect=[None,OSError('directory sync failure')]):
                self.assertRaises(OSError,n.save,d,p)
            self.assertEqual(n.load(p).value('x'),5); self.assertEqual(n.recover(p).value('x'),2)
    def test_plain_dict_edit(self):
        from collections import UserDict
        d=model(); self.assertRaises(n.NativeError,d.edit,UserDict({'x':9})); self.assertEqual(d.value('x'),2)
    def test_recovery_suffix_reserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'model.gcad'; d=model(); n.save(d,p); d.edit({'x':5}); n.save(d,p)
            old=n.recovery_path(p).read_bytes()
            self.assertRaises(n.NativeError,n.save,d,n.recovery_path(p))
            self.assertEqual(n.recovery_path(p).read_bytes(),old)
