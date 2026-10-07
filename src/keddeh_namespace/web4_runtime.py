"""Launch owner-supplied WEB4 packages with pinned custody and real readbacks."""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import tempfile
import time
from urllib.parse import urlsplit
import urllib.request

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .envelope import SCHEMA, canonical_bytes, content_root, envelope_digest
from .hydrate_service_volumes import hydrate
from .registry_service import Registry
from .signatures import sign_observation
from .universal_propagation import PropagationRuntime, Topology

PINS = {
 'estate': ('BRAINK_MCP_PLUGIN_V5_7_BILATERAL_CLOSURE.zip','c48596dbcb4d826a1172308ab33baf6b52ff76795fce3c62262d4a20b07e5c9e'),
 'actuators': ('BRAINK_V6_1_MESH_ACTUATION_OVERLAY.zip','430db9147e822c68abf06635be1ca99131d6d10a151e536f87a82e00cf87c192'),
 'http': ('BRAINK_POSIX_HTTP4055_MULTIPLEXED_R36_20260930.zip','8718fc7486d73559a3562482245b0fe00acc322b165980c14f1fd03ff3164552'),
 'network': ('BRAINK_NETWORK_EXECUTABLE_V4_20260930 (1).tar.gz','5d73d8591b4414c7a531d7ddc1d4b8573ef63d688071caf53cbc4dc2e9362153'),
 'observer': ('BRAINK_V7_1_PERIODIC_BIO_OBSERVER_PATCH.zip','45a023ab82d314068a8b195e093ab05635a45018c5441e191d5449496bd29fa0'),
 'workbook': ('BRAINK_V7_3_BILATERAL_DIAGNOSTIC_WORKBOOK_PATCH.zip','4a47d15059006771a292327c5fc107b06fa9d04041f990e49185b43ca8d7cc9a'),
 'carrier': ('kex_html_linux_carrier.zip','2f45e96c5bb5bb20726d03138b2ecb8d14109eff449120b459ca6c68f3c64e31'),
 'terminal': ('kex_linux_terminal_mesh_patched.html','ced343b1c54d81b38c74f07d08a7dbc853a56e467dcbb83138a512c97b9cb2c7'),
 'agent': ('kex-host-agent.py','0094c4960a208734dc6d783dc5812899928dba9f6d9664ead7c979be046733d5'),
 'research_ui': ('KEDDEH_BRAINK_V76_RESIDENT_ENGINEERING_RESEARCH_VM(1).html','7f6e4ce0a41d3ba8823984533f41479be77efa7656f3e016f591af6e49c13fec'),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value, private=True):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '.' + secrets.token_hex(8))
    with temp.open('x') as stream:
        os.chmod(temp, 0o600 if private else 0o644)
        json.dump(value, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)
    directory=os.open(path.parent,os.O_RDONLY | os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)


def copy_files(source, target):
    """Mutable launch derivation; immutable admitted source remains separate."""
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(source).rglob('*')):
        if path.is_file() and path.name != '.keddeh-admission.json':
            out = target / path.relative_to(source); out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out); out.chmod(0o600)



def harden_broker_source(text):
    if '# WEB4_BROKER_FILE_LOCK_V1' in text:return text
    text=text.replace('from pathlib import Path','from pathlib import Path\nimport fcntl, contextlib',1)
    helper = """# WEB4_BROKER_FILE_LOCK_V1
@contextlib.contextmanager
def file_lock():
    with (STATE_DIR / '.broker.lock').open('a+b') as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(lock_file, fcntl.LOCK_UN)

def save_command(value):
    temp = COMMAND_FILE.with_name('.command.' + secrets.token_hex(8) + '.tmp')
    with temp.open('x') as stream:
        stream.write(json.dumps(value, indent=2)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, COMMAND_FILE)

"""
    text=text.replace('def ledger(event,payload,status="OBSERVED"):',helper+'def ledger(event,payload,status="OBSERVED"):',1)
    text=text.replace('    with LOCK:\n        rows=[]','    with LOCK, file_lock():\n        rows=[]',1)
    text=text.replace('def verify_ledger():','def _verify_ledger():',1)
    text=text.replace('def save_node(x):','def verify_ledger():\n    with LOCK, file_lock():\n        return _verify_ledger()\n\ndef save_node(x):',1)
    text=text.replace('COMMAND_FILE.write_text(json.dumps(cmd,indent=2))','save_command(cmd)')
    text=text.replace('t=COMMAND_FILE.with_suffix(".tmp"); t.write_text(json.dumps(cmd,indent=2)); os.replace(t,COMMAND_FILE)','save_command(cmd)')
    return text


