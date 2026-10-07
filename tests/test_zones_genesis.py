import copy
import hashlib
import json
import socketserver
import threading
import unittest
from pathlib import Path
import test_runtime_foundation
from test_envelope import observation
from keddeh_namespace.compile_zones import compile_zone
from keddeh_namespace.envelope import canonical_bytes
from keddeh_namespace.genesis import LeaseController,validate_topology,probe_returns
from keddeh_namespace.signatures import sign_observation


class ZonesGenesisTests(unittest.TestCase):
    setUp=test_runtime_foundation.RuntimeTests.setUp
    def inventory(self):
        records=[dict(host='@',ttl=1800,type='SOA',value='ns1.example.com. admin.example.com. 1 3600 600 86400 300'),
                 dict(host='@',ttl=1800,type='NS',value='ns1.example.com.'),
                 dict(host='@',ttl=1800,type='MX',value='1 smtp.google.com.'),
                 dict(host='@',ttl=1800,type='TXT',value='"v=spf1 include:_spf.google.com ~all"'),
                 dict(host='@',ttl=1800,type='TXT',value='"independent-verification"'),
                 dict(host='google._domainkey',ttl=1800,type='TXT',value='"complete-dkim-fixture"')]
        return dict(zone='example.com',captured_at='2026-10-07T00:00:00Z',authority='fixture authority',records=records)
    def config(self,inventory):
        return dict(zone='example.com',preservation_sha256=hashlib.sha256(canonical_bytes(inventory)).hexdigest(),production=False)
    def test_zone_determinism_and_mail_custody(self):
        inventory=self.inventory();config=self.config(inventory)
        text,receipt=compile_zone(inventory,config)
        self.assertEqual(compile_zone(inventory,config),(text,receipt))
        self.assertIn('1 smtp.google.com.',text)
        self.assertIn('"complete-dkim-fixture"',text)
        self.assertIn('"independent-verification"',text)
    def test_missing_custody_invalid_record_and_public_address_gate(self):
        inventory=self.inventory();config=self.config(inventory)
        with self.assertRaises(ValueError): compile_zone(inventory,dict(config,preservation_sha256=None))
        bad=copy.deepcopy(inventory);bad['records'][0]['host']='outside.net.'
        with self.assertRaises(ValueError): compile_zone(bad,self.config(bad))
        production=dict(config,production=True,nodes=[dict(role='primary',name='ns1.example.com',public_ip='127.0.0.1'),dict(role='secondary',name='ns2.example.com',public_ip='127.0.0.2')])
        with self.assertRaises(ValueError): compile_zone(inventory,production)
    def test_leases_replay_resource_ceiling_freeze_and_restart(self):
        database=self.root/'leases.db';controller=LeaseController(database,cooldown=1,max_lease=100)
        controller.admit('a','nonce-a',seconds=100,now=10)
        with self.assertRaises(ValueError): controller.admit('b','nonce-b',seconds=100,now=10)
        controller.admit('b','nonce-b',seconds=100,now=11)
        controller.admit('c','nonce-c',seconds=100,now=12)
        with self.assertRaises(ValueError): controller.admit('d','nonce-d',seconds=100,now=13)
        restarted=LeaseController(database,cooldown=1,max_lease=100)
        with self.assertRaises(ValueError): restarted.admit('a','nonce-a',seconds=10,now=120)
        restarted.freeze()
        with self.assertRaises(ValueError): restarted.admit('d','nonce-d',seconds=10,now=120)
        with self.assertRaises(ValueError): restarted.reanchor(False)
        restarted.reanchor(True);self.assertEqual(restarted.admit('d','nonce-d',seconds=10,now=120),130)
    def test_actual_six_signed_return_connections(self):
        key=self.generator
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                request=json.loads(self.rfile.readline(65536))
                envelope=observation();envelope.update(runtime_id=request['child'],transaction=request['challenge'],
                                                        metric='genesis-return',readback=request['connection'])
                self.wfile.write(canonical_bytes(sign_observation(envelope,key))+b'\n')
        children=[]
        for index in range(3):
            returns=[]
            for number in range(2):
                server=socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler)
                threading.Thread(target=server.serve_forever,daemon=True).start()
                self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
                returns.append(dict(identity=f'child-{index}-return-{number}',host='127.0.0.1',port=server.server_address[1]))
            children.append(dict(identity=f'child-{index}',returns=returns))
        self.assertEqual(len(probe_returns('root',children,self.trust)),6)
        bad=copy.deepcopy(children);bad[0]['returns'][1]=bad[0]['returns'][0]
        with self.assertRaises(ValueError): validate_topology('root',bad)
        with self.assertRaises(ValueError): validate_topology('root',children[:2])
