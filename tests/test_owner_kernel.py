import math
import tempfile
import unittest
from pathlib import Path
import numpy as np
from keddeh_namespace.owner_kernel import KCloudNode, DynamicHealingAgent, StochasticKuramotoPLL
from keddeh_namespace.domain_mesh import DomainMesh

class OwnerKernelTests(unittest.TestCase):
    def test_owner_boundary_rejects_zero_and_unsigned_payload(self):
        node=KCloudNode()
        self.assertEqual(node.process_request(0,'A.KEDDEH:commit'),'DROPPED')
        self.assertEqual(node.process_request(2,'foreign'),'DROPPED')
        self.assertEqual(node.process_request(-2,'A.KEDDEH:restart'),'MAPPED')
    def test_owner_healing_contracts_bilateral_error(self):
        result=DynamicHealingAgent().resolve_drift([1,0])
        self.assertLess(max(result),1);self.assertGreater(min(result),0)
    def test_owner_flywheel_retains_wrapped_state_without_parent(self):
        pll=StochasticKuramotoPLL();pll.sigma=0;pll.theta=np.array([6.27,6.28,0.01]);pll.omega=np.array([.3,.29,.31])
        for i in range(1000):coherence,phase=pll.step(i*.01,0,False,0)
        self.assertTrue(all(0<=x<2*math.pi for x in pll.theta));self.assertGreater(coherence,.99)
        self.assertTrue(np.max(abs(pll.omega-.297))<.001)
    def test_recursive_reanchor_rejects_cycle_before_network_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            class Controller:pass
            c=Controller();c.state=Path(root);c.root=Path(root)
            mesh=DomainMesh(c);mesh.data['domains']=[{'id':'domain-0','parent':None},{'id':'domain-1','parent':'domain-0'}]
            with self.assertRaises(ValueError):mesh.reanchor('domain-0','domain-1')