def _prepare(root, library, offset=0):
    root = Path(root).absolute()
    if root.exists() and any(root.iterdir()):
        raise ValueError('prepare requires an empty root; existing state is never replaced')
    if not 0 <= offset <= 40000:
        raise ValueError('invalid port offset')
    root.mkdir(parents=True, exist_ok=True); root.chmod(0o700)
    rows = json.loads(Path(library).read_text())['files']
    by_name = {r['name']: r for r in rows}
    packages = {}; provenance = []
    for role, (name, sha) in PINS.items():
        row = by_name[name]; source = Path(row['library_path'])
        if row['sha256'] != sha or digest(source) != sha or source.stat().st_size != row['bytes']:
            raise ValueError('source custody mismatch: ' + role)
        target = root / 'packages' / role
        if name.endswith(('.zip', '.tar.gz')):
            hydrate(source, root/'admitted', {'bytes':row['bytes'], 'sha256':sha}, max_bytes=256*1024*1024)
            copy_files(root/'admitted'/sha, target)
        else:
            target.mkdir(parents=True); shutil.copyfile(source, target/name); (target/name).chmod(0o600)
        packages[role] = str(target)
        provenance.append({'role':role,'source_name':name,'source_sha256':sha,'source_bytes':row['bytes']})
    estate = Path(packages['estate'])
    # Overlay only actual node sources, not incomplete replacement MCP imports.
    copy_files(Path(packages['actuators'])/'mesh/nodes', estate/'mesh/nodes')
    observer = Path(packages['observer'])/'BRAINK_V7_1_PERIODIC_BIO_OBSERVER_PATCH'
    workbook = Path(packages['workbook'])/'BRAINK_V7_3_BILATERAL_DIAGNOSTIC_WORKBOOK_PATCH'
    copy_files(observer/'periodic_root', estate/'periodic_root')
    copy_files(workbook/'workbook_runtime', estate/'workbook_runtime')
    shutil.copyfile(workbook/'server/workbook_adapter.py', estate/'server/workbook_adapter.py')
    shutil.copyfile(Path(packages['agent'])/'kex-host-agent.py', estate/'host_agent/kex-host-agent.py')
    ports = {'gateway':18087+offset,'network':18086+offset,'http':4055+offset,'broker':18777+offset,'mesh':list(range(19100+offset,19110+offset))}
    registry_path = estate/'mesh/registry.json'; registry = json.loads(registry_path.read_text())
    for node, port in zip(registry['nodes'], ports['mesh']):node['port']=port
    registry['mesh_status_port'] += offset; registry['mcp']['url']=f'http://127.0.0.1:{ports["network"]}/mcp'
    write_json(registry_path, registry)
    harness = Path(packages['http'])/'dist-http4055/server/http4055Harness.js'
    text = harness.read_text()
    if "server.listen(4055, '127.0.0.1'" not in text:raise ValueError('unexpected HTTP harness source')
    harness.write_text(text.replace("server.listen(4055, '127.0.0.1'", "server.listen(Number(process.env.BRAINK_HTTP_PORT || '4055'), '127.0.0.1'"))
    core = Path(packages['http'])/'braink_core_runtime.py'
    text=core.read_text(); core.write_text(text.replace('self.journal_path = "braink_state_journal.bin"','self.journal_path = os.environ.get("BRAINK_JOURNAL_PATH", "braink_state_journal.bin")'))
    broker = estate/'broker/owner_broker.py'
    text = broker.read_text()
    # Existing broker omits request binding, locking and terminal lease rejection.
    text=text.replace('    def do_POST(self):','    def do_POST(self):\n        with LOCK:\n            self._locked_post()\n    def _locked_post(self):',1)
    needle='            node["nextSequence"]+=1; save_node(node)\n            result=body.get("result",{})'
    if needle not in text:raise ValueError('unexpected broker result implementation')
    text=text.replace(needle,'            result=body.get("result",{})\n            if cmd.get("status")!="LEASED" or result.get("requestId")!=cmd["requestId"] or result.get("nodeId")!=node["id"]:\n                return self.sendj({"error":"result_binding_or_state_invalid"},409)\n            node["nextSequence"]+=1; save_node(node)',1)
    broker.write_text(harden_broker_source(text))
    # Ignore bundled runtime state: these are fresh local runtime namespaces.
    state=root/'state';state.mkdir(mode=0o700)
    (state/'token').write_text(secrets.token_urlsafe(32));(state/'token').chmod(0o600)
    (state/'pairing-code').write_text(secrets.token_urlsafe(24));(state/'pairing-code').chmod(0o600)
    key=Ed25519PrivateKey.generate();(state/'generator.key').write_bytes(key.private_bytes_raw());(state/'generator.key').chmod(0o600)
    trust={'web4-local-generator':{'public_key':base64.b64encode(key.public_key().public_bytes_raw()).decode(),'roles':['generator'],'runtime_ids':['web4-local']}}
    write_json(state/'trust.json',trust)
    # Reset only derived incoming state that would otherwise assert old runtime observations.
    (estate/'data_runtime/live_state.json').unlink(missing_ok=True)
    config={'schema':'keddeh.web4.launch.v1','packages':packages,'estate':str(estate),'ports':ports,'sources':provenance,'scope':'local cloud workspace; real owner-package processes, not public deployment','derivations':['v5.7 MCP plus exact v6.1 workstation sources','observer/workbook modules integrated separately; incomplete replacement MCP not substituted','HTTP configurable port and separate journal','broker serialized requests and result/lease binding','runtime state separated from bundled evidence']}
    config['files']={str(p.relative_to(root)):digest(p) for p in (root/'packages').rglob('*') if p.is_file()}
    write_json(root/'launch.json',config)
    return {'root':str(root),'packages':len(packages),'nodes':len(ports['mesh']),'ports':ports,'source_verification':'passed'}



