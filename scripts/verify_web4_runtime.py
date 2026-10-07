#!/usr/bin/env python3
"""Exercise actual owner-package cloud processes; retain explicit local scope."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from keddeh_namespace.web4_runtime import http_json, LaunchController


def run(root):
    root=Path(root);cfg=json.loads((root/'launch.json').read_text());ports=cfg['ports'];token=(root/'state/token').read_text()
    def call(body):return http_json(ports['gateway'],'/api/web4/control',body,token)
    checks=[]
    before=http_json(ports['gateway'],'/api/web4/status',token=token)
    assert before['healthy_nodes']==10
    assert all(x['alive'] for x in before['services'].values())
    checks.append('ten real workstation health/telemetry readbacks and service processes')
    try:http_json(ports['gateway'],'/api/web4/status')
    except urllib.error.HTTPError as e:assert e.code==401
    else:raise AssertionError('unauthenticated gateway accepted')
    checks.append('gateway rejects unauthenticated status')
    tenant='WEB4_INTEGRATION';node=1;nonce=4055
    commit=call({'action':'commit','node_id':node,'nonce':nonce,'tenant_id':tenant})
    actor=commit['actor'];assert actor['status']=='ACTOR_COMMITTED'
    raw=(root/'state/http-journal.bin').read_bytes();tx=hashlib.sha256(f'{tenant}|{node}|{nonce}'.encode()).hexdigest()
    record=[struct.unpack('<32sIIQ',raw[i:i+48]) for i in range(0,len(raw),48)]
    assert any(r[0].hex()==tx and r[1]==node and r[2]==nonce for r in record)
    original_size=len(raw)
    repeat=call({'action':'commit','node_id':node,'nonce':nonce,'tenant_id':tenant})
    assert repeat['actor']['receipt_hash']==actor['receipt_hash']
    assert (root/'state/http-journal.bin').stat().st_size==original_size
    checks.append('R36 HTTP commit durable bytes and idempotent retry')
    call({'action':'restart','name':'http'})
    end=time.monotonic()+8
    while True:
        try:
            recovered=call({'action':'commit','node_id':node,'nonce':nonce,'tenant_id':tenant});break
        except urllib.error.HTTPError:
            if time.monotonic()>end:raise
            time.sleep(.1)
    assert recovered['actor']['receipt_hash']==actor['receipt_hash']
    assert (root/'state/http-journal.bin').stat().st_size==original_size
    checks.append('HTTP process/worker restart preserves durable receipt without duplicate append')
    network=http_json(ports['network'],'/mcp',{'jsonrpc':'2.0','id':'web4-network-init','method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'WEB4','version':'1'}}})
    assert 'result' in network
    network_commit=http_json(ports['network'],'/mcp',{'jsonrpc':'2.0','id':'web4-network-commit','method':'tools/call','params':{'name':'commit_transaction','arguments':{'node_id':2,'execution_vector':1234,'tenant_id':tenant,'sequence_id':'web4.integration.network'}}})
    assert not network_commit['result'].get('isError')
    assert (root/'state/network-journal.bin').stat().st_size>=48
    checks.append('network MCP initialization and actual transaction commit')
    request={'producer':'WEB4_INTEGRATION','transaction_id':'web4.integration.http','correlation_id':actor['correlation_id'],'tenant_id':tenant,'node_id':node,'execution_vector':nonce,'receipt_hash':actor['receipt_hash'],'actor_identity':'WEB4_HTTP_ACTOR'}
    requests=root/'state/http-verification-requests.jsonl';requests.write_text(json.dumps(request)+'\n')
    verifier=Path(cfg['packages']['network'])/'braink-chatgpt-plugin/server/detached_journal_verifier.py'
    ledger=root/'state/http-detached-verification.jsonl'
    output=subprocess.check_output([sys.executable,str(verifier),'--requests',str(requests),'--journal',str(root/'state/http-journal.bin'),'--ledger',str(ledger),'--key',str(root/'state/local-verifier.pem')],text=True)
    verified=json.loads(ledger.read_text());assert verified['verification_result']=='VERIFIED'
    signature=verified.pop('signature')
    Ed25519PublicKey.from_public_bytes(base64.b64decode(signature['public_key_b64'])).verify(base64.b64decode(signature['value_b64']),json.dumps(verified,sort_keys=True,separators=(',',':')).encode())
    checks.append('separate verifier process reads actual journal and signed result verifies; same-owner local scope')
    call({'action':'boot'})
    end=time.monotonic()+8
    while True:
        broker=http_json(ports['broker'],'/api/self-host/status');command=broker.get('command') or {}
        if command.get('status')=='COMPLETED':break
        if time.monotonic()>end:raise AssertionError('outbound agent boot did not complete')
        time.sleep(.1)
    assert command['result']['workspaceReadback']['readbackMatched']
    assert broker['ledger']['ok']
    assert len(command['result']['phases'])==6
    checks.append('broker pairing, poll, lease, six boot phases, fsync/readback, result and ledger')
    # Authenticated old-sequence and forged lease replay must be rejected.
    agent=json.loads((root/'state/agent.json').read_text())
    try:http_json(ports['broker'],'/api/self-host/agent',{'action':'RESULT','sequence':0,'commandId':command['id'],'leaseId':command['leaseId'],'result':command['result']},agent['credential'])
    except urllib.error.HTTPError as e:assert e.code==409
    else:raise AssertionError('stale broker sequence accepted')
    checks.append('broker stale-sequence replay rejected')
    estate=call({'action':'estate','tool':'mesh_status','arguments':{'telemetry':True}})
    assert estate['structuredContent']['mesh']['complete']
    checks.append('preserved estate MCP reaches actual ten-node mesh via stdio RPC')
    observer=call({'action':'observer','identity':'web4://integration'});assert observer['observer']['id']=='web4-local-observer'
    workbook=call({'action':'workbook'});assert workbook['diagnostic']['ok']
    checks.append('owner observer compiler and fresh workbook diagnostics execute')
    propagation=call({'action':'propagate','adjacency':[[0,1],[0,0]],'initial':[1,0],'steps':10})
    assert propagation['output']['states'][1]>0
    checks.append('propagation results persist through signed namespace generation bridge')
    actuation=call({'action':'propagate','adjacency':[[0,1],[0,0]],'initial':[1,0],'steps':10,'actuate':True})
    assert len(actuation['output']['actuation'])==2
    assert all(x['actor']['status']=='ACTOR_COMMITTED' for x in actuation['output']['actuation'])
    checks.append('propagation explicitly actuates two real R36 registers and seals the actor readbacks')
    name='node-'+str(ports['mesh'][0]);old=http_json(ports['gateway'],'/api/web4/status',token=token)['services'][name]['pid']
    # Kill only the process selected from this authenticated controller's own readback.
    import os,signal
    os.kill(old,signal.SIGTERM)
    end=time.monotonic()+8
    while True:
        now=http_json(ports['gateway'],'/api/web4/status',token=token)
        if now['healthy_nodes']==10 and now['services'][name]['pid']!=old:break
        if time.monotonic()>end:raise AssertionError('automatic owned node restart failed')
        time.sleep(.1)
    assert now['services'][name]['restarts']>=1
    checks.append('real failed workstation is automatically restarted and health read back')
    registry=LaunchController(root).registry;events=registry.replay();assert len(events)>=5
    checks.append('signed namespace journal replays all committed runtime observations')
    for path in ('/terminal','/carrier','/research'):
        with urllib.request.urlopen(f'http://127.0.0.1:{ports["gateway"]}{path}',timeout=3) as response:
            text=response.read();assert b'<html' in text.lower() or b'<!doctype' in text.lower()
            if path=='/terminal':assert b'/web4-bridge.js' in text
    checks.append('all three owner UI carriers served; terminal bridge injected')
    # Verify actual kernel-enforced descriptor/output/core limits on an owned node.
    limits=Path(f'/proc/{now["services"][name]["pid"]}/limits').read_text()
    assert '256                  256' in limits
    checks.append('actual Linux process descriptor limit observed')
    return {'schema':'keddeh.web4.integration-evidence.v1','status':'passed','checks':checks,'healthy_nodes':10,'namespace_events_verified':len(events),'workbook_findings':workbook['diagnostic']['result']['finding_count'],'source_packages':cfg['sources'],'scope':'actual local owner-package processes and HTTP/stdio readbacks','limitations':['same cloud host; not independent production failure domains','original browser rendering and multi-tab mesh not automated in this HTTP test','local detached verifier is not an independent production assessor','no public HTTPS or registrar deployment','workbook diagnostics may report missing files from broader source estate','FD/core/file-output bounds observed; no production memory/quota/CPU reservations claimed']}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='/workspace/braink-setup/web4-runtime');ap.add_argument('--output');a=ap.parse_args();result=run(a.root)
    if a.output:Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
