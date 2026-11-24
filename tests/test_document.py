import unittest
from goosecad.document import Document, DocumentError, RevisionConflict
from goosecad.parametric import Input, Operation, EvaluationError, Cancelled
from goosecad.geometry.kernel import box, properties


def doc(limit=100):
    return Document([Input('x',2),Input('y',3),Operation('area',('x','y'),lambda x,y:x*y)],history_limit=limit)


class DocumentTests(unittest.TestCase):
    def test_batch_undo_redo(self):
        d=doc(); rev=d.revision
        r=d.edit({'x':4,'y':5},expected_revision=rev)
        self.assertEqual(r.evaluated,('area',)); self.assertEqual(d.value('area'),20)
        d.undo(expected_revision=r.revision); self.assertEqual(d.value('area'),6)
        d.redo(); self.assertEqual(d.value('area'),20); self.assertEqual(d.revision,rev+3)

    def test_history_order_and_new_edit(self):
        d=doc(); d.edit({'x':3}); d.edit({'x':4}); d.undo(); d.undo()
        self.assertEqual(d.value('x'),2); d.redo(); self.assertEqual(d.value('x'),3)
        d.edit({'y':6}); self.assertEqual(d.snapshot().redo_depth,0)
        with self.assertRaises(DocumentError): d.redo()

    def test_history_bound(self):
        d=doc(2)
        for i in range(3,8): d.edit({'x':i})
        self.assertEqual(d.snapshot().undo_depth,2); d.undo(); d.undo(); self.assertEqual(d.value('x'),5)
        with self.assertRaises(DocumentError): d.undo()
        d.redo(); d.redo(); self.assertEqual(d.value('x'),7)
        d=doc(0); d.edit({'x':4}); self.assertEqual(d.snapshot().undo_depth,0)

    def test_stale_revision_rejected(self):
        d=doc(); old=d.revision; d.edit({'x':3}); s=d.snapshot()
        for action in (lambda:d.edit({'x':4},expected_revision=old),lambda:d.undo(expected_revision=old),lambda:d.redo(expected_revision=old)):
            with self.assertRaises(RevisionConflict): action()
        self.assertEqual(d.snapshot(),s)

    def test_failure_keeps_redo_and_revision(self):
        d=Document([Input('x',2),Operation('b',('x',),lambda x:box(x,2,3)),Operation('v',('b',),lambda b:properties(b).volume)])
        d.edit({'x':4}); d.undo(); old=d.snapshot()
        with self.assertRaises(EvaluationError): d.edit({'x':0})
        self.assertEqual(d.snapshot(),old); d.redo(); self.assertAlmostEqual(d.value('v'),24)

    def test_cancelled_undo_keeps_history(self):
        d=doc(); d.edit({'x':4}); old=d.snapshot()
        with self.assertRaises(Cancelled): d.undo(cancelled=lambda:True)
        self.assertEqual(d.snapshot(),old); d.undo(); self.assertEqual(d.value('x'),2)

    def test_invalid_and_empty(self):
        d=doc(); d.edit({'x':4}); d.undo(); old=d.snapshot()
        for change in ({'x':[]},{'x':float('nan')},{'x':float('inf')},{'area':5},{'x':4,'unknown':1}):
            with self.assertRaises(DocumentError): d.edit(change)
        d.edit({}); self.assertEqual(d.snapshot(),old)
        with self.assertRaises(DocumentError): doc(-1)
        with self.assertRaises(DocumentError): Document([Input('bad',{})])

    def test_change_mapping_copied(self):
        d=doc(); edit={'x':4}; d.edit(edit); edit['x']=99; d.undo(); d.redo(); self.assertEqual(d.value('x'),4)

    def test_two_writers_one_revision(self):
        from threading import Thread, Barrier
        d=doc(); rev=d.revision; barrier=Barrier(2); results=[]
        def writer(x):
            barrier.wait(timeout=3)
            try: d.edit({'x':x},expected_revision=rev); results.append('ok')
            except RevisionConflict: results.append('conflict')
        threads=[Thread(target=writer,args=(x,)) for x in (4,5)]
        for t in threads:t.start()
        for t in threads:t.join(4)
        self.assertFalse(any(t.is_alive() for t in threads)); self.assertCountEqual(results,['ok','conflict']); self.assertEqual(d.revision,rev+1)

    def test_reentrant_mapping_rejected(self):
        from collections.abc import Mapping
        d=doc(); old=d.snapshot()
        class Bad(Mapping):
            def __len__(self): return 1
            def __iter__(self):
                d.edit({'x':99})
                yield 'x'
            def __getitem__(self,key): return 4
        with self.assertRaises(DocumentError): d.edit(Bad())
        self.assertEqual(d.snapshot(),old)

    def test_real_geometry_undo_redo(self):
        d=Document([Input('x',2),Operation('solid',('x',),lambda x:box(x,2,3)),Operation('vol',('solid',),lambda s:properties(s).volume)])
        d.edit({'x':5}); self.assertAlmostEqual(d.value('vol'),30)
        d.undo(); self.assertAlmostEqual(d.value('vol'),12)
        d.redo(); self.assertAlmostEqual(d.value('vol'),30)

