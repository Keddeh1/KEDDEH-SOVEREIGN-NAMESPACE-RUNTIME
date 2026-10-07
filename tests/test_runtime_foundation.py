import base64
import copy
import json
import os
import sqlite3
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from keddeh_namespace.envelope import envelope_digest
from keddeh_namespace.logical_vfs import LogicalVFS, Conflict
from keddeh_namespace.registry_service import Registry, make_server
from keddeh_namespace.signatures import sign_observation,verify_observation,sign_assessment,verify_assessment
from keddeh_namespace.verify_vfs import verify_volume
from test_envelope import observation


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.generator=Ed25519PrivateKey.generate();self.verifier=Ed25519PrivateKey.generate()
        self.trust={identity:{'public_key':base64.b64encode(key.public_key().public_bytes_raw()).decode(),
                              'roles':[role], 'runtime_ids':['node-1','child-0','child-1','child-2'] if role=='generator' else []} for identity,key,role in
                    [('generator-1',self.generator,'generator'),('verifier-1',self.verifier,'verifier')]}

    def signed(self,parent=None,path='state'):
        envelope=observation(parent);envelope['metric']='registry-generation:'+path
        return sign_observation(envelope,self.generator)

    def test_signatures_tamper_trust_and_assessment(self):
        signed=self.signed();digest=verify_observation(signed,self.trust)
        assessment=sign_assessment(signed,'verifier-1',self.verifier)
        self.assertEqual(verify_assessment(signed,assessment,self.trust),digest)
        altered=copy.deepcopy(signed);altered['envelope']['readback']='changed'
        with self.assertRaises(ValueError): verify_observation(altered,self.trust)
        with self.assertRaises(ValueError): verify_observation(signed,{})
        with self.assertRaises(ValueError): sign_assessment(signed,'generator-1',self.generator)
        assessment['envelope_sha256']='f'*64
        with self.assertRaises(ValueError): verify_assessment(signed,assessment,self.trust)

    def test_same_key_under_two_identities_is_not_independent(self):
        signed=self.signed()
        trust=copy.deepcopy(self.trust)
        trust['verifier-1']['public_key']=trust['generator-1']['public_key']
        assessment=sign_assessment(signed,'verifier-1',self.generator)
        with self.assertRaises(ValueError): verify_assessment(signed,assessment,trust)

    def test_vfs_versions_restart_and_corruption(self):
        vfs=LogicalVFS(self.root)
        first=vfs.write('zone/state',b'first',expected_version=0)
        second=vfs.write('zone/state',b'second',expected_version=1)
        restored=LogicalVFS(self.root)
        self.assertEqual(restored.read('zone/state')[1],b'second')
        self.assertEqual(len(restored.history()),2)
        self.assertEqual(restored.read_object(first['digest']),b'first')
        with self.assertRaises(Conflict): restored.write('zone/state',b'stale',expected_version=1)
        target=vfs.objects/second['digest'];target.chmod(0o644);target.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): restored.history()

    def test_vfs_atomic_conflict_under_concurrency(self):
        vfs=LogicalVFS(self.root)
        def writer(n):
            try: vfs.write('state',str(n).encode(),expected_version=0);return True
            except Conflict: return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(writer,range(4))),1)
        self.assertEqual(len(vfs.history()),1)

    def test_sqlite_rollback_leaves_head_unchanged(self):
        vfs=LogicalVFS(self.root)
        vfs.write('state',b'first',expected_version=0)
        with vfs.connect() as db:
            db.execute("CREATE TRIGGER reject_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): vfs.write('state',b'failed',expected_version=1)
        self.assertEqual(vfs.read('state')[1],b'first')
        self.assertEqual(len(vfs.history()),1)

    def test_path_escape_and_symlink_rejected(self):
        vfs=LogicalVFS(self.root)
        for path in ('../escape','/absolute','a/../b','a//b','./a'):
            with self.assertRaises(ValueError): vfs.write(path,b'x',expected_version=0)
        digest=vfs.put_object(b'object');target=vfs.objects/digest;target.unlink()
        outside=self.root/'outside';outside.write_bytes(b'object');target.symlink_to(outside)
        with self.assertRaises(OSError): vfs.read_object(digest)

    def test_capacity_gate_and_local_readback(self):
        result=verify_volume(self.root,required_bytes=1,require_mount=False)
        self.assertEqual(result['fsync_readback'],'passed')
        with self.assertRaises(ValueError): verify_volume(self.root,required_bytes=100_000_000_000_000,require_mount=False)
        with self.assertRaises(ValueError): verify_volume(self.root,required_bytes=1)

    def test_registry_restart_idempotency_replay_and_divergence(self):
        registry=Registry(self.root,self.trust);signed=self.signed(path='runtime/state')
        request=dict(desired_state={'generation':1},phase_state={'generation':1},request_id='first',path='runtime/state',expected_version=0,signed=signed)
        result=registry.commit(request)
        restarted=Registry(self.root,self.trust)
        self.assertEqual(restarted.commit(request),result)
        self.assertEqual(len(restarted.replay()),1)
        replay=dict(request,request_id='different')
        with self.assertRaises(Conflict): restarted.commit(replay)
        changed=dict(request,path='other')
        with self.assertRaises(ValueError): restarted.commit(changed)
        stale=dict(request,request_id='second',signed=self.signed(envelope_digest(signed['envelope']),path='runtime/state'))
        with self.assertRaises(Conflict): restarted.commit(stale)
        second=dict(stale,expected_version=1)
        restarted.commit(second);self.assertEqual(len(restarted.replay()),2)
        divergent=dict(second,request_id='third',expected_version=2,signed=self.signed('b'*64,path='runtime/state'))
        with self.assertRaises(Conflict): restarted.commit(divergent)

    def test_http_functional_commit_auth_and_readback(self):
        registry=Registry(self.root,self.trust);token='test-only-secret-token-'+'x'*32
        server=make_server(registry,token)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        url=f'http://127.0.0.1:{server.server_port}'
        with self.assertRaises(urllib.error.HTTPError) as exc: urllib.request.urlopen(url+'/health')
        self.assertEqual(exc.exception.code,401)
        payload=dict(desired_state={'generation':1},phase_state={'generation':1},request_id='http',path='state',expected_version=0,signed=self.signed())
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
        request=urllib.request.Request(url+'/generations',data=json.dumps(payload).encode(),headers=headers)
        with urllib.request.urlopen(request) as response: self.assertEqual(response.status,201)
        request=urllib.request.Request(url+'/health',headers=headers)
        with urllib.request.urlopen(request) as response: self.assertEqual(json.load(response)['verified_events'],1)
        request=urllib.request.Request(url+'/generations?path=state',headers=headers)
        with urllib.request.urlopen(request) as response:
            readback=json.load(response)
            self.assertEqual(readback['head']['version'],1)
            self.assertEqual(readback['generation']['desired_state'],{'generation':1})
        with self.assertRaises(ValueError): make_server(registry,token,host='0.0.0.0')

    def test_registry_retains_independent_assessment(self):
        registry=Registry(self.root,self.trust);signed=self.signed()
        result=registry.commit(dict(desired_state={'generation':1},phase_state={'generation':1},request_id='one',path='state',expected_version=0,signed=signed))
        assessment=sign_assessment(signed,'verifier-1',self.verifier)
        self.assertEqual(registry.assess(assessment)['status'],'assessment_signature_verified')
        restarted=Registry(self.root,self.trust)
        self.assertEqual(len(restarted.replay()),1)
        restarted.assess(assessment)  # identical retry is safe
        tampered=dict(assessment,signature='invalid')
        with self.assertRaises(ValueError): restarted.assess(tampered)

    def test_registry_atomic_abort_and_concurrent_writers(self):
        registry=Registry(self.root,self.trust)
        request=dict(desired_state={'generation':1},phase_state={'generation':1},request_id='one',path='state',expected_version=0,signed=self.signed())
        with registry.vfs.connect() as db:
            db.execute("CREATE TRIGGER reject_observation BEFORE INSERT ON observations BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): registry.commit(request)
        self.assertEqual(registry.replay(),[])
        with registry.vfs.connect() as db: db.execute('DROP TRIGGER reject_observation')
        def commit(index):
            modified=observation();modified['metric']='registry-generation:state';modified['transaction']=f'synthetic writer {index}'
            request=dict(desired_state={'generation':1},phase_state={'generation':1},request_id=str(index),path='state',expected_version=0,signed=sign_observation(modified,self.generator))
            try: registry.commit(request);return True
            except Conflict: return False
        with ThreadPoolExecutor(max_workers=4) as pool: self.assertEqual(sum(pool.map(commit,range(4))),1)
        self.assertEqual(len(registry.replay()),1)

    def test_desired_state_and_path_tampering_rejected(self):
        registry=Registry(self.root,self.trust)
        signed=self.signed()
        request=dict(desired_state={'generation':1},phase_state={'generation':1},request_id='one',path='state',expected_version=0,signed=signed)
        wrong=dict(request,desired_state={'generation':2})
        with self.assertRaises(ValueError): registry.commit(wrong)
        wrong=dict(request,path='other')
        with self.assertRaises(ValueError): registry.commit(wrong)
        self.assertEqual(registry.replay(),[])
