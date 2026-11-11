import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).resolve().parents[1] / 'src/keddeh_namespace/ai_py_binding.py'
spec = importlib.util.spec_from_file_location('ai_py_binding', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FakeController:
    def __init__(self, directory):
        self.state = Path(directory)
        self.ports = {'mesh': [19100, 19101]}
        self.source_digest = 'a' * 64
        self.alive = True
        self.calls = []
        self.probe_failure = False
    def estate_rpc(self, method, params):
        if self.probe_failure: raise RuntimeError('estate unavailable')
        return {'schema': 'preserved.estate.readback', 'status': 'OBSERVED'}
    def status(self):
        return {'schema': 'keddeh.web4.readback.v1', 'healthy_nodes': 2 if self.alive else 0,
                'services': {'estate': {'alive': self.alive}}}
    def control(self, request):
        self.calls.append(request)
        return {'schema': 'existing.kex.source', 'result': len(self.calls)}

class HostBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.host = FakeController(self.tmp.name)
        self.binding = module.HostBinding(self.host)
    def request(self, rid='test-request-01', op='mesh_discover', args=None):
        return {'schema': module.REQUEST_SCHEMA, 'requestId': rid, 'operation': op, 'arguments': {} if args is None else args}
    def test_host_status_is_local_and_no_site_claim(self):
        obj = self.binding.status()
        self.assertTrue(obj['connected'])
        self.assertFalse(obj['siteDeploymentVerified'])
        self.assertFalse(obj['arbitraryPythonExecution'])
        self.host.alive = False
        self.assertEqual(self.binding.status()['state'], 'NO_PYTHON_HOST_BINDING')
    def test_process_alive_without_functional_rpc_is_not_binding(self):
        self.host.probe_failure = True
        result = self.binding.status()
        self.assertFalse(result['connected'])
        self.assertIsNone(result['functionalReadbackDigest'])
        with self.assertRaisesRegex(RuntimeError, 'NO_PYTHON_HOST_BINDING'):
            self.binding.execute(self.request())
        self.assertEqual(self.host.calls, [])
    def test_host_status_errors_are_disconnected_without_side_effects(self):
        self.host.status = lambda: (_ for _ in ()).throw(OSError('closed'))
        result = self.binding.status()
        self.assertFalse(result['connected'])
        self.assertEqual(result['state'], 'NO_PYTHON_HOST_BINDING')
        with self.assertRaisesRegex(RuntimeError, 'NO_PYTHON_HOST_BINDING'):
            self.binding.execute(self.request())
        self.assertEqual(self.host.calls, [])
    def test_real_dispatch_and_stable_readback(self):
        result = self.binding.execute(self.request())
        self.assertEqual(result['state'], 'RECORDED')
        self.assertEqual(self.host.calls, [{'action':'estate','tool':'mesh_discover','arguments':{}}])
        self.assertEqual(self.binding.receipt('test-request-01')['receiptDigest'], result['receiptDigest'])
    def test_replay_after_reconstruction_does_not_redispatch(self):
        self.binding.execute(self.request())
        other = module.HostBinding(self.host)
        replay = other.execute(self.request())
        self.assertTrue(replay['replay'])
        self.assertEqual(len(self.host.calls), 1)
    def test_changed_body_under_same_identity_rejected(self):
        self.binding.execute(self.request())
        with self.assertRaisesRegex(ValueError, 'COLLISION'):
            self.binding.execute(self.request(op='mesh_status'))
        self.assertEqual(len(self.host.calls), 1)
    def test_pending_after_crash_not_executed(self):
        payload = self.request()
        base = {'schema': module.RECEIPT_SCHEMA,'requestId':'test-request-01',
                'inputDigest':module.digest(payload),'operation':'mesh_discover',
                'sourceDigest':self.host.source_digest,'createdAt':module.now(),
                'state':'PENDING','effect':'NOT_YET_RECONCILED'}
        self.binding._persist(base)
        result = self.binding.execute(payload)
        self.assertEqual(result['state'], 'PENDING')
        self.assertEqual(self.host.calls, [])
    def test_unavailable_host_makes_no_receipt(self):
        self.host.alive = False
        with self.assertRaisesRegex(RuntimeError,'NO_PYTHON_HOST_BINDING'):
            self.binding.execute(self.request())
        self.assertIsNone(self.binding.receipt('test-request-01'))
    def test_failure_after_dispatch_is_explicitly_uncertain(self):
        self.host.control = lambda payload: (_ for _ in ()).throw(OSError('private'))
        result = self.binding.execute(self.request())
        self.assertEqual(result['state'], 'OUTCOME_UNCERTAIN')
        self.assertNotIn('private', str(result))
        self.assertEqual(self.binding.execute(self.request())['state'], 'OUTCOME_UNCERTAIN')
    def test_unadmitted_payload_and_traversal_rejected(self):
        cases = [self.request(rid='../pwned--'),self.request(op='python_eval'),
                 self.request(args={'cmd':'echo x'}),{**self.request(), 'unexpected':'x'}]
        for case in cases:
            with self.assertRaises(ValueError):self.binding.execute(case)
        self.assertEqual(self.host.calls, [])
    def test_receipt_tampering_detected(self):
        self.binding.execute(self.request())
        path=self.binding._path('test-request-01')
        path.write_text(path.read_text().replace('RECORDED','FAKE_PASS'))
        with self.assertRaisesRegex(ValueError, 'INTEGRITY_FAILURE'):
            self.binding.receipt('test-request-01')

if __name__ == '__main__': unittest.main()
