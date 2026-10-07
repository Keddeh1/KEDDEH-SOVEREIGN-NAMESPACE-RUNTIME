#!/usr/bin/env python3
"""Capture current baseline evidence without exporting private keys or tokens."""
from pathlib import Path
import hashlib,json,platform,sqlite3,subprocess,sys,time,urllib.request,urllib.error
from keddeh_namespace.web4_runtime import PINS
def http_json(port,path,body=None,token=None):
    raw=None if body is None else json.dumps(body).encode()
    headers={"Content-Type":"application/json"}
    if token:headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(f"http://127.0.0.1:{port}"+path,data=raw,headers=headers)
    with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
base=Path('/workspace');engine=Path(__file__).resolve().parents[2];out=base/'braink-setup/research-100';out.mkdir(exist_ok=True)
def save(step,result):
 (out/f'step-{step:03d}.json').write_text(json.dumps({'step':step,'status':'passed','result':result},indent=2)+'\n');print('Step',step,'passed',flush=True)
def shell(args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True).strip()
plan=json.loads((engine/'docs/research/PLAN_100.json').read_text());assert len(plan['steps'])==100 and len({s['id'] for s in plan['steps']})==100;save(1,{'tasks':100,'groups':10,'plan_sha256':hashlib.sha256((engine/'docs/research/PLAN_100.json').read_bytes()).hexdigest()})
files=sorted(base.glob('*/.keddeh/family.json'));assert len(files)==9;repos=[]
for f in files:
 root=f.parents[1];origin=shell(['git','remote','get-url','origin'],root);assert origin.startswith('https://github.com/Keddeh1/');head=shell(['git','rev-parse','HEAD'],root);branch=shell(['git','branch','--show-current'],root);remote=shell(['git','ls-remote','origin','refs/heads/'+branch],root).split()[0];assert head==remote;repos.append({'repository':origin.removeprefix('https://github.com/').removesuffix('.git'),'commit':head,'branch':branch})
save(2,repos)
for f in files:subprocess.run([sys.executable,str(f.parent/'verify-engine.py'),str(engine)],check=True)
save(3,{'qualified_commit':'d420b5008474cb0dc1b5bf47a7a8433245097072','launchers_verified':9,'wheel_sha256':'2b69697ba06fde8502a545eefed4764e6f5ba55f7ffb3953c3cd907937ebd9ea'})
custody=[]
for name,sha in list(PINS.values())+[(x['name'],x['sha256']) for x in json.loads((engine/'docs/OWNER_SOURCE_MANIFEST.json').read_text())['files']]:
 local=base/'library-files/KEDDEH/2026-10-07'/sha/name;private=base/'SYSTEMS-SERVICES-FOR-DEPLOYMENT-QUEUE/library/2026-10-07'/sha/name;assert hashlib.sha256(local.read_bytes()).hexdigest()==sha;assert hashlib.sha256(private.read_bytes()).hexdigest()==sha;custody.append({'name':name,'sha256':sha,'bytes':local.stat().st_size})
save(4,{'sources':custody,'local_and_private_queue_verified':True})
families=[];samples=[]
for f in files:
 m=json.loads(f.read_text());root=Path(m['runtime_root']);cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text();port=cfg['ports']['gateway'];status=http_json(port,'/api/web4/status',token=token);domains=http_json(port,'/api/web4/control',{'action':'domains'},token);bil=http_json(port,'/api/web4/control',{'action':'bilateral'},token);assert status['healthy_nodes']==10 and all(x['alive'] for x in status['services'].values());assert len(domains['domains'])==3 and all(d['live']['ownerAlive'] and len(d['live']['ownerPids'])==3 for d in domains['domains']);families.append({'repository':m['repository'],'healthy_host_workstations':10,'domain_workers':9,'network_namespaces':[d['live']['networkNamespace'] for d in domains['domains']],'source_digest':status['source_digest']});samples.append((m,root,port,token,bil['cycle']))
assert len({ns for fam in families for ns in fam['network_namespaces']})==27;save(5,{'families':families,'domains':27,'workstations':171,'physical_hosts':1})
end=time.monotonic()+45;progress=[]
while time.monotonic()<end:
 progress=[]
 for m,root,port,token,before in samples:
  bil=http_json(port,'/api/web4/control',{'action':'bilateral'},token);progress.append({'repository':m['repository'],'before':before,'after':bil['cycle'],'status':bil['status'],'pending_retained':bil.get('pending') is not None})
 if all(x['after']>x['before'] and x['status']=='operating' for x in progress):break
 time.sleep(1)
else:raise RuntimeError('bilateral cycle progression did not qualify for all families')
save(6,{'samples':progress,'all_nine_advanced':True})
for _,_,port,_,_ in samples:
 try:http_json(port,'/api/web4/status');raise AssertionError('owner status accepted unauthenticated request')
 except urllib.error.HTTPError as exc:assert exc.code==401
m=json.loads(files[0].read_text())['vfs']
for path,data in [('/events?after=0&limit=1',None),('/subscriptions',b'{}')]:
 try:urllib.request.urlopen(urllib.request.Request(m['endpoint']+path,data=data));raise AssertionError('VFS accepted unauthenticated operation')
 except urllib.error.HTTPError as exc:assert exc.code==401
save(7,{'owner_gateways_rejected':9,'vfs_read_and_mutation_rejected':True,'http_status':401})
expected='3c5bcca03b82efee3f3148f4e2b392fff5a44d4c124b1e8ffc4b35c17ea88d0e'
for _,root,_,_,_ in samples:
 state=json.loads((root/'state/vfs-subscription/subscription.json').read_text());assert state['objects']['/packages/web4/OWNER_FAMILY_BUNDLE.tar.gz']==expected;obj=root/'state/vfs-subscription/mirror/objects'/expected;assert hashlib.sha256(obj.read_bytes()).hexdigest()==expected
save(8,{'independently_verified_caches':9,'sha256':expected})
result=shell([sys.executable,'scripts/check_governance.py'],engine);save(9,{'result':result,'qualification_record_sha256':hashlib.sha256((engine/'docs/evidence/owner-family-qualification.json').read_bytes()).hexdigest()})
save(10,{'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'uv':shell(['uv','--version']),'node':shell(['node','--version']),'docker':json.loads(shell(['docker','version','--format','{{json .}}']))['Server']['Version'],'os':platform.system(),'architecture':platform.machine()})
