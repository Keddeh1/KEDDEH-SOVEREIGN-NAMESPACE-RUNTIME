import copy
import http.server
import json
from pathlib import Path
import tempfile
import threading
import unittest

from keddeh_namespace.host_relay import Worker, post, validate, REQUEST_LIMIT, RESPONSE_LIMIT, COMPLETION_LIMIT


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); (self.root/'state').mkdir()
        (self.root/'state/host-binding.json').write_text(json.dumps({'host_id':'owned'}))
        (self.root/'launch.json').write_text(json.dumps({'ports':{'gateway':18087}}))
        self.args = dict(operation='restart',name='http',request_id='rpc-0001',host_id='owned',instance_id='i',source_digest='s',expected_generation=1,expected_pid=123,pipeline_generation=2)
        self.packet = dict(jsonrpc='2.0',id='rpc-0001',method='tools/call',params={'name':'host_actuator','arguments':self.args})
        self.call = dict(id='rpc-0001',claim='lease',packet=self.packet)
        self.events = []; self.fail_complete = False; self.fail_local = False
        self.worker = Worker(self.root,self.root/'dedicated-token',self.root/'pending.json',self.transport)

    def transport(self,url,token,payload):
        self.events.append(copy.deepcopy(payload))
        if payload.get('op')=='claim':return {'call':self.call}
        if payload.get('op')=='complete':
            if self.fail_complete:raise OSError('lost acknowledgement')
            return {'stored':True}
        if payload.get('arguments',{}).get('operation')=='status':
            return {'structuredContent':{'record':{'status':'COMPLETED','command':self.args,'result':{'status':'COMPLETED','request_id':'rpc-0001'}}}}
        if self.fail_local:raise OSError('uncertain local mutation')
        return {'structuredContent':{'status':'COMPLETED'},'content':[]}

    def test_complete_retry_never_reexecutes(self):
        self.fail_complete=True
        with self.assertRaises(OSError):self.worker.step()
        persisted=json.loads((self.root/'pending.json').read_text())
        self.assertIn('result',persisted)
        self.fail_complete=False
        self.assertEqual(self.worker.step(),'completed')
        self.assertEqual(sum(e.get('action')=='estate' for e in self.events),1)
        completions=[e for e in self.events if e.get('op')=='complete']
        self.assertEqual(completions[0],completions[1])
        self.assertEqual((self.root/'pending.json').stat().st_mode & 0o777,0o600)

    def test_lost_mutation_response_recovers_history_after_pipeline_changes(self):
        self.fail_local=True
        with self.assertRaises(OSError):self.worker.step()
        self.fail_local=False
        # A second mutation would now encounter a changed pipeline fence.
        original=self.transport
        def changed_pipeline(url,token,payload):
            if payload.get('arguments',{}).get('operation')=='restart':raise ValueError('stale pipeline generation')
            return original(url,token,payload)
        self.worker=Worker(self.root,self.root/'dedicated-token',self.root/'pending.json',changed_pipeline)
        self.worker.step()
        local=[e for e in self.events if e.get('arguments',{}).get('operation')=='restart']
        self.assertEqual(len(local),1);self.assertEqual(local[0]['arguments'],self.args)
        result=json.loads((self.root/'pending.json').read_text())['result']['result']
        self.assertEqual(result['structuredContent'],{'status':'COMPLETED','request_id':'rpc-0001'})
        self.assertFalse(result['isError'])
        self.assertEqual(sum(e.get('op')=='claim' for e in self.events),1)

    def test_malformed_never_calls_gateway(self):
        for mutation in ('tool','fence','host','oversize','identity'):
            with self.subTest(mutation=mutation):
                (self.root/'pending.json').unlink(missing_ok=True)
                self.call=copy.deepcopy(dict(id='rpc-0001',claim='lease',packet=self.packet))
                p=self.call['packet'];self.events=[]
                if mutation=='identity':p['params']['arguments']['request_id']='different'
                if mutation=='tool':p['params']['name']='shell'
                if mutation=='fence':p['params']['arguments'].pop('expected_pid')
                if mutation=='host':p['params']['arguments']['host_id']='other'
                if mutation=='oversize':p['params']['arguments']['name']='x'*REQUEST_LIMIT
                self.worker.step()
                self.assertFalse(any(e.get('action')=='estate' for e in self.events))
                self.assertEqual(self.events[-1]['result']['error']['code'],-32602)

    def test_lost_claim_response_reclaims_same_lease_after_restart(self):
        original=self.transport
        def lost(url,token,payload):
            if payload.get('op')=='claim':raise OSError('claim response lost')
            return original(url,token,payload)
        self.worker.transport=lost
        with self.assertRaises(OSError):self.worker.step()
        self.assertFalse((self.root/'pending.json').exists())
        self.worker=Worker(self.root,self.root/'dedicated-token',self.root/'pending.json',original)
        self.worker.step()
        saved=json.loads((self.root/'pending.json').read_text())
        self.assertEqual(saved['call'],self.call)
        self.assertEqual(sum(e.get('action')=='estate' for e in self.events),1)

    def test_uncertain_history_prevents_mutation_replay(self):
        self.fail_local=True
        with self.assertRaises(OSError):self.worker.step()
        self.fail_local=False
        original=self.transport
        def uncertain(url,token,payload):
            if payload.get('arguments',{}).get('operation')=='status':
                return {'structuredContent':{'record':{'status':'UNCERTAIN','command':self.args}}}
            return original(url,token,payload)
        self.worker.transport=uncertain
        with self.assertRaises(ValueError):self.worker.step()
        self.assertEqual(sum(e.get('arguments',{}).get('operation')=='restart' for e in self.events),1)
        self.assertNotIn('result',json.loads((self.root/'pending.json').read_text()))

    def test_claim_identity_and_id_syntax_rejected(self):
        for identity in ('mismatch-0001','bad','bad id!0001',123):
            with self.subTest(identity=identity):
                (self.root/'pending.json').unlink(missing_ok=True)
                self.call=copy.deepcopy(dict(id='rpc-0001',claim='lease',packet=self.packet))
                self.call['packet']['id']=identity
                self.events=[]
                with self.assertRaises(ValueError):self.worker.step()
                self.assertFalse(any(e.get('action')=='estate' for e in self.events))

    def test_status_and_unknown_operation(self):
        p=copy.deepcopy(self.packet);p['params']['arguments']={'operation':'status'}
        self.assertEqual(validate(p,'owned'),{'operation':'status'})
        p['params']['arguments']['operation']='shell'
        with self.assertRaises(ValueError):validate(p,'owned')

    def test_changed_host_does_not_claim_or_execute(self):
        (self.root/'pending.json').write_text(json.dumps({'host_id':'other'}))
        with self.assertRaises(ValueError):self.worker.step()
        self.assertEqual(self.events,[])

    def test_worker_http_claim_gateway_complete(self):
        observed=[];call=self.call
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                observed.append((self.path,self.headers['Authorization'],body))
                if body.get('op')=='claim':result={'call':call}
                elif body.get('op')=='complete':result={'stored':True}
                else:result={'structuredContent':{'status':'COMPLETED'},'content':[]}
                raw=json.dumps(result).encode();self.send_response(200)
                self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        (self.root/'dedicated-token').write_text('relay-test')
        (self.root/'state/token').write_text('local-test')
        origin=f'http://127.0.0.1:{server.server_port}'
        def transport(url,token,body):
            return post(origin+('/host-relay' if body.get('op') else '/api/web4/control'),token,body)
        self.worker.transport=transport
        self.assertEqual(self.worker.step(),'completed')
        self.assertEqual([r[1] for r in observed],['Bearer relay-test','Bearer local-test','Bearer relay-test'])
        self.assertEqual(observed[1][2],{'action':'estate','tool':'host_actuator','arguments':self.args})
        self.assertEqual(observed[2][2]['result']['id'],'rpc-0001')

    def test_gateway_unmarked_errors_after_entry_remain_uncertain(self):
        from types import SimpleNamespace
        from keddeh_namespace.web4_runtime import gateway_handler
        import urllib.error
        entered=[]
        def control(body):
            entered.append(body)
            if body.get('kind')=='value':raise ValueError('failure after controller entry')
            raise RuntimeError('uncertain service outcome')
        controller=SimpleNamespace(token='local-test',ports={},control=control)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),gateway_handler(controller))
        controller.ports['gateway']=server.server_port
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        token=self.root/'local-token';token.write_text('local-test')
        for kind,status in [('value',400),('runtime',502)]:
            with self.assertRaises(urllib.error.HTTPError) as failure:
                post(f'http://127.0.0.1:{server.server_port}/api/web4/control',token,{'kind':kind})
            self.assertEqual(failure.exception.code,status)
        self.assertEqual(len(entered),2)

    def test_public_proxy_preserved_and_loopback_direct(self):
        from unittest.mock import patch, MagicMock
        from keddeh_namespace.host_relay import ENDPOINT
        token=self.root/'proxy-test-token';token.write_text('test-only')
        reply=MagicMock();reply.__enter__.return_value.read.return_value=b'{"call":null}'
        opener=MagicMock();opener.open.return_value=reply
        with patch('urllib.request.ProxyHandler') as proxy, patch('urllib.request.build_opener',return_value=opener):
            post(ENDPOINT,token,{'op':'claim','host_id':'owned'})
            proxy.assert_called_once_with()
            proxy.reset_mock()
            post('http://127.0.0.1:18087/api/web4/control',token,{'action':'estate'})
            proxy.assert_called_once_with({})
            with self.assertRaises(ValueError):post('https://unapproved.invalid/',token,{})

    def test_http_contract_auth_bounds_and_redirect(self):
        observed=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                data=self.rfile.read(int(self.headers['Content-Length']))
                observed.append((self.path,self.headers['Authorization'],json.loads(data)))
                if self.path=='/redirect':
                    self.send_response(302);self.send_header('Location','/secret');self.end_headers();return
                raw=b'x'*262145 if self.path=='/large' else b'{"stored":true}'
                self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        token=self.root/'test-token';token.write_text('test-only')
        origin=f'http://127.0.0.1:{server.server_port}'
        self.assertEqual(post(origin+'/claim',token,{'op':'claim','host_id':'owned'}),{'stored':True})
        self.assertEqual(observed[0],('/claim','Bearer test-only',{'op':'claim','host_id':'owned'}))
        with self.assertRaises(ValueError):post(origin+'/large',token,{})
        with self.assertRaises(ValueError):post(origin+'/redirect',token,{})
        with self.assertRaises(ValueError):post(origin,token,{'x':'a'*REQUEST_LIMIT})
        self.assertEqual(len(observed),3)
        result={'jsonrpc':'2.0','id':'rpc-0001','result':{'text':'x'*70000}}
        self.assertEqual(post(origin+'/complete',token,{'op':'complete','result':result}),{'stored':True})
        with self.assertRaises(ValueError):
            post(origin+'/complete',token,{'op':'complete','result':{'text':'x'*RESPONSE_LIMIT}})
        with self.assertRaises(ValueError):
            post(origin+'/complete',token,{'op':'complete','result':{},'claim':'x'*COMPLETION_LIMIT})
        self.assertEqual(len(observed),4)

if __name__=='__main__':unittest.main()
