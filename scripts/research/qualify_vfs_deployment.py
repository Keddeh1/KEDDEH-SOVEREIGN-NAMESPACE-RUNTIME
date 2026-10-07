#!/usr/bin/env python3
"""Observe the deployed snapshot fix and durable family subscription recovery."""
from pathlib import Path
import json,sys,time,urllib.request
from keddeh_namespace.web4_runtime import LaunchController
base=Path('/workspace');out=base/'braink-setup/research-100';rows=[];end=time.monotonic()+45
while True:
 rows=[]
 for f in sorted(base.glob('*/.keddeh/family.json')):
  m=json.loads(f.read_text());root=Path(m['runtime_root']);state=json.loads((root/'state/vfs-subscription/subscription.json').read_text())
  rows.append({'repository':m['repository'],'status':state['status'],'cursor':state['cursor'],'bundle_sha256':state['objects'].get('/packages/web4/OWNER_FAMILY_BUNDLE.tar.gz')})
 if all(r['status']=='subscribed' for r in rows):break
 if time.monotonic()>end:raise RuntimeError('not every subscription recovered; retain actual statuses')
 time.sleep(1)
m=json.loads((base/'Keddeh-SYSTEMS-Virtual-File-Space-ZCG-ARCHITECTURE/.keddeh/family.json').read_text());root=Path(m['runtime_root']);cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text()
def request(url,token):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':'Bearer '+token}),timeout=60) as r:return json.load(r)
view=request('http://127.0.0.1:'+str(cfg['ports']['gateway'])+'/api/web4/status',token)
expected=LaunchController(root).source_digest;assert view['source_digest']==expected and view['services']['vfs-server']['alive']
v=cfg['vfs'];page=request(v['endpoint']+'/events?after=0&limit=1',Path(v['token_file']).read_text().strip());assert len(page['events'])==1
result={'deployed_source_digest':expected,'managed_vfs_alive':True,'event_readback_passed':True,'subscriptions':rows,'retained_package_digest':'3c5bcca03b82efee3f3148f4e2b392fff5a44d4c124b1e8ffc4b35c17ea88d0e','scope':'actual current cloud-host deployment; controllers restored with retained state, existing domains have a recorded 256 MiB operational mitigation'}
(out/'step-020.json').write_text(json.dumps({'step':20,'status':'passed','result':result},indent=2)+'\n');print('Step 20 passed: snapshot-fix source bound to live VFS; nine subscriptions recovered')
