import copy
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from keddeh_namespace.bootstrap import preflight
from keddeh_namespace.service_stack import render_stack,SERVICES,ARCHIVES
from keddeh_namespace.hydrate_service_volumes import hydrate
from keddeh_namespace.compile_zones import prepare_authority_generation
from keddeh_namespace.render_knot_config import render
import test_zones_genesis


class DeploymentGateTests(unittest.TestCase):
    def test_bootstrap_never_claims_ready_for_fixture(self):
        with self.assertRaises(ValueError): preflight({'production':False},{})
        with self.assertRaises(ValueError): preflight({'production':True},{})

    def test_authority_generation_preserves_mail_and_advances_serial(self):
        inventory=test_zones_genesis.ZonesGenesisTests.inventory(self)
        config=test_zones_genesis.ZonesGenesisTests.config(self,inventory)
        config.update(soa_serial=2,nodes=[dict(role='primary',name='ns1.example.com',public_ip='192.0.2.1'),dict(role='secondary',name='ns2.example.com',public_ip='192.0.2.2')])
        text,receipt=prepare_authority_generation(inventory,config)
        self.assertIn('1 smtp.google.com.',text);self.assertIn('complete-dkim-fixture',text)
        self.assertIn('ns2.example.com.',text);self.assertEqual(receipt['status'],'staged_authority_change_not_delegated')
        with self.assertRaises(ValueError): prepare_authority_generation(inventory,dict(config,soa_serial=1))
        primary=render(config,'primary');secondary=render(config,'secondary')
        self.assertIn('dnssec-signing: on',primary);self.assertIn('master: peer',secondary)
        self.assertNotIn('secret:',primary)

    def test_service_manifest_gate_and_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifests={};source={'archives':{}}
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,'w') as z: z.writestr('main.txt','fixture')
            payload=buffer.getvalue();archive=root/'source.zip';archive.write_bytes(payload)
            expected={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
            receipt=hydrate(archive,root/'volumes',expected)
            from keddeh_namespace.envelope import canonical_bytes
            pin=hashlib.sha256(canonical_bytes(receipt)).hexdigest()
            self.addCleanup(lambda: None)
            for name,archive_name in zip(SERVICES,ARCHIVES):
                source['archives'][archive_name]=expected
                manifests[name]={'image':'fixture/image@sha256:'+'a'*64,'volume':str(root/'volumes'/expected['sha256']),
                 'entrypoint':['fixture-only'],'port':8080,'route':'/'+name+'/','state_bytes':1024,'state_policy':'ephemeral','admission_receipt_sha256':pin}
            nginx=root/'nginx.conf';nginx.write_text('fixture')
            proxy={'image':'fixture/nginx@sha256:'+'b'*64,'listen_port':8088,'config_path':str(nginx)}
            compose,text=render_stack(manifests,source,proxy);stack=json.loads(compose)
            self.assertEqual(len(stack['services']),5)
            for name in SERVICES:
                self.assertNotIn('ports',stack['services'][name]);self.assertTrue(stack['services'][name]['read_only'])
                self.assertEqual(stack['services'][name]['cap_drop'],['ALL'])
            self.assertIn('location / { return 404; }',text)
            bad=copy.deepcopy(manifests);bad['storespace']['image']='untrusted:latest'
            with self.assertRaises(ValueError): render_stack(bad,source,proxy)
            bad=copy.deepcopy(manifests);bad['storespace']['state_policy']='persistent'
            with self.assertRaises(ValueError): render_stack(bad,source,proxy)
            # Restore directory write mode so temporary fixture cleanup is allowed.
            for path in (root/'volumes').rglob('*'):
                if path.is_dir(): path.chmod(0o755)
                elif path.is_file(): path.chmod(0o644)
