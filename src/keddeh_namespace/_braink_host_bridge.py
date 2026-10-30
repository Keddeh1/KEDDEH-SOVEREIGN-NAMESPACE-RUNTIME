"""Bounded callback from the existing owner BRAINK MCP dispatcher to WEB4."""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

HOST_ACTUATOR_TOOL = {
    'name':'host_actuator',
    'description':'Dispatch a descriptor-bound owned service operation through the existing WEB4 owner gateway; return persisted actuator outcome.',
    'inputSchema':{'type':'object','properties':{'operation':{'type':'string','enum':['status','start','stop','restart']},
        'name':{'type':'string'},'request_id':{'type':'string','maxLength':128},
        'host_id':{'type':'string'},'instance_id':{'type':'string'},'source_digest':{'type':'string'},
        'expected_generation':{'type':'integer','minimum':0},'expected_pid':{'type':['integer','null']},
        'pipeline_generation':{'type':'integer','minimum':0},'projection_context':{'type':'object'}},
        'required':['operation'],'additionalProperties':False}}


def host_actuator(arguments):
    if type(arguments) is not dict:raise ValueError('host actuator arguments must be an object')
    if set(arguments)-set(HOST_ACTUATOR_TOOL['inputSchema']['properties']):raise ValueError('unsupported host actuator argument')
    operation=arguments.get('operation')
    if operation not in ('status','start','stop','restart'):raise ValueError('unsupported host actuator operation')
    # A synchronous callback cannot terminate/reinitialize the dispatcher waiting for its result.
    if operation!='status' and arguments.get('name')=='estate':
        raise ValueError('use direct owner host control for the estate dispatcher lifecycle')
    port=int(os.environ['KEDDEH_WEB4_GATEWAY_PORT'])
    if not 1<=port<=65535:raise ValueError('invalid local gateway port')
    token=Path(os.environ['KEDDEH_WEB4_TOKEN_FILE']).read_text()
    payload=json.dumps({'action':'host',**arguments}).encode()
    if len(payload)>262144:raise ValueError('host actuator input exceeds bound')
    request=urllib.request.Request(f'http://127.0.0.1:{port}/api/web4/control',data=payload,
        headers={'Content-Type':'application/json','Authorization':'Bearer '+token},method='POST')
    # No proxy, arbitrary destination, token argument, or automatic retry is accepted.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request,timeout=20) as response:
            raw=response.read(2*1024*1024+1)
    except urllib.error.HTTPError as exc:
        raw=exc.read(4097)
        try:rejection=json.loads(raw) if len(raw)<=4096 else None
        except ValueError:rejection=None
        if (exc.code in (400,401,403) and type(rejection) is dict
                and set(rejection)=={'schema','effect','code'}
                and rejection.get('schema')=='keddeh.host-rejection.v1'
                and rejection.get('effect')=='none'
                and rejection.get('code') in ('AUTH_DENIED','ORIGIN_DENIED','INVALID_BODY','ADMISSION_REJECTED')):
            return rejection
        raise RuntimeError('WEB4 host actuator rejected request: HTTP '+str(exc.code)) from None
    if len(raw)>2*1024*1024:raise ValueError('host actuator response exceeds bound')
    result=json.loads(raw)
    if type(result) is not dict:raise ValueError('invalid host actuator result')
    return result
