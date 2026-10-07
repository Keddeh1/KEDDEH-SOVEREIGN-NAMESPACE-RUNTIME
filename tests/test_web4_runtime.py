import base64
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from keddeh_namespace.web4_runtime import LaunchController, encode_readback, prepare, verify_launch, write_json

class Web4RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def test_exact_float_readback_encoding(self):
        value=encode_readback({'signal':[0.1,-0.0,1]})
        self.assertEqual(float.fromhex(value['signal'][0]['$hex']),0.1)
        self.assertEqual(value['signal'][1]['$hex'],'-0x0.0p+0')
        self.assertEqual(value['signal'][2],1)
        with self.assertRaises(ValueError):encode_readback(math.nan)

    def test_source_mutation_rejected_before_launch(self):
        p=self.root/'packages/node.js';p.parent.mkdir();p.write_text('original')
        write_json(self.root/'launch.json',{'files':{'packages/node.js':hashlib.sha256(p.read_bytes()).hexdigest()}})
        verify_launch(self.root);p.write_text('changed')
        with self.assertRaises(ValueError):verify_launch(self.root)

    def test_source_symlink_rejected(self):
        p=self.root/'packages/node.js';p.parent.mkdir();outside=self.root/'outside';outside.write_text('same');p.symlink_to(outside)
        write_json(self.root/'launch.json',{'files':{'packages/node.js':hashlib.sha256(outside.read_bytes()).hexdigest()}})
        with self.assertRaises(ValueError):verify_launch(self.root)

    def test_prepare_never_replaces_existing_state(self):
        p=self.root/'user-state';p.write_text('retain')
        with self.assertRaises(ValueError):prepare(self.root,self.root/'unused')
        self.assertEqual(p.read_text(),'retain')

    def test_failed_prepare_does_not_publish_partial_root(self):
        dest=self.root/'new-runtime';library=self.root/'empty.json';write_json(library,{'files':[]})
        with self.assertRaises(KeyError):prepare(dest,library)
        self.assertFalse(dest.exists())
        self.assertFalse(list(self.root.glob('.web4-prepare-*')))

    def fixture_controller(self):
        state=self.root/'state';state.mkdir(exist_ok=True);(self.root/'packages').mkdir(exist_ok=True)
        key=Ed25519PrivateKey.generate();(state/'generator.key').write_bytes(key.private_bytes_raw());(state/'token').write_text('x'*32)
        write_json(state/'trust.json',{'web4-local-generator':{'public_key':base64.b64encode(key.public_key().public_bytes_raw()).decode(),'roles':['generator'],'runtime_ids':['web4-local']}})
        write_json(self.root/'launch.json',{'files':{},'ports':{'mesh':[]},'estate':str(self.root/'packages'),'sources':[{'sha256':'a'*64}]})
        return LaunchController(self.root)

    def test_namespace_bridge_restart_parent_and_float_binding(self):
        controller=self.fixture_controller()
        first=controller.receipt('measurement',{'voltage':0.1})
        restarted=LaunchController(self.root);second=restarted.receipt('measurement',{'voltage':0.2})
        self.assertEqual((first['version'],second['version']),(1,2))
        self.assertEqual(len(restarted.registry.replay()),2)
        _,raw=restarted.registry.vfs.read('web4/runtime');data=json.loads(raw)
        self.assertEqual(data['signed']['envelope']['parent_envelope_sha256'],first['envelope_sha256'])
        self.assertEqual(data['desired_state']['voltage']['$hex'],float(0.2).hex())

    def test_control_rejects_bad_commit_and_unknown_command(self):
        controller=self.fixture_controller()
        for action in ({'action':'commit','node_id':1,'nonce':-1,'tenant_id':'x'},{'action':'arbitrary_shell','command':'ignored'},{'action':'estate','tool':'broker_queue_domain'}):
            with self.assertRaises(ValueError):controller.control(action)

    def test_receipt_recovery_after_commit_and_intervening_launch(self):
        c=self.fixture_controller()
        first=c.receipt('bilateral.cycle',{'cycle':1,'actors':[{'status':'ACTOR_COMMITTED'}]},request_id='cycle-one')
        resumed=LaunchController(self.root)
        resumed.receipt('runtime.launch',{'healthy_nodes':10})
        recovered=resumed.receipt('bilateral.cycle',{'cycle':1,'actors':[{'status':'ACTOR_COMMITTED'}]},request_id='cycle-one')
        self.assertEqual(first,recovered)
        self.assertEqual(len(resumed.registry.replay()),2)
        with self.assertRaises(ValueError):resumed.receipt('bilateral.cycle',{'cycle':2},request_id='cycle-one')

    def test_owner_disconnect_blocks_mutation_preserves_readback_and_stop(self):
        c=self.fixture_controller()
        state=c.control({'action':'pipeline','connected':False,'reason':'test owner isolation'})
        self.assertFalse(state['connected'])
        with self.assertRaises(RuntimeError):c.control({'action':'commit','node_id':1,'nonce':1,'tenant_id':'test'})
        self.assertFalse(c.control({'action':'projection'})['gate']['connected'])
        self.assertEqual(c.control({'action':'stop'})['status'],'shutdown requested')

    def test_bilateral_crash_after_namespace_commit_reconciles_one_receipt(self):
        from keddeh_namespace.bilateral_runtime import BilateralRuntime
        from unittest.mock import patch
        c=self.fixture_controller();c.ports['http']=4055
        observed={'healthy_nodes':10,'services':{'actor':{'alive':True}},'nodes':[{'port':19100+i,'ok':True,'state_hash':str(i)} for i in range(10)]}
        class PowerLoss(BaseException):pass
        c.bilateral.configure(True)
        durable_save=c.bilateral.save
        def cut_final_save():
            if c.bilateral.data['pending'] is None:raise PowerLoss()
            durable_save()
        with patch.object(c,'status',return_value=observed),patch('keddeh_namespace.web4_runtime.http_json',return_value={'status':'ACTOR_COMMITTED'}),patch.object(c.bilateral,'save',side_effect=cut_final_save):
            with self.assertRaises(PowerLoss):c.bilateral.tick()
        self.assertEqual(len(c.registry.replay()),1)
        restored=BilateralRuntime(c)
        self.assertEqual(len(restored.data['pending']['actors']),10)
        c.receipt('runtime.launch',{'healthy_nodes':10})
        with patch.object(c,'status',return_value=observed),patch('keddeh_namespace.web4_runtime.http_json') as actuator:
            restored.tick();actuator.assert_not_called()
        self.assertEqual(restored.data['cycle'],1)
        self.assertEqual(len(c.registry.replay()),2)

    def test_controller_restart_adopts_existing_boot_lease(self):
        from unittest.mock import patch
        c=self.fixture_controller();c.ports['broker']=18777
        command={'status':'LEASED','requestId':'owner-retained-boot','leaseId':'retained'}
        with patch('keddeh_namespace.web4_runtime.load_module'),patch('keddeh_namespace.web4_runtime.http_json',return_value={'command':command}):
            self.assertEqual(c.queue_boot(resume=True),command)
            self.assertEqual(c.current_boot_id,'owner-retained-boot')
            with self.assertRaises(ValueError):c.queue_boot()
