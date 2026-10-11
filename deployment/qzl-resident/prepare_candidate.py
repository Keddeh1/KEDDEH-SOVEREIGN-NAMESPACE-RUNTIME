import json,shutil,hashlib
from pathlib import Path
from keddeh_namespace.web4_runtime import prepare,write_json
base=Path('/workspace/deployments/owner-qzl-resident');base.mkdir(mode=0o700,exist_ok=True)
root=base/'canary-owner';q=base/'canary-qzl'
prepare(root,'/workspace/work/owner-qzl-integration/library-manifest.json',3000)
q.mkdir(mode=0o700);old=Path('/workspace/deployments/qzl-scheduler')
for d in ['app','source','owner-package']:shutil.copytree(old/d,q/d)
cfg=json.loads((old/'config.json').read_text());cfg.update(runtime=str(q/'state'),source=str(q/'source'),python='/usr/local/bin/python',yosys='/usr/local/bin/yowasp-yosys',dependency_path='',owner_family='qzl-qualified-tooling-canary')
cfg['owner_backend'].update(source_root=str(q/'owner-package/src'),vfs_root=str(q/'owner-vfs'));write_json(q/'config.json',cfg)
c=json.loads((root/'launch.json').read_text())
c['repository']='Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME';c['family_id']=cfg['owner_family'];c['engine_ref']='9bd3152e57d2612e40e700bc1d8e5b8a932fba45+qzl-resident'
c['vfs']={'endpoint':'http://127.0.0.1:21887','token_file':str(root/'state/token')}
c['vfs_hub']={'code_root':'/workspace/work/owner-qzl-integration/hub','state_root':str(root/'state/vfs-hub'),'port':21887,'token_file':str(root/'state/token')}
c['qzl_scheduler']={'app_root':str(q/'app'),'config_file':str(q/'config.json'),'python':cfg['python'],'files':{f:hashlib.sha256((q/'app'/f).read_bytes()).hexdigest() for f in ['scheduler.py','supervisor.py','owner_backend.py']}}
write_json(root/'launch.json',c);print('Separate canary prepared from supplied owner packages')