if __name__=='__main__': unittest.main()


class StructuralHistoryTests(unittest.TestCase):
    def test_mixed_history_preserves_unaffected_values_and_stamps(self):
        from goosecad.document.document import Document
        from goosecad.parametric import Input, Operation
        a=Input("x",2)
        calls=[]
        op=Operation("a",("x",),lambda x: calls.append(x) or object())
        doc=Document((a,op))
        doc.edit({"x":3})
        old_stamp,old_value=doc.versioned_value("a")
        old_revision=doc.revision
        doc.append((Input("y",4),Operation("b",("y",),lambda y:y*2)))
        self.assertGreater(doc.revision,old_revision)
        self.assertEqual(doc.versioned_value("a"),(old_stamp,old_value))
        self.assertEqual(calls,[2,3])
        stamp=doc.versioned_value("b")[0]
        doc.edit({"y":5})
        self.assertEqual(doc.value("b"),10)
        doc.undo()
        self.assertEqual(doc.value("b"),8)
        doc.undo()
        with self.assertRaises(KeyError):
            doc.value("b")
        doc.undo()
        self.assertEqual(doc.value("x"),2)
        doc.redo()
        doc.redo()
        self.assertEqual(doc.value("b"),8)
        self.assertGreater(doc.versioned_value("b")[0],stamp)
        doc.redo()
        self.assertEqual(doc.value("b"),10)

    def test_structure_failure_and_cancel_are_atomic(self):
        from goosecad.document.document import Document, RevisionConflict
        from goosecad.parametric import Input, Operation, Cancelled, GraphError
        doc=Document((Input("x",2),))
        before=doc.snapshot()
        for extra in ((Input("x",3),),
                      (Operation("bad",("missing",),lambda x:x),),
                      (Operation("bad",("x",),lambda x:1/0),)):
            with self.assertRaises(GraphError):
                doc.append(extra)
            self.assertEqual(doc.snapshot(),before)
        with self.assertRaises(Cancelled):
            doc.append((Input("y",5),),cancelled=lambda:True)
        self.assertEqual(doc.snapshot(),before)
        with self.assertRaises(RevisionConflict):
            doc.append((Input("y",5),),expected_revision=99)
        self.assertEqual(doc.snapshot(),before)
        doc.append((Input("y",5),))
        with self.assertRaises(Cancelled):
            doc.undo(cancelled=lambda:True)
        self.assertEqual(doc.value("y"),5)
        self.assertEqual(doc.history_depths,(1,0))
        doc.undo()
        doc.append((Input("z",7),))
        self.assertEqual(doc.history_depths,(1,0))
