"""Hosting scope, physical backing contract, and real owned process lifecycle."""
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import test_web4_runtime
from keddeh_namespace.bootstrap import storage_requirements
from keddeh_namespace.verify_vfs import verify_volume

class StorageContracts(unittest.TestCase):
    def test_logical_quota_is_not_physical_allocation(self):
        policy=storage_requirements({'vfs_backing_required_bytes':8192,'vfs_backing_reserve_bytes':4096},'vfs',10**13)
        with tempfile.TemporaryDirectory() as root:
            with patch('os.statvfs',return_value=SimpleNamespace(f_frsize=4096,f_blocks=16,f_bavail=8)):
                result=verify_volume(root,require_mount=False,**policy)
        self.assertEqual(result['logical_quota_bytes'],10**13)
        self.assertEqual(result['required_bytes'],8192)
        self.assertEqual(result['fsync_readback'],'passed')

    def test_capacity_and_reserve_enforced(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('os.statvfs',return_value=SimpleNamespace(f_frsize=4096,f_blocks=16,f_bavail=1)):
                with self.assertRaisesRegex(ValueError,'capacity'):
                    verify_volume(root,required_bytes=10**13,require_mount=False)
                with self.assertRaisesRegex(ValueError,'reserve'):
                    verify_volume(root,required_bytes=8192,reserve_bytes=4096,require_mount=False)

    def test_no_invented_backing_contract(self):
        p=storage_requirements({},'vfs',10**13)
        self.assertIsNone(p['required_bytes']);self.assertIsNone(p['reserve_bytes'])
        p=storage_requirements({'vfs_required_bytes':10**13},'vfs',10**13)
        self.assertEqual(p['required_bytes'],10**13);self.assertIsNone(p['reserve_bytes'])
        p=storage_requirements({'vfs_required_bytes':10**13,'vfs_backing_reserve_bytes':0},'vfs',10**13)
        self.assertEqual(p['required_bytes'],10**13);self.assertEqual(p['reserve_bytes'],0)

class HostingSemantics(unittest.TestCase):
    setUp=test_web4_runtime.Web4RuntimeTests.setUp
    fixture_controller=test_web4_runtime.Web4RuntimeTests.fixture_controller

    def test_empty_broker_is_not_empty_execution_inventory(self):
        c=self.fixture_controller();c.ports['broker']=18777
        c.specs['http']=('unused','unused',None,False)
        with patch('keddeh_namespace.web4_runtime.http_json',return_value={'node':None,'command':None}):state=c.status()
        inventory=state['execution_inventory']
        self.assertEqual(inventory['broker']['registered_clients'],0)
        self.assertEqual(inventory['native']['configured_services'],['http'])
        self.assertEqual(len(inventory['browser']),3)
        self.assertIn('no service or Linux launch',state['substrate_status']['operation'])
        with patch('keddeh_namespace.web4_runtime.http_json',side_effect=OSError):
            self.assertIsNone(c.status()['execution_inventory']['broker']['registered_clients'])

    def test_owned_service_boot_executes_and_is_idempotent(self):
        c=self.fixture_controller();(c.state/'pairing-code').write_text('test-only');self.addCleanup(c.close)
        c.specs['test-worker']=([sys.executable,'-c','import time; time.sleep(30)'],str(self.root),None,False)
        first=c.control({'action':'boot','target':'service','name':'test-worker'})
        self.assertIsNone(c.processes['test-worker'].poll())
        second=c.control({'action':'boot','target':'service','name':'test-worker'})
        self.assertEqual(first['pid'],second['pid'])
        c.terminate(c.processes['test-worker'])
        third=c.control({'action':'boot','target':'service','name':'test-worker'})
        self.assertNotEqual(first['pid'],third['new_pid'])
        with self.assertRaises(ValueError):c.control({'action':'boot','target':'service','name':'arbitrary'})
        c.control({'action':'pipeline','connected':False,'reason':'test'})
        with self.assertRaises(RuntimeError):c.control({'action':'boot','target':'service','name':'test-worker'})

    def test_substrate_dispatch_and_invalid_target(self):
        c=self.fixture_controller()
        with patch.object(c,'queue_boot',return_value={'status':'QUEUED'}) as boot:
            self.assertEqual(c.control({'action':'boot'})['status'],'QUEUED');boot.assert_called_once()
        with self.assertRaises(ValueError):c.control({'action':'boot','target':'linux'})

    def test_service_boot_serves_real_loopback_http(self):
        import socket
        import time
        import urllib.request
        c=self.fixture_controller();(c.state/'pairing-code').write_text('test-only');self.addCleanup(c.close)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        (self.root/'readback.txt').write_text('owned-service-readback')
        c.specs['test-http']=([sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1'],str(self.root),None,False)
        c.control({'action':'boot','target':'service','name':'test-http'})
        deadline=time.monotonic()+5
        while True:
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/readback.txt',timeout=1) as response:
                    self.assertEqual(response.read(),b'owned-service-readback')
                break
            except OSError:
                if time.monotonic()>=deadline:raise
                time.sleep(.05)
