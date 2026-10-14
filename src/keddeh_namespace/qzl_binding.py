"""Owner-controller admission and observation of the QZL schedule service."""
import hashlib,json,os,secrets,time
from pathlib import Path

def start(controller):
 cfg=controller.config.get('qzl_scheduler')
 if not cfg:return
 root=Path(cfg['app_root'])
 for name,sha in cfg['files'].items():
  if hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha:raise ValueError('QZL service custody mismatch')
 controller.spawn('qzl-scheduler',[cfg['python'],str(root/'supervisor.py'),'--config',cfg['config_file']],root,{'KEDDEH_FILE_BUDGET':str(256*1024*1024)})
 end=time.monotonic()+15
 while time.monotonic()<end:
  if controller.processes['qzl-scheduler'].poll() is not None:raise RuntimeError('QZL scheduler exited')
  view=status(controller)
  if view['healthy']:return
  time.sleep(.1)
 raise RuntimeError('QZL scheduler handshake failed')

def status(controller):
 cfg=controller.config.get('qzl_scheduler')
 if not cfg:return {'configured':False,'healthy':False}
 root=Path(json.loads(Path(cfg['config_file']).read_text())['runtime'])
 proc=controller.processes.get('qzl-scheduler')
 try:
  h=json.loads((root/'supervisor-heartbeat.json').read_text());w=json.loads((root/'heartbeat.json').read_text());os.kill(h['worker_pid'],0)
  from datetime import datetime,timezone
  fresh=(datetime.now(timezone.utc)-datetime.fromisoformat(h['time'])).total_seconds()<15
  healthy=bool(proc and proc.poll() is None and h['pid']==proc.pid and fresh and w['pid']==h['worker_pid'])
  return {'configured':True,'healthy':healthy,'supervisor':h,'worker':w,'jobs':json.loads((root/'schedule-state.json').read_text()) if (root/'schedule-state.json').exists() else {},'release_ready':(root/'current').is_dir(),'current_release':str((root/'current').resolve()) if (root/'current').is_dir() else None}
 except (OSError,ValueError,KeyError) as e:return {'configured':True,'healthy':False,'error':type(e).__name__}

def control(controller,body):
 if 'job' not in body:return status(controller)
 job=body['job']
 if job not in ('qualification','canary','promote','rollback'):raise ValueError('Unsupported QZL job')
 cfg=controller.config['qzl_scheduler'];root=Path(json.loads(Path(cfg['config_file']).read_text())['runtime']);ident=secrets.token_hex(16)
 from .web4_runtime import write_json
 write_json(root/'requests'/(ident+'.json'),{'id':ident,'job':job,'family':controller.config['family_id']})
 return {'status':'QUEUED','id':ident,'job':job,'executed':False}
