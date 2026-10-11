#!/usr/bin/env python3
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--runtime',required=True,type=Path);ap.add_argument('--start',action='store_true');a=ap.parse_args()
base=Path(__file__).resolve().parent;root=a.runtime.resolve()
# Dedicated install only: never overwrite an existing deployment or active node.
root.mkdir(parents=True,exist_ok=False,mode=0o700)
(root/'app').mkdir(mode=0o700)
shutil.copyfile(base/'scheduler.py',root/'app/scheduler.py')
shutil.copyfile(base/'supervisor.py',root/'app/supervisor.py')
shutil.copyfile(base/'owner_backend.py',root/'app/owner_backend.py')
shutil.copytree(base/'owner-package',root/'owner-package')
shutil.copytree(base/'source',root/'source')
subprocess.run([sys.executable,'-m','pip','install','--target',str(root/'deps'),'-r',str(base/'requirements.txt')],check=True)
files=[p.name for p in (root/'source').iterdir() if p.is_file()]
cfg={'runtime':str(root/'state'),'source':str(root/'source'),'python':sys.executable,'yosys':str(root/'deps/bin/yowasp-yosys'),'dependency_path':str(root/'deps'),'source_files':files,'timeout':300}
binding=json.loads((base/'owner-package-binding.json').read_text());binding['source_root']=str(root/'owner-package/src');binding['vfs_root']=str(root/'owner-vfs');cfg['owner_backend']=binding
(root/'config.json').write_text(json.dumps(cfg,indent=2));os.chmod(root/'config.json',0o600)
command=[sys.executable,str(root/'app/supervisor.py'),'--config',str(root/'config.json')]
unit='[Unit]\nDescription=QZL qualification schedule\n[Service]\nType=simple\nExecStart='+ ' '.join('"'+s.replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"' for s in command)+'\nRestart=on-failure\nRestartSec=10\nUMask=0077\nNoNewPrivileges=true\n[Install]\nWantedBy=default.target\n'
(root/'qzl-scheduler.service').write_text(unit)
result={'installed':str(root),'command':command,'systemd_unit':str(root/'qzl-scheduler.service'),'systemd_installation':'Not automatically enabled; use existing host service manager','hardware_deployment':False}
if a.start:
 with (root/'scheduler.log').open('ab') as log:p=subprocess.Popen(command,stdout=log,stderr=log,start_new_session=True)
 result['pid']=p.pid
print(json.dumps(result,indent=2))
