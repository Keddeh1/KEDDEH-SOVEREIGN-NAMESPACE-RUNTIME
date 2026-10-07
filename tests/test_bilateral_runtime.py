import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from keddeh_namespace.bilateral_runtime import BilateralRuntime

class Controller:
    def __init__(self, root): self.state=Path(root); self.ports={'http':4055}; self.healthy=True
    def status(self):
        return {'healthy_nodes':10 if self.healthy else 9,'services':{'actor':{'alive':True}},'nodes':[{'port':19100+i,'state_hash':str(i),'compute_cycles':10,'ok':True} for i in range(10)]}
    def receipt(self,event,data):return {'event':event,'cycle':data['cycle']}

class BilateralTests(unittest.TestCase):
    def test_default_disabled_and_strict_enable(self):
        with tempfile.TemporaryDirectory() as root:
            rt=BilateralRuntime(Controller(root));rt.tick();self.assertFalse(rt.data['enabled'])
            with self.assertRaises(ValueError):rt.configure('true')
    def test_partial_actuation_resumes_after_reconstruction(self):
        with tempfile.TemporaryDirectory() as root:
            c=Controller(root);rt=BilateralRuntime(c);rt.configure(True)
            with patch('keddeh_namespace.web4_runtime.http_json',side_effect=[{'status':'ACTOR_COMMITTED'},OSError('offline')]):rt.tick()
            self.assertEqual(len(rt.data['pending']['actors']),1)
            resumed=BilateralRuntime(c)
            with patch('keddeh_namespace.web4_runtime.http_json',return_value={'status':'ACTOR_COMMITTED'}) as call:resumed.tick()
            self.assertEqual(call.call_count,9);self.assertEqual(resumed.data['cycle'],1)
            self.assertIsNone(resumed.data['pending']);self.assertEqual(resumed.data['last']['commands'][0]['right_port'],19101)
            self.assertEqual(resumed.data['last']['commands'][1]['right_port'],19100)
    def test_unavailable_feedback_pauses_without_actuation(self):
        with tempfile.TemporaryDirectory() as root:
            c=Controller(root);c.healthy=False;rt=BilateralRuntime(c);rt.configure(True)
            with patch('keddeh_namespace.web4_runtime.http_json') as call:rt.tick();call.assert_not_called()
            self.assertEqual(rt.data['status'],'paused');self.assertIsNone(rt.data['pending'])
