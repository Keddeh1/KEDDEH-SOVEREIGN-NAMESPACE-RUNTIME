"""Promote a qualified resident controller; preserve configurations and roll back on failure."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
from keddeh_namespace.web4_runtime import http_json,write_json
work=Path(__file__).parent;owner=Path('/workspace/deployments/owner-qzl-web4');qzl=Path('/workspace/deployments/qzl-scheduler');name='keddeh-qzl-owner-resident'
report=json.loads((work/'canary-qualification.json').read_text());assert report['status']=='PASS'
assert json.loads((work/'canary-promotion.json').read_text())['status']=='PASS'
recovery=json.loads((work/'canary-recovery.json').read_text());assert recovery['status']=='PASS'
image=subprocess.check_output(['docker','image','inspect','keddeh-owner-qzl:canary','--format','{{.Id}}'],text=True).strip();assert image==recovery['image']
backup=work/'pre-rollout';backup.mkdir(mode=0o700,exist_ok=False)
for path in [owner/'launch.json',qzl/'config.json']:shutil.copyfile(path,backup/(path.parent.name+'-'+path.name))
cfg=json.loads((owner/'launch.json').read_text());token=(owner/'state/token').read_text();before=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token);assert before['healthy_nodes']==10 and before['qzl_scheduler']['healthy']
env=dict(os.environ);env['PYTHONPATH']='/workspace/work/owner-qzl-integration/engine:/workspace/work/owner-qzl-integration/hub'
try:
 subprocess.run([sys.executable,'-m','keddeh_namespace.web4_runtime','stop','--root',str(owner)],env=env,check=True,capture_output=True)
 q=json.loads((qzl/'config.json').read_text());q.update(python='/usr/local/bin/python',yosys='/usr/local/bin/yowasp-yosys',dependency_path='');write_json(qzl/'config.json',q)
 cfg['qzl_scheduler']['python']=q['python'];cfg['engine_ref']='9bd3152e57d2612e40e700bc1d8e5b8a932fba45+qzl-resident';write_json(owner/'launch.json',cfg)
 args=['docker','create','--name',name,'--label','keddeh.owner-root='+str(owner),'--label','keddeh.role=resident-owner-controller','--restart','unless-stopped','--network','host','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--memory','2g','--cpus','2','--pids-limit','256','--tmpfs','/tmp:rw,nosuid,size=256m']
 for src,ro in [(str(owner),False),(str(qzl),False),(str(owner/'packages'),True),('/workspace/work/owner-qzl-integration/hub',True),('/var/run/docker.sock',False)]:args+=['--mount','type=bind,src='+src+',dst='+src+(',readonly' if ro else '')]
 args+=['-e','PYTHONPATH=/workspace/work/owner-qzl-integration/hub',image,str(owner)]
 subprocess.run(args,check=True,capture_output=True);subprocess.run(['docker','start',name],check=True,capture_output=True)
 end=time.monotonic()+90
 while time.monotonic()<end:
  try:
   live=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token)
   if live['healthy_nodes']==10 and live['qzl_scheduler']['healthy'] and live['boot_status']=='COMPLETED':break
  except OSError:pass
  time.sleep(.5)
 else:raise RuntimeError('Resident qualification deadline exceeded')
 result={'status':'PROMOTED','container':name,'image':image,'restart_policy':'unless-stopped','baseline':before,'observed':live,'rollback_configs':str(backup),'preserved_runtime':str(owner),'preserved_qzl':str(qzl)};write_json(work/'production-rollout.json',result);print(json.dumps({'status':'PROMOTED','container':name,'healthy_nodes':live['healthy_nodes']}))
except Exception:
 subprocess.run(['docker','stop','--timeout','30',name],capture_output=True)
 for path in [owner/'launch.json',qzl/'config.json']:shutil.copyfile(backup/(path.parent.name+'-'+path.name),path)
 subprocess.run([sys.executable,'-m','keddeh_namespace.web4_runtime','start','--root',str(owner)],env=env,check=True)
 raise
