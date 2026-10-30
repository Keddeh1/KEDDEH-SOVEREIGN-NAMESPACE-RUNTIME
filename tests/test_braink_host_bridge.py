"""Actual pinned BRAINK stdio dispatcher, authenticated HTTP ingress and service."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
import test_web4_runtime
from keddeh_namespace.hydrate_service_volumes import hydrate
from keddeh_namespace.web4_runtime import copy_files, PINS, bind_braink_host_source, gateway_handler, install_braink_host_bridge, http_json

class BrainkHostBridgeTests(unittest.TestCase):
    setUp=test_web4_runtime.Web4RuntimeTests.setUp
    fixture_controller=test_web4_runtime.Web4RuntimeTests.fixture_controller

    def live_bridge(self):
        name,sha=PINS['estate']
        archive=Path(os.environ.get('KEDDEH_TEST_ESTATE_ARCHIVE',f'/workspace/library-files/KEDDEH/2026-10-07/{sha}/{name}'))
        if not archive.is_file():self.skipTest('pinned owner estate archive required for actual BRAINK integration')
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),sha)
        c=self.fixture_controller();(c.state/'pairing-code').write_text('test-only')
        hydrate(archive,self.root/'admitted',{'sha256':sha,'bytes':archive.stat().st_size},max_bytes=256*1024*1024)
        copy_files(self.root/'admitted'/sha,c.estate)
        install_braink_host_bridge(c.estate)
        server=ThreadingHTTPServer(('127.0.0.1',0),gateway_handler(c));server.daemon_threads=True
        c.ports['gateway']=server.server_port
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def cleanup():
            c.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.addCleanup(cleanup)
        c.spawn('estate',[sys.executable,str(c.estate/'server/braink_mcp.py'),'--stdio'],c.estate,stdio=True)
        c.estate_rpc('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}})
        tools=c.estate_rpc('tools/list')['tools']
        self.assertIn('host_actuator',[tool['name'] for tool in tools])
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        (self.root/'probe.txt').write_text('BRAINK actual outbound readback')
        c.specs['worker']=([sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1'],str(self.root),None,False)
        return c,port

    def call(self,c,arguments,token=None):
        return http_json(c.ports['gateway'],'/api/web4/control',{'action':'estate','tool':'host_actuator','arguments':arguments},token=c.token if token is None else token,timeout=25)['structuredContent']

    def command(self,c,operation,request):
        host=self.call(c,{'operation':'status'})
        service=next(row for row in host['services'] if row['name']=='worker')
        return {'operation':operation,'name':'worker','request_id':request,'host_id':host['host_id'],
                'instance_id':host['instance_id'],'source_digest':host['source_digest'],
                'expected_generation':service['generation'],'expected_pid':service['pid'],'pipeline_generation':host['pipeline_generation']}

    def test_inbound_braink_dispatch_service_and_persisted_outbound_result(self):
        c,port=self.live_bridge();command=self.command(c,'start','braink-start')
        started=self.call(c,command);self.assertEqual(started['status'],'COMPLETED')
        self.assertEqual(started,self.call(c,command))
        self.assertEqual(json.loads(c.actuator_path.read_text())['requests']['braink-start']['result'],started)
        for operation in ('status','restart'):
            if operation=='restart':self.assertEqual(self.call(c,self.command(c,operation,'braink-restart'))['status'],'COMPLETED')
            deadline=time.monotonic()+5
            while True:
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/probe.txt',timeout=1) as response:
                        self.assertEqual(response.read(),b'BRAINK actual outbound readback')
                    break
                except OSError:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.05)
        stopped=self.call(c,self.command(c,'stop','braink-stop'));self.assertFalse(stopped['readback']['alive'])
        c.recover_services();self.assertFalse(c.service_readback('worker')['alive'])
        with socket.socket() as sock:self.assertNotEqual(sock.connect_ex(('127.0.0.1',port)),0)
        with self.assertRaises(urllib.error.HTTPError):self.call(c,{**command,'request_id':'stale-start'})
        self.assertFalse(c.service_readback('worker')['alive'])

    def test_authorization_fence_failure_and_self_dispatch_rejection(self):
        c,_=self.live_bridge();command=self.command(c,'start','braink-start')
        with self.assertRaises(urllib.error.HTTPError) as unauthorized:self.call(c,command,token='invalid')
        self.assertEqual(unauthorized.exception.code,401);self.assertFalse(c.actuator['requests'])
        c.pipeline.configure(False,'test')
        with self.assertRaises(urllib.error.HTTPError):self.call(c,command)
        self.assertFalse(c.actuator['requests'])
        c.pipeline.configure(True,'test');command=self.command(c,'start','braink-start')
        with self.assertRaises(urllib.error.HTTPError):
            self.call(c,{**command,'projection_context':{'space':'owner','agreement_version':'1.0'}})
        self.assertFalse(c.actuator['requests'])
        with self.assertRaises(urllib.error.HTTPError):self.call(c,{**command,'name':'estate'})
        self.assertTrue(c.processes['estate'].poll() is None)
        c.specs['worker']=(c.specs['worker'][0],str(self.root/'absent'),None,False)
        failed=self.call(c,command);self.assertEqual(failed['status'],'FAILED')
        self.assertEqual(failed['error'],'FileNotFoundError')
        self.assertEqual(failed,self.call(c,command))

    def test_derivation_rejects_unknown_source(self):
        with self.assertRaises(ValueError):bind_braink_host_source('different dispatcher')

    def test_readonly_inspection_does_not_rewrite_active_actuator_state(self):
        c=self.fixture_controller()
        from keddeh_namespace.web4_runtime import LaunchController, write_json
        write_json(c.actuator_path,{'services':{},'requests':{'pending':{'status':'ACCEPTED','command':{}}}})
        before=c.actuator_path.read_bytes()
        LaunchController(self.root)
        self.assertEqual(c.actuator_path.read_bytes(),before)
        self.assertFalse((c.state/'host-binding.json').exists())

    def test_offline_upgrade_preserves_state_and_obeys_controller_lock(self):
        import fcntl
        from keddeh_namespace.web4_runtime import upgrade_braink_host_bridge, write_json, verify_launch
        c=self.fixture_controller();server=c.estate/'server';server.mkdir()
        dispatcher=server/'braink_mcp.py'
        original='from server.host_agent_adapter import host_agent_status, host_agent_self_test, host_agent_capabilities, host_agent_contract\ndef tool_defs():\n    return []\nTOOLS={}\n'
        dispatcher.write_text(original)
        config=json.loads((self.root/'launch.json').read_text())
        config['files']={str(dispatcher.relative_to(self.root)):hashlib.sha256(dispatcher.read_bytes()).hexdigest()}
        write_json(self.root/'launch.json',config)
        sentinel=c.state/'retained-state';sentinel.write_text('retain')
        self.assertEqual(upgrade_braink_host_bridge(self.root)['status'],'planned')
        self.assertEqual(dispatcher.read_text(),original)
        with (self.root/'.controller.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):upgrade_braink_host_bridge(self.root,True)
        applied=upgrade_braink_host_bridge(self.root,True)
        self.assertEqual(applied['status'],'applied_not_started');verify_launch(self.root)
        self.assertEqual(sentinel.read_text(),'retain')
        self.assertEqual((Path(applied['backup'])/'braink_mcp.py').read_text(),original)
        self.assertEqual(upgrade_braink_host_bridge(self.root,True)['status'],'already_current')