def prepare(root, library, offset=0):
    destination=Path(root).absolute()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('prepare requires an empty root; existing state is never replaced')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.web4-prepare-',dir=destination.parent) as temp:
        staging=Path(temp)/'runtime'
        result=_prepare(staging,library,offset)
        config=json.loads((staging/'launch.json').read_text())
        config['packages']={key:str(destination/Path(value).relative_to(staging)) for key,value in config['packages'].items()}
        config['estate']=str(destination/Path(config['estate']).relative_to(staging))
        write_json(staging/'launch.json',config)
        os.replace(staging,destination)
        result['root']=str(destination)
        return result


def verify_launch(root):
    root=Path(root);config=json.loads((root/'launch.json').read_text())
    for name, sha in config['files'].items():
        original=root/name;path=original.resolve()
        if original.is_symlink() or not path.is_relative_to((root/'packages').resolve()) or digest(path)!=sha:
            raise ValueError('launch source changed: '+name)
    return config


def http_json(port, path, body=None, token=None):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=None if body is None else json.dumps(body).encode(),headers=headers)
    with urllib.request.urlopen(req,timeout=8) as response:
        raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('readback too large')
        return json.loads(raw)


def encode_readback(value):
    if type(value) is float:
        import math
        if not math.isfinite(value):raise ValueError('nonfinite readback')
        return {'$type':'float64','$hex':value.hex()}
    if isinstance(value,dict):return {k:encode_readback(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [encode_readback(v) for v in value]
    return value


def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class LaunchController:
    def __init__(self, root):
        self.root=Path(root);self.config=verify_launch(root);self.ports=self.config['ports'];self.estate=Path(self.config['estate']);self.state=self.root/'state'
        self.token=(self.state/'token').read_text();self.stop_event=threading.Event();self.lock=threading.RLock();self.processes={};self.specs={};self.restarts={};self.stdio_lock=threading.Lock();self.rpc_responses=queue.Queue(maxsize=32);self.sequence=0
        self.registry=Registry(self.state/'registry',json.loads((self.state/'trust.json').read_text()))
        self.key=Ed25519PrivateKey.from_private_bytes((self.state/'generator.key').read_bytes())
        from importlib.metadata import version
        code=Path(__file__).parent
        self.source_manifest={'owner_sources':self.config['sources'],'derived_files':self.config['files'],'runtime_version':version('keddeh-sovereign-namespace-runtime'),'owner_control_sources':['17414b23a824cd73452ab4118de70157f0e4837c287044f9b18655df03488b25','d096d679ecbf4bc358a34b721a236a813d66318e86e8cf5ea16fdb0eaabb87e2','93904ea11317c3e4cef24fa5ab797e0688972abe78ff084992a573cb8b51c00b','e699ff4f64baace2c2dd01375f204c6c047d32108a81bbbca33b80898445e2c8'],'runtime_files':{p.name:digest(p) for p in sorted(code.iterdir()) if p.is_file() and p.suffix in ('.py','.js','.mjs')}}
        self.source_digest=hashlib.sha256(canonical_bytes(self.source_manifest)).hexdigest()
        write_json(self.state/'runtime-source-manifest.json',self.source_manifest)
        self.last_receipt=None;self.current_boot_id=None;self.retry_after={};self.recovery_errors={}
        from .bilateral_runtime import BilateralRuntime
        self.bilateral=BilateralRuntime(self)
        from .owner_kernel import KCloudNode
        self.owner_kernel=KCloudNode()
        self.owner_kernel.state='OPERATING'
        from .domain_mesh import DomainMesh
        self.domains=DomainMesh(self)
        from .vfs_subscription import VFSSubscription
        self.vfs=VFSSubscription(self)

    def env(self):
        values={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','TMPDIR','PYTHONPATH')}
        values.update(PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1',BRAINK_PLUGIN_ROOT=str(self.estate),PLUGIN_DATA=str(self.state/'estate'),BRAINK_MESH_STATE=str(self.state/'mesh/state.json'),BRAINK_MESH_LEDGER=str(self.state/'mesh/ledger.jsonl'),BRAINK_MESH_LOGS=str(self.state/'mesh/logs'),BRAINK_MESH_PIDS=str(self.state/'mesh/pids'),BRAINK_NODE_ROOTS=str(self.estate/'mesh/nodes'),BRAINK_BROKER_STATE_DIR=str(self.state/'broker'),BRAINK_BROKER_LEDGER=str(self.state/'broker/ledger.jsonl'),BRAINK_BROKER_PAIRING_CODE=(self.state/'pairing-code').read_text())
        return values

    def spawn(self,name,argv,cwd,extra=None,stdio=False):
        env=self.env();env.update(extra or {});self.specs[name]=(argv,str(cwd),extra,stdio)
        logs=self.state/'logs';logs.mkdir(exist_ok=True)
        with (logs/(name+'.log')).open('ab',buffering=0) as log:
            guarded=[sys.executable,str(Path(__file__).with_name('_web4_exec.py')),*argv]
            proc=subprocess.Popen(guarded,cwd=cwd,env=env,stdin=subprocess.PIPE if stdio else subprocess.DEVNULL,stdout=subprocess.PIPE if stdio else log,stderr=log,start_new_session=True)
        self.processes[name]=proc
        if stdio:
            def reader():
                for line in iter(lambda:proc.stdout.readline(2*1024*1024+1),b''):
                    try:self.rpc_responses.put(json.loads(line))
                    except ValueError:self.rpc_responses.put({'error':{'message':'invalid estate RPC response'}})
            threading.Thread(target=reader,daemon=True).start()
        return proc

    def wait_health(self,name,port,path,timeout=8):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if self.processes[name].poll() is not None:raise RuntimeError(name+' exited; inspect its private log')
            try:return http_json(port,path)
            except (OSError,ValueError):self.stop_event.wait(.05)
        raise RuntimeError(name+' failed functional readiness')

    def estate_rpc(self,method,params=None):
        with self.stdio_lock:
            self.sequence+=1;ident=self.sequence
            proc=self.processes['estate'];proc.stdin.write((json.dumps({'jsonrpc':'2.0','id':ident,'method':method,'params':params or {}})+'\n').encode());proc.stdin.flush()
            deadline=time.monotonic()+15
            while True:
                reply=self.rpc_responses.get(timeout=max(.01,deadline-time.monotonic()))
                if reply.get('id')==ident:break
                if time.monotonic()>=deadline:raise RuntimeError('estate RPC response deadline')
            if 'error' in reply:raise RuntimeError('estate RPC failed: '+str(reply['error']))
            return reply['result']

    def start(self):
        # No adopting an unrelated process already using a declared port.
        for port in (self.ports['gateway'],self.ports['network'],self.ports['http'],self.ports['broker'],*self.ports['mesh']):
            with socket.socket() as sock:
                sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',port))
        p=self.config['packages']
        hub=self.config.get('vfs_hub')
        if hub:
            self.spawn('vfs-server',[sys.executable,'-m','vfs_server.server','--root',hub['state_root'],'--host','127.0.0.1','--port',str(hub['port']),'--token-file',hub['token_file']],hub['code_root'])
            self.wait_health('vfs-server',hub['port'],'/ready')
        self.spawn('broker',[sys.executable,str(self.estate/'broker/owner_broker.py'),'--port',str(self.ports['broker'])],self.estate)
        self.wait_health('broker',self.ports['broker'],'/health')
        self.pair_agent()
        network=Path(p['network'])/'braink-chatgpt-plugin/server'
        self.spawn('network',['node',str(network/'dist/src/server.js')],network,{'BRAINK_MCP_HOST':'127.0.0.1','PORT':str(self.ports['network']),'BRAINK_JOURNAL_PATH':str(self.state/'network-journal.bin'),'BRAINK_ROUTE_LEDGER':str(self.state/'network-routes.jsonl'),'BRAINK_VERIFICATION_LEDGER':str(self.state/'network-verification.jsonl')})
        self.wait_health('network',self.ports['network'],'/diagnostics')
        http=Path(p['http'])
        self.spawn('http',['node',str(http/'dist-http4055/server/http4055Harness.js')],http,{'BRAINK_HTTP_PORT':str(self.ports['http']),'BRAINK_JOURNAL_PATH':str(self.state/'http-journal.bin')})
        self.wait_health('http',self.ports['http'],'/diagnostics')
        registry=json.loads((self.estate/'mesh/registry.json').read_text())
        for node in registry['nodes']:
            name='node-'+str(node['port']);script=next((self.estate/'mesh/nodes'/candidate for candidate in node['candidates'] if (self.estate/'mesh/nodes'/candidate).is_file()),None)
            if script is None:raise RuntimeError('missing exact node source')
            self.spawn(name,['node',str(script)],script.parent,{'PORT':str(node['port'])})
            health=self.wait_health(name,node['port'],'/api/health')
            if health.get('domain')!=node['id']:raise ValueError('wrong node identity')
        self.spawn('estate',[sys.executable,str(self.estate/'server/braink_mcp.py'),'--stdio'],self.estate,stdio=True)
        self.estate_rpc('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'KEDDEH-WEB4','version':'1.0'}})
        self.spawn('agent',[sys.executable,str(self.estate/'host_agent/kex-host-agent.py'),'--broker',f'http://127.0.0.1:{self.ports["broker"]}','--state-file',str(self.state/'agent.json'),'--workspace',str(self.state/'agent-volume'),'--name','KEDDEH-WEB4-CLOUD','--allow-insecure-local','--poll-interval','1'],self.estate)
        # Pair only once, without putting pairing credentials in process arguments.
        # The first pairing is completed before the persistent polling process.
        return self

    def pair_agent(self):
        agent=load_module(self.estate/'host_agent/kex-host-agent.py','web4_agent_pair')
        statefile=self.state/'agent.json'
        if not statefile.exists():
            # Suppress owner package's normal pairing log; no credentials enter output.
            import contextlib,io
            with contextlib.redirect_stdout(io.StringIO()):agent.pair(f'http://127.0.0.1:{self.ports["broker"]}',(self.state/'pairing-code').read_text(),statefile,'KEDDEH-WEB4-CLOUD',self.state/'agent-volume',None)

    def status(self):
        nodes=[]
        for port in self.ports['mesh']:
            try:health=http_json(port,'/api/health');telemetry=http_json(port,'/api/telemetry');nodes.append({'port':port,'ok':health.get('status')=='HEALTHY','domain':health.get('domain'),'compute_cycles':telemetry.get('computeCycles'),'state_hash':telemetry.get('stateHash')})
            except (OSError,ValueError) as exc:nodes.append({'port':port,'ok':False,'error':type(exc).__name__})
        services={name:{'pid':proc.pid,'alive':proc.poll() is None,'restarts':self.restarts.get(name,0)} for name,proc in self.processes.items()}
        try:
            broker=http_json(self.ports['broker'],'/api/self-host/status');command=broker.get('command') or {}
            boot_status=command.get('status') if command.get('requestId')==self.current_boot_id else 'pending current boot'
        except (OSError,ValueError):boot_status='unavailable'
        return {'source_digest':self.source_digest,'repository':self.config.get('repository'),'family_id':self.config.get('family_id'),'boot_status':boot_status,'schema':'keddeh.web4.readback.v1','scope':'local real processes','nodes':nodes,'healthy_nodes':sum(n['ok'] for n in nodes),'services':services,'last_receipt':self.last_receipt,'external_mining':'not observed; state-hash cycles are local computation'}

    def receipt(self,event,readback):
        with self.lock:
            previous=None;version=0
            try:
                head,payload=self.registry.vfs.read('web4/runtime');version=head['version'];previous=envelope_digest(json.loads(payload)['signed']['envelope'])
            except KeyError:pass
            readback=encode_readback(readback)
            phase={'event':event,'local_scope':True,'production_promoted':False}
            source=self.source_digest
            envelope=dict(schema=SCHEMA,runtime_id='web4-local',source_sha256=source,generator_id='web4-local-generator',observer_id='web4-controller',metric='registry-generation:web4/runtime',execution_plane='local-cloud-processes',observed_at=datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z'),transaction=event,readback='live HTTP/process observation',stateRoot=content_root('state',readback),phaseRoot=content_root('phase',phase),parent_envelope_sha256=previous)
            signed=sign_observation(envelope,self.key)
            result=self.registry.commit({'request_id':secrets.token_hex(16),'path':'web4/runtime','expected_version':version,'signed':signed,'desired_state':readback,'phase_state':phase})
            self.last_receipt=result;return result

    def queue_boot(self):
        # Use the supplied broker command format and actual outbound agent loop.
        broker=load_module(self.estate/'broker/owner_broker.py','web4_local_broker')
        existing=http_json(self.ports['broker'],'/api/self-host/status').get('command') or {}
        if existing.get('status') in ('QUEUED','LEASED'):raise ValueError('boot command already pending; preserve its lease')
        broker.STATE_DIR=self.state/'broker';broker.EVIDENCE=broker.STATE_DIR/'ledger.jsonl';broker.NODE_FILE=broker.STATE_DIR/'node.json';broker.COMMAND_FILE=broker.STATE_DIR/'pending_command.json'
        request='web4.boot.'+secrets.token_hex(8)
        self.current_boot_id=request
        return broker.queue_command('BOOT_SUBSTRATE',{'requestId':request,'nodeId':'broker-bound','lifecycle':['SEED','RESOLVE_TARGETS','MOUNT_WRITABLE_STATE','VERIFY_READBACK','COMPOSE_CAPABILITIES','WELCOME']})

    def restart(self,name):
        with self.lock:
            if name not in self.specs:raise ValueError('unknown owned runtime service')
            proc=self.processes[name];self.terminate(proc)
            argv,cwd,extra,stdio=self.specs[name]
            if stdio:
                while not self.rpc_responses.empty():self.rpc_responses.get_nowait()
            self.spawn(name,argv,cwd,extra,stdio);self.restarts[name]=self.restarts.get(name,0)+1
            if stdio:self.estate_rpc('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'KEDDEH-WEB4','version':'1.0'}})
            return {'name':name,'old_pid':proc.pid,'new_pid':self.processes[name].pid,'status':'restarted; readiness must be read back'}

    @staticmethod
    def terminate(proc):
        if proc.poll() is None:
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                proc.wait(timeout=3)
        # Child workers are in this group too, even when the parent exited first.
        try:os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:pass

    def close(self):
        self.stop_event.set()
        for proc in reversed(list(self.processes.values())):self.terminate(proc)

    def control(self,body):
        action=body.get('action')
        owner_index={'boot':1,'restart':-2,'stop':-3,'commit':2,'propagate':2,'bilateral':2,'domains':3,'vfs':3,'hci':3,'workbook':3,'observer':3,'estate':3}.get(action)
        if owner_index is None:raise ValueError('unsupported owner-kernel action')
        payload='A.KEDDEH:'+json.dumps(body,sort_keys=True)
        if self.owner_kernel.process_request(owner_index,payload)!='MAPPED':raise ValueError('owner kernel denied routing')
        self.owner_kernel.ledger=self.owner_kernel.ledger[-128:]
        write_json(self.state/'owner-kernel-routing.json',{'state':self.owner_kernel.state,'ledger':self.owner_kernel.ledger})
        if action=='domains':
            result=self.domains.control(body)
            if body.get('operation','status')!='status':return {'domain':result,'namespace_receipt':self.receipt('domains.'+body['operation'],result)}
            return result
        if action=='vfs':return dict(self.vfs.state)
        if action=='hci':
            from .hci_contract import KEDDEHHCIContract
            readback={'runtime':self.status(),'bilateral':dict(self.bilateral.data),'domains':self.domains.control({'operation':'status'})}
            return {'console':KEDDEHHCIContract('KEDDEH').render(readback),'readback':readback,'standards_assessment':'not independently certified'}
        if action=='bilateral':
            if 'enabled' in body:return self.bilateral.configure(body['enabled'])
            with self.bilateral.lock:return dict(self.bilateral.data)
        if action=='boot':return self.queue_boot()
        if action=='restart':return self.restart(body['name'])
        if action=='commit':
            node=body.get('node_id');nonce=body.get('nonce');tenant=body.get('tenant_id')
            if type(node) is not int or not 1<=node<=11 or type(nonce) is not int or not 0<=nonce<=0xffffffff or type(tenant) is not str or not tenant or len(tenant)>128:raise ValueError('invalid commit')
            from urllib.parse import urlencode
            result=http_json(self.ports['http'],'/api/ingress?'+urlencode({'node_id':node,'nonce':nonce,'tenant_id':tenant}),{})
            return {'actor':result,'namespace_receipt':self.receipt('http4055.commit',result),'independent_assessment':'pending'}
        if action=='propagate':
            steps=body.get('steps',100)
            if type(steps) is not int or not 1<=steps<=1000:raise ValueError('invalid steps')
            rt=PropagationRuntime(Topology.adjacency(body['adjacency']),seed=0,initial=body.get('initial'))
            for _ in range(steps):rt.tick()
            output={'states':rt.states,'steps':rt.steps,'scope':'software propagation'}
            actuate=body.get('actuate',False)
            if type(actuate) is not bool:raise ValueError('actuate must be boolean')
            if actuate:
                if len(rt.states)>len(self.ports['mesh']):raise ValueError('actuation exceeds declared workstation/register mapping')
                from urllib.parse import urlencode
                receipts=[]
                for index,value in enumerate(rt.states):
                    nonce=round(max(0.0,min(1.0,value))*0xffffffff)
                    record=http_json(self.ports['http'],'/api/ingress?'+urlencode({'node_id':index+1,'nonce':nonce,'tenant_id':'WEB4_PROPAGATION'}),{})
                    if record.get('status')!='ACTOR_COMMITTED':raise RuntimeError('R36 actuation failed; retain valid prefix for recovery')
                    receipts.append({'node_id':index+1,'workstation_port':self.ports['mesh'][index],'nonce':nonce,'actor':record})
                output.update(actuation=receipts,encoding='clamp state to [0,1], round to uint32; local R36 registers only')
            return {'output':output,'namespace_receipt':self.receipt('propagation.actuate' if actuate else 'propagation',output),'independent_assessment':'pending'}
        if action=='workbook':
            module=load_module(self.estate/'server/workbook_adapter.py','web4_workbook')
            result=module.diagnostic_run();return {'diagnostic':result,'scope':'fresh diagnostic; bundled receipts not treated as current'}
        if action=='observer':
            module=load_module(self.estate/'periodic_root/definition_node_compiler.py','web4_observer')
            return module.make_node(body.get('identity','web4://runtime'),context='cloud-runtime',observer={'id':'web4-local-observer','frame':'live-process-readback'},evidence=[str(self.state/'registry')])
        if action=='estate':
            tool=body.get('tool')
            if tool=='mesh_read_status':tool='mesh_status'
            if tool not in ('estate_status','mesh_discover','mesh_status','mesh_aggregate','mesh_verify_evidence','host_agent_capabilities','lexicon_stats','bilateral_summary','dependency_frontier'):
                raise ValueError('estate tool not exposed by this gateway')
            return self.estate_rpc('tools/call',{'name':tool,'arguments':body.get('arguments',{})})
        if action=='stop':self.stop_event.set();return {'status':'shutdown requested'}
        raise ValueError('unsupported control action')


def serve(root):
    root=Path(root);lock=(root/'.controller.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    controller=LaunchController(root);server=None
    try:
        controller.start()
        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup();self.connection.settimeout(10)
            def log_message(self,*_):pass
            def send(self,status,value,content_type='application/json'):
                raw=json.dumps(value).encode() if content_type=='application/json' else value
                self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
            def auth(self):
                value=self.headers.get('Authorization','')
                return secrets.compare_digest(value.encode('utf-8'),('Bearer '+controller.token).encode('utf-8'))
            def do_GET(self):
                path=urlsplit(self.path).path
                if path=='/health':return self.send(200,{'status':'running','scope':'local WEB4 gateway; use authenticated status for functional health'})
                if path=='/api/web4/generation':
                    if not self.auth():return self.send(401,{'error':'unauthorized'})
                    try:
                        controller.registry.replay();head,payload=controller.registry.vfs.read('web4/runtime')
                        return self.send(200,{'head':head,'generation':json.loads(payload),'source_manifest':controller.source_manifest,'assessment':'local generator receipt; independent production assessment pending'})
                    except (KeyError,ValueError,OSError):return self.send(503,{'error':'generation unavailable or invalid'})
                if path=='/api/web4/status':
                    if not self.auth():return self.send(401,{'error':'unauthorized'})
                    return self.send(200,controller.status())
                names={'/terminal':'terminal','/carrier':'carrier','/research':'research_ui'}
                if path in names:
                    role=names[path];directory=Path(controller.config['packages'][role]);files=list(directory.rglob('*.html'));raw=files[0].read_bytes()
                    addition=b'<script src="/web4-client.js"></script><script src="/web4-panel.js"></script>'
                    if role=='terminal':addition+=b'<script src="/web4-bridge.js"></script>'
                    raw=raw.replace(b'</body>',addition+b'</body>')
                    return self.send(200,raw,'text/html; charset=utf-8')
                assets={'/web4-bridge.js':'web4_bridge.js','/web4-client.js':'web4_client.js','/web4-panel.js':'web4_panel.js'}
                if path in assets:return self.send(200,(Path(__file__).parent/assets[path]).read_bytes(),'text/javascript')
                if path=='/':return self.send(200,b'<h1>KEDDEH WEB4 runtime</h1><a href="/terminal">Terminal</a> <a href="/carrier">HTML carrier</a> <a href="/research">Resident research UI</a><p>Terminal: cloud auth, cloud status, cloud boot, cloud commit NODE NONCE TENANT, cloud restart node-PORT, cloud observer, cloud workbook.</p>','text/html; charset=utf-8')
                return self.send(404,{'error':'not_found'})
            def do_POST(self):
                if urlsplit(self.path).path!='/api/web4/control':return self.send(404,{'error':'not_found'})
                if not self.auth():return self.send(401,{'error':'unauthorized'})
                origin=self.headers.get('Origin')
                if origin and origin!=f'http://127.0.0.1:{controller.ports["gateway"]}':return self.send(403,{'error':'origin denied'})
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=262144:raise ValueError('invalid body size')
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict):raise ValueError('object required')
                    output=controller.control(body);return self.send(200,output)
                except (ValueError,KeyError) as exc:return self.send(400,{'error':str(exc)})
                except Exception as exc:return self.send(502,{'error':type(exc).__name__,'detail':'inspect private runtime logs'})
        server=ThreadingHTTPServer(('127.0.0.1',controller.ports['gateway']),Handler);server.daemon_threads=True
        threading.Thread(target=server.serve_forever,daemon=True).start()
        write_json(root/'controller.json',{'pid':os.getpid(),'ports':controller.ports,'scope':'local process controller'})
        controller.receipt('runtime.launch',controller.status());controller.queue_boot()
        print('WEB4_RUNTIME_READY: authenticated gateway and real package processes',flush=True)
        signal.signal(signal.SIGTERM,lambda *_:controller.stop_event.set());signal.signal(signal.SIGINT,lambda *_:controller.stop_event.set())
        controller.domains.resume()
        while not controller.stop_event.wait(.5):
            controller.bilateral.tick()
            controller.vfs.tick()
            # One owned process per role; bounded restart rate for all owner services.
            for name,proc in list(controller.processes.items()):
                if proc.poll() is not None and time.monotonic()>=controller.retry_after.get(name,0):
                    controller.retry_after[name]=time.monotonic()+min(60,2**min(controller.restarts.get(name,0),6))
                    try:controller.restart(name);controller.recovery_errors.pop(name,None)
                    except Exception as exc:controller.recovery_errors[name]=type(exc).__name__
            write_json(controller.state/'service-recovery.json',{'restarts':controller.restarts,'errors':controller.recovery_errors})
    finally:
        if server:server.shutdown();server.server_close()
        controller.close();(root/'controller.json').unlink(missing_ok=True);lock.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','start','serve','status','stop','restart']);parser.add_argument('--root',default='/workspace/braink-setup/web4-runtime');parser.add_argument('--library',default='/workspace/library-files/KEDDEH/2026-10-07/manifest.json');parser.add_argument('--port-offset',type=int,default=0);parser.add_argument('--name');args=parser.parse_args();root=Path(args.root)
    if args.command=='prepare':print(json.dumps(prepare(root,args.library,args.port_offset),indent=2));return
    if args.command=='serve':serve(root);return
    if args.command=='start':
        config=verify_launch(root);log=(root/'controller.log').open('ab',buffering=0)
        proc=subprocess.Popen([sys.executable,'-m','keddeh_namespace.web4_runtime','serve','--root',str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        end=time.monotonic()+20;token=(root/'state/token').read_text()
        while time.monotonic()<end:
            if proc.poll() is not None:raise RuntimeError('controller exited; inspect '+str(root/'controller.log'))
            try:
                result=http_json(config['ports']['gateway'],'/api/web4/status',token=token)
                if result['healthy_nodes']==10 and result['boot_status']=='COMPLETED':print(json.dumps({'status':'running','pid':proc.pid,'healthy_nodes':10,'root':str(root)},indent=2));return
            except OSError:pass
            time.sleep(.1)
        LaunchController.terminate(proc);raise RuntimeError('launch timed out')
    config=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text()
    if args.command=='status':result=http_json(config['ports']['gateway'],'/api/web4/status',token=token)
    else:result=http_json(config['ports']['gateway'],'/api/web4/control',{'action':args.command,'name':args.name},token)
    if args.command=='stop':
        deadline=time.monotonic()+45
        with (root/'.controller.lock').open('a+b') as lock:
            while True:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()>deadline:raise RuntimeError('shutdown did not complete; processes preserved for diagnosis')
                    time.sleep(.1)
        result['status']='stopped; owned process cleanup completed'
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
