#!/usr/bin/env python3
"""Persistent, isolated QZL tooling scheduler. Does not deploy FPGA/silicon firmware."""
import argparse,datetime as dt,fcntl,hashlib,json,os,shutil,subprocess,tempfile,time,uuid
from pathlib import Path
from zoneinfo import ZoneInfo
_owner_backend=None
def bind_owner(cfg):
 global _owner_backend
 if 'owner_backend' in cfg:
  from owner_backend import OwnerBackend
  _owner_backend=OwnerBackend(cfg)
TZ=ZoneInfo('Australia/Adelaide')
def seal(path,data):
 if _owner_backend:_owner_backend.commit(path,data)
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
  f.write(data);f.flush();os.fsync(f.fileno());tmp=f.name
 os.replace(tmp,path)
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def encode(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def read(p):
 payload=_owner_backend.read(p) if _owner_backend else None
 return json.loads(payload if payload is not None else p.read_bytes())
def digest_tree(p):
 return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob('*')) if f.is_file()}
def switch(root,name,target):
 tmp=root/(name+'.'+uuid.uuid4().hex);tmp.symlink_to(target);os.replace(tmp,root/name)
 fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def execute(cfg,job,slot):
 bind_owner(cfg)
 root=Path(cfg['runtime']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (root/'schedule.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  state=read(root/'schedule-state.json') if (root/'schedule-state.json').exists() else {}
  prior=state.get(slot if slot.startswith('queue-') else job,{})
  if prior.get('slot')==slot and prior.get('status')=='PASS':return {'status':'ALREADY_COMPLETED','job':job,'slot':slot}
  receipt={'job':job,'slot':slot,'started':dt.datetime.now(TZ).isoformat(),'scope':'QZL RTL qualification/tooling; no hardware deployment'}
  try:
   if job=='qualification':
    run=root/'runs'/uuid.uuid4().hex;run.mkdir(parents=True,mode=0o700)
    for name in cfg['source_files']:shutil.copyfile(Path(cfg['source'])/name,run/name)
    env=dict(os.environ);env['PYTHONPATH']=cfg['dependency_path']
    r=subprocess.run([cfg['python'],str(run/'run_qualification.py'),'--yosys',cfg['yosys']],cwd=run,env=env,capture_output=True,text=True,timeout=cfg.get('timeout',300))
    seal(run/'runner.log',(r.stdout+r.stderr).encode())
    if r.returncode:raise RuntimeError('Qualification failed; inspect '+str(run/'runner.log'))
    q=read(run/'qualification.json')
    if q['status']!='PASS_WITH_LIMITATIONS' or not all(q['checks'].values()):raise RuntimeError('Qualification contract rejected')
    manifest={'path':str(run),'digests':digest_tree(run),'qualified_at':dt.datetime.now(TZ).isoformat()}
    seal(root/'qualified.json',encode(manifest));receipt['release']=str(run)
   elif job=='canary':
    m=read(root/'qualified.json');src=Path(m['path'])
    if digest_tree(src)!=m['digests']:raise RuntimeError('Qualified source changed')
    if (dt.datetime.now(TZ)-dt.datetime.fromisoformat(m['qualified_at'])).total_seconds()>86400:raise RuntimeError('Qualification older than 24h')
    release=root/'releases'/uuid.uuid4().hex;shutil.copytree(src,release)
    env=dict(os.environ);env['PYTHONPATH']=cfg['dependency_path']
    r=subprocess.run([cfg['python'],str(release/'run_qualification.py'),'--yosys',cfg['yosys']],cwd=release,env=env,capture_output=True,text=True,timeout=cfg.get('timeout',300))
    if r.returncode:raise RuntimeError('Canary failed: '+r.stderr[-1000:])
    switch(root,'canary',release)
    seal(root/'canary.json',encode({'path':str(release),'digests':digest_tree(release),'qualified_at':dt.datetime.now(TZ).isoformat()}));receipt['release']=str(release)
   elif job=='promote':
    m=read(root/'canary.json');release=Path(m['path'])
    if digest_tree(release)!=m['digests']:raise RuntimeError('Canary changed')
    if (dt.datetime.now(TZ)-dt.datetime.fromisoformat(m['qualified_at'])).total_seconds()>86400:raise RuntimeError('Canary older than 24h')
    if (root/'current').is_symlink():switch(root,'previous',(root/'current').resolve())
    switch(root,'current',release);receipt['release']=str(release)
   elif job=='rollback':
    old=(root/'previous').resolve(strict=True);switch(root,'current',old);receipt['release']=str(old)
   else:raise ValueError('Unknown job')
   receipt['status']='PASS'
  except Exception as e:receipt.update(status='FAIL',error=str(e))
  receipt['finished']=dt.datetime.now(TZ).isoformat()
  receipts=root/'receipts';receipts.mkdir(exist_ok=True,mode=0o700)
  head=read(root/'receipt-head.json') if (root/'receipt-head.json').exists() else {'sha256':None}
  receipt['previous_sha256']=head['sha256'];payload=encode(receipt);sha=hashlib.sha256(payload).hexdigest()
  seal(receipts/(uuid.uuid4().hex+'.json'),payload);seal(root/'receipt-head.json',encode({'sha256':sha}))
  state[('manual:'+job) if slot.startswith(('manual-','queue-')) else job]={'slot':slot,'status':receipt['status'],'receipt_sha256':sha}
  if slot.startswith('queue-'):state[slot]={'slot':slot,'status':receipt['status'],'receipt_sha256':sha}
  seal(root/'schedule-state.json',encode(state));return receipt

def slots(now):
 jobs=[]
 if now.hour>=6:jobs.append(('qualification',now.date().isoformat()))
 if now.weekday()==6:
  if (now.hour,now.minute)>=(6,30):jobs.append(('canary',now.date().isoformat()))
  if now.hour>=7:jobs.append(('promote',now.date().isoformat()))
 return jobs

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--run',choices=['qualification','canary','promote','rollback']);ap.add_argument('--serve',action='store_true');a=ap.parse_args();cfg=read(Path(a.config))
 if a.run:
  r=execute(cfg,a.run,'manual-'+uuid.uuid4().hex);print(json.dumps(r));return 0 if r['status']=='PASS' else 1
 if not a.serve:ap.error('Choose --run or --serve')
 bind_owner(cfg)
 root=Path(cfg['runtime']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (root/'daemon.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  while True:
   for job,slot in slots(dt.datetime.now(TZ)):
    state=read(root/'schedule-state.json') if (root/'schedule-state.json').exists() else {}
    prior=state.get(job,{})
    # One scheduled attempt per slot, including failures; explicit retry uses --run.
    if prior.get('slot')!=slot:print(json.dumps(execute(cfg,job,slot)),flush=True)
   requests=root/'requests';requests.mkdir(exist_ok=True,mode=0o700)
   for req in sorted(requests.glob('*.json'))[:20]:
    try:
     item=read(req)
     if item.get('family')!=cfg.get('owner_family') or item.get('id')!=req.stem or item.get('job') not in ['qualification','canary','promote','rollback']:raise ValueError('Queue admission mismatch')
     result=execute(cfg,item['job'],'queue-'+item['id'])
     seal(root/'request-results'/(req.stem+'.json'),encode(result));req.unlink()
    except Exception as e:
     seal(root/'request-results'/(req.stem+'.json'),encode({'status':'FAIL','error':str(e)}));req.rename(req.with_suffix('.rejected'))
   seal(root/'heartbeat.json',encode({'time':dt.datetime.now(TZ).isoformat(),'pid':os.getpid(),'status':'RUNNING'}));time.sleep(30)
if __name__=='__main__':raise SystemExit(main())
