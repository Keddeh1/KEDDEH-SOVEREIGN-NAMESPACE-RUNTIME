import argparse,json,os,signal,subprocess,time,hashlib
from pathlib import Path
from keddeh_namespace.web4_runtime import http_json
ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--container',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.root);cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text();q=json.loads(Path(cfg['qzl_scheduler']['config_file']).read_text());state=Path(q['runtime'])
def inspect():return json.loads(subprocess.check_output(['docker','inspect',a.container],text=True))[0]
before=inspect();assert before['Config']['Labels']['keddeh.owner-root']==str(root) and before['HostConfig']['RestartPolicy']['Name']=='unless-stopped'
view=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token);assert view['healthy_nodes']==10 and view['qzl_scheduler']['healthy']
files={n:hashlib.sha256((state/n).read_bytes()).hexdigest() for n in ['schedule-state.json','receipt-head.json'] if (state/n).exists()}
pid=before['State']['Pid'];proc=Path('/proc')/str(pid);cmd=(proc/'cmdline').read_bytes();assert b'keddeh_namespace.web4_runtime' in cmd and str(root).encode() in cmd
assert (proc/'status').read_text().split('Uid:')[1].split()[0]==str(os.getuid())
os.kill(pid,signal.SIGKILL)
end=time.monotonic()+90
while time.monotonic()<end:
 after=inspect()
 if after['State']['Running'] and after['RestartCount']>before['RestartCount']:
  try:
   live=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token)
   if live['healthy_nodes']==10 and live['qzl_scheduler']['healthy'] and live['boot_status']=='COMPLETED':break
  except OSError:pass
 time.sleep(.5)
else:raise RuntimeError('Automatic resident recovery deadline exceeded')
for name,sha in files.items():assert hashlib.sha256((state/name).read_bytes()).hexdigest()==sha,'Durable QZL state changed after crash'
result={'status':'PASS','image':after['Image'],'container':a.container,'restart_policy':after['HostConfig']['RestartPolicy']['Name'],'old_host_pid':pid,'new_host_pid':after['State']['Pid'],'old_restart_count':before['RestartCount'],'new_restart_count':after['RestartCount'],'healthy_workstations':live['healthy_nodes'],'qzl_service_healthy':live['qzl_scheduler']['healthy'],'preserved_files':files,'signal':'SIGKILL','manual_restart_used':False}
Path(a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
