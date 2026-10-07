import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from keddeh_namespace.pipeline_gate import PipelineGate

class PipelineTests(unittest.TestCase):
    def test_disconnect_persists_and_reconnect_rejects_stale_generation(self):
        with tempfile.TemporaryDirectory() as root:
            gate=PipelineGate(Path(root));gate.configure(False,'isolate pipeline')
            recovered=PipelineGate(Path(root))
            with self.assertRaises(RuntimeError):recovered.dispatch(lambda: self.fail('actuated'))
            result=recovered.configure(True,'owner reconnect')
            with self.assertRaises(ValueError):recovered.dispatch(lambda: self.fail('actuated'),0)
            self.assertEqual(recovered.dispatch(lambda: 'committed',result['generation']),'committed')
    def test_no_admission_after_disconnect_acknowledgement(self):
        with tempfile.TemporaryDirectory() as root:
            gate=PipelineGate(Path(root));entered=threading.Event();release=threading.Event();ack=threading.Event()
            def operation():entered.set();self.assertTrue(release.wait(3))
            worker=threading.Thread(target=lambda:gate.dispatch(operation));worker.start()
            self.assertTrue(entered.wait(3))
            closer=threading.Thread(target=lambda:(gate.configure(False,'disconnect'),ack.set()));closer.start()
            self.assertFalse(ack.wait(.05));release.set();worker.join(3);closer.join(3)
            self.assertTrue(ack.is_set())
            with self.assertRaises(RuntimeError):gate.dispatch(lambda:self.fail('new command'))
    def test_failed_durable_write_does_not_acknowledge_fence(self):
        with tempfile.TemporaryDirectory() as root:
            gate=PipelineGate(Path(root))
            with patch('keddeh_namespace.web4_runtime.write_json',side_effect=OSError('disk unavailable')):
                with self.assertRaises(OSError):gate.configure(False,'disconnect')
            self.assertTrue(gate.status()['connected'])
    def test_offsite_projection_has_no_actor_credentials(self):
        with tempfile.TemporaryDirectory() as root:
            plan=PipelineGate(Path(root)).projection()
            remote=next(s for s in plan['services'] if s['id']=='offsite-observation')
            self.assertEqual(remote['actor_access'],'none')
            self.assertIn('not deployed',remote['deployment'])
    def test_user_space_agreement_acceptance_revocation_and_restart(self):
        with tempfile.TemporaryDirectory() as root:
            gate=PipelineGate(Path(root));context={'space':'owner','agreement_version':'1.0'}
            with self.assertRaises(ValueError):gate.require_agreement(context)
            gate.accept('1.0',True)
            restarted=PipelineGate(Path(root));restarted.require_agreement(context)
            with self.assertRaises(ValueError):restarted.require_agreement({'space':'customer','agreement_version':'1.0'})
            restarted.accept('1.0',False)
            with self.assertRaises(ValueError):PipelineGate(Path(root)).require_agreement(context)
