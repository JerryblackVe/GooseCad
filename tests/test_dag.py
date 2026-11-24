import unittest
from goosecad.parametric import Graph, Input, Operation, GraphError, EvaluationError, Cancelled
from goosecad.geometry.kernel import box, properties

class DagTests(unittest.TestCase):
    def test_diamond_and_independent_branch(self):
        g = Graph([Operation('out', ('b','c'), lambda b,c:b+c), Input('a',2),
                   Operation('b',('a',),lambda a:a*2), Operation('c',('a',),lambda a:a+1),
                   Input('x',3), Operation('y',('x',),lambda x:x*10)])
        r = g.update({'a':4})
        self.assertEqual(r.evaluated, ('b','c','out'))
        self.assertEqual(g.value('out'),13)
        self.assertEqual(g.value('y'),30)

    def test_cycle_and_self_cycle(self):
        for nodes in ([Operation('a',('b',),str),Operation('b',('a',),str)], [Operation('a',('a',),str)]):
            with self.assertRaisesRegex(GraphError,'Circular'): Graph(nodes)

    def test_invalid_graph(self):
        for nodes in ([Input('a',1),Input('a',2)], [Operation('a',('missing',),str)],
                      [Input('a',1),Operation('b',('a','a'),sum)], [Input('',1)]):
            with self.assertRaises(GraphError): Graph(nodes)

    def test_atomic_failure(self):
        g = Graph([Input('a',2), Operation('b',('a',),lambda a:a+1), Operation('c',('b',),lambda b:1/(b-5))])
        old = g.snapshot()
        with self.assertRaises(EvaluationError) as cm: g.update({'a':4})
        self.assertEqual(cm.exception.node,'c')
        self.assertEqual(g.snapshot(),old)
        g.update({'a':5})
        self.assertEqual(g.value('c'),1)

    def test_cancelled_before_commit(self):
        g = Graph([Input('a',1),Operation('b',('a',),lambda a:a+1)])
        old = g.snapshot(); calls = iter([False,False,True])
        with self.assertRaises(Cancelled): g.update({'a':2},cancelled=lambda:next(calls))
        self.assertEqual(g.snapshot(),old)

    def test_batch_and_full_equivalence(self):
        g = Graph([Input('a',1),Input('b',2),Operation('c',('a','b'),lambda a,b:a*b)])
        self.assertEqual(g.update({'b':3,'a':4}).evaluated,('c',))
        old=g.snapshot()[1]; g.update({},full=True); self.assertEqual(g.snapshot()[1],old)

    def test_invalid_update_and_empty(self):
        g=Graph([Input('a',1),Operation('b',('a',),str)]); old=g.snapshot()
        for changes in ({'a':2,'b':3},{'missing':2}):
            with self.assertRaises(GraphError): g.update(changes)
        self.assertEqual(g.update({}).revision,old[0]); self.assertEqual(g.snapshot(),old)

    def test_reentrant_update(self):
        holder=[]
        def fn(a):
            if holder: holder[0].update({'a':99})
            return a
        g=Graph([Input('a',1),Operation('b',('a',),fn)]); holder.append(g); old=g.snapshot()
        with self.assertRaises(EvaluationError): g.update({'a':2})
        self.assertEqual(g.snapshot(),old)

    def test_deep_chain_no_recursion(self):
        n=3000; g=Graph([Input('0',0)]+[Operation(str(i),(str(i-1),),lambda x:x+1) for i in range(1,n)])
        self.assertEqual(len(g.update({'0':3}).evaluated),n-1)
        self.assertEqual(g.value(str(n-1)),n+2)

    def test_real_occt_model_and_failure(self):
        g=Graph([Input('width',10),Operation('solid',('width',),lambda w:box(w,2,3)),
                 Operation('volume',('solid',),lambda s:properties(s).volume),
                 Input('other',5),Operation('independent',('other',),lambda w:box(w,2,3))])
        independent=g.value('independent')
        self.assertEqual(g.update({'width':20}).evaluated,('solid','volume'))
        self.assertAlmostEqual(g.value('volume'),120)
        self.assertIs(g.value('independent'),independent)
        old=g.snapshot(); solid=g.value('solid')
        with self.assertRaises(EvaluationError): g.update({'width':0})
        self.assertEqual(g.revision,old[0]); self.assertIs(g.value('solid'),solid)

    def test_random_dag_against_full(self):
        from random import Random
        rng=Random(4601)
        nodes=[Input(f'p{i}',i) for i in range(8)]
        ids=[n.id for n in nodes]
        for i in range(200):
            deps=tuple(rng.sample(ids,2)); name=f'f{i}'
            nodes.append(Operation(name,deps,lambda a,b:(a+b)%997)); ids.append(name)
        g=Graph(nodes); oracle=Graph(nodes)
        for _ in range(40):
            changes={f'p{rng.randrange(8)}':rng.randrange(1000) for _ in range(3)}
            g.update(changes); oracle.update(changes,full=True)
            self.assertEqual(g.snapshot()[1],oracle.snapshot()[1])

    def test_reader_observes_complete_revision(self):
        from threading import Thread, Event
        entered, release, read_started = Event(), Event(), Event()
        def fn(x):
            if x==2:
                entered.set()
                if not release.wait(3): raise RuntimeError('timeout')
            return x*10
        g=Graph([Input('a',1),Operation('b',('a',),fn)])
        captured=[]; errors=[]
        def write():
            try: g.update({'a':2})
            except Exception as exc: errors.append(exc)
        def read():
            read_started.set(); captured.append(g.snapshot())
        w=Thread(target=write); r=Thread(target=read); w.start()
        try:
            self.assertTrue(entered.wait(3)); r.start(); self.assertTrue(read_started.wait(3))
        finally:
            release.set(); w.join(3)
            if r.ident is not None: r.join(3)
        self.assertFalse(w.is_alive() or r.is_alive()); self.assertFalse(errors)
        self.assertEqual(captured,[(2,{'a':2,'b':20})])

if __name__=='__main__': unittest.main()
