import json,hashlib,os,shutil,subprocess,time
from pathlib import Path
from keddeh_namespace.web4_runtime import http_json
s=Path(__file__).parent;root=Path('/workspace/deployments/owner-qzl-web4');app=Path('/workspace/deployments/qzl-scheduler/app');container='keddeh-qzl-owner-resident'
assert json.loads((s/'crash-qualification.json').read_text())['status']=='PASS'
assert json.loads(Path('/workspace/work/owner-qzl-resident/canary-qualification.json').read_text())['status']=='PASS'
config=root/'launch.json';baseline=config.read_bytes();backup=s/'production-baseline';backup.mkdir(exist_ok=False)
(backup/'launch.json').write_bytes(baseline)
for n in ['scheduler.py','durable_transaction.py']:
 if (app/n).exists():shutil.copy2(app/n,backup/n)
info=json.loads(subprocess.check_output(['docker','inspect',container]))[0];assert info['Config']['Labels']['keddeh.owner-root']==str(root)
subprocess.run(['docker','stop',container],check=True)
try:
 cfg=json.loads(baseline)
 for n in ['scheduler.py','durable_transaction.py']:
  tmp=app/(n+'.new');shutil.copy2(s/n,tmp);os.replace(tmp,app/n)
  cfg['qzl_scheduler']['files'][n]=hashlib.sha256((app/n).read_bytes()).hexdigest()
 temp=config.with_suffix('.new');temp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(temp,config)
 subprocess.run(['docker','start',container],check=True)
 end=time.monotonic()+90;token=(root/'state/token').read_text()
 while True:
  try:
   v=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token)
   if v['healthy_nodes']==10 and v['qzl_scheduler']['healthy']:break
  except Exception:pass
  if time.monotonic()>end:raise RuntimeError('Readiness deadline exceeded')
  time.sleep(1)
 (s/'durability-rollout.json').write_text(json.dumps({'status':'PROMOTED','workstations':10,'custody_files':cfg['qzl_scheduler']['files'],'recovery':'write-ahead roll-forward of prepared receipts; prior release restored on unprepared interruption'},indent=2)+'\n')
except BaseException:
 subprocess.run(['docker','stop',container],check=True)
 config.write_bytes(baseline)
 for n in ['scheduler.py','durable_transaction.py']:
  if (backup/n).exists():shutil.copy2(backup/n,app/n)
  elif (app/n).exists():(app/n).unlink()
 subprocess.run(['docker','start',container],check=True);raise
