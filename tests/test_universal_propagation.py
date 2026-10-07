import math
from pathlib import Path
import tempfile
import unittest
from keddeh_namespace.universal_propagation import Edge, Topology, PropagationRuntime, sigmoid, topology_experiment

class UniversalPropagationTests(unittest.TestCase):
    def test_negative_activation_and_extremes(self):
        self.assertGreater(sigmoid(-1),0)
        self.assertAlmostEqual(sigmoid(0),0.5)
        self.assertEqual(sigmoid(-1000),0)
        self.assertEqual(sigmoid(1000),1)
        with self.assertRaises(ValueError):sigmoid(math.nan)

    def test_direction_and_synchronous_update(self):
        rt=PropagationRuntime(Topology.adjacency([[0,2],[0,0]]),initial=[1,0],decay=0)
        rt.tick()
        self.assertEqual(rt.states[0],1)
        self.assertAlmostEqual(rt.states[1],0.2*sigmoid(1))

    def test_signed_weight(self):
        rt=PropagationRuntime(Topology.adjacency([[0,-2],[0,0]]),decay=0)
        self.assertLess(rt.tick()[1],0)

    def test_delay_reads_past_not_current(self):
        rt=PropagationRuntime(Topology(('a','b'),(Edge(0,1,1,2),)),dt=1,initial=[1,0])
        self.assertAlmostEqual(rt.tick()[1],sigmoid(1))
        self.assertAlmostEqual(rt.tick()[1],sigmoid(1))
        self.assertAlmostEqual(rt.tick()[1],sigmoid(1))
        self.assertAlmostEqual(rt.tick()[1],sigmoid(0))
        self.assertLessEqual(len(rt.history),3)

    def test_dropout_and_seed(self):
        topo=Topology.adjacency([[0,1],[1,0]])
        a=PropagationRuntime(topo,dropout=0.5,seed=3)
        b=PropagationRuntime(topo,dropout=0.5,seed=3)
        for _ in range(20):self.assertEqual(a.tick(),b.tick())
        self.assertEqual(PropagationRuntime(topo,dropout=1).tick(),(0,0))

    def test_graphml_defaults_direction_delay(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'graph.xml';p.write_text('<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><key id="w" for="edge" attr.name="weight"><default>2</default></key><key id="d" for="edge" attr.name="delay_steps"/><graph edgedefault="directed"><node id="a"/><node id="b"/><edge source="a" target="b"><data key="d">2</data></edge></graph></graphml>')
            topo=Topology.graphml(p);self.assertEqual(topo.edges,(Edge(0,1,2,2),))
            p.write_text('<!DOCTYPE a [<!ENTITY b "test">]><graphml/>')
            with self.assertRaises(ValueError):Topology.graphml(p)

    def test_invalid_inputs(self):
        for matrix in ([],[[1,2]],[[math.inf]]):
            with self.assertRaises(ValueError):Topology.adjacency(matrix)
        with self.assertRaises(ValueError):PropagationRuntime(Topology.adjacency([[0]]),dt=2)
        with self.assertRaises(ValueError):Topology(('a',),(Edge(0,2,1),))

    def test_experiment_reproducible_and_scoped(self):
        a=topology_experiment(nodes=4,rounds=4,trials=10)
        self.assertEqual(a,topology_experiment(nodes=4,rounds=4,trials=10))
        self.assertEqual(len(a['results']),10)
        for row in a['results']:
            self.assertTrue(0<=row['mean_coverage']<=1)
            self.assertLessEqual(row['wilson_95_interval'][0],row['full_coverage_probability']+1e-12)
            self.assertGreaterEqual(row['wilson_95_interval'][1],row['full_coverage_probability']-1e-12)
