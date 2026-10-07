#!/usr/bin/env python3
"""Deploy an admitted repository family using the owner's runtime engine."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from keddeh_namespace.web4_runtime import prepare, write_json, http_json
ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);a=ap.parse_args()
manifest=json.loads(Path(a.manifest).read_text());root=Path(manifest['runtime_root'])
if not (root/'launch.json').exists():prepare(root,manifest['library_manifest'],manifest['port_offset'])
cfg=json.loads((root/'launch.json').read_text())
if cfg.get('repository') not in (None,manifest['repository']):raise ValueError('runtime root is already bound to another repository')
cfg['vfs']=manifest['vfs'];
if 'vfs_hub' in manifest:cfg['vfs_hub']=manifest['vfs_hub']
cfg['repository']=manifest['repository'];cfg['family_id']=manifest['family_id'];cfg['engine_ref']=manifest['engine_ref'];write_json(root/'launch.json',cfg)
try:
    token=(root/'state/token').read_text()
    live=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token)
    from keddeh_namespace.web4_runtime import LaunchController
    desired=LaunchController(root).source_digest
    if live.get('family_id')!=manifest['family_id'] or live.get('source_digest')!=desired:
        subprocess.run([sys.executable,'-m','keddeh_namespace.web4_runtime','stop','--root',str(root)],check=True)
        subprocess.run([sys.executable,'-m','keddeh_namespace.web4_runtime','start','--root',str(root)],check=True)
        live=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token)
    if live['healthy_nodes']!=10:raise RuntimeError('existing family unhealthy; retain state for diagnosis')
except OSError:
    subprocess.run([sys.executable,'-m','keddeh_namespace.web4_runtime','start','--root',str(root)],check=True)
subprocess.run([sys.executable,str(Path(__file__).with_name('bootstrap_owner_environment.py')),'--root',str(root)],check=True)
token=(root/'state/token').read_text();domains=http_json(cfg['ports']['gateway'],'/api/web4/control',{'action':'domains'},token)
end=__import__('time').monotonic()+25
while __import__('time').monotonic()<end:
    bilateral=http_json(cfg['ports']['gateway'],'/api/web4/control',{'action':'bilateral'},token)
    domains=http_json(cfg['ports']['gateway'],'/api/web4/control',{'action':'domains'},token)
    if bilateral['status']=='operating' and len(domains['domains'])==3 and all(d['live'].get('ownerAlive') and len(d['live'].get('ownerPids',[]))==3 for d in domains['domains']):break
    __import__('time').sleep(.5)
else:raise RuntimeError('family did not reach live bilateral/domain readiness')
result={'schema':'keddeh.repository-family-deployment.v1','repository':manifest['repository'],'family_id':manifest['family_id'],'engine_ref':manifest['engine_ref'],'runtime_root':str(root),'healthy_workstations':10,'virtual_domains':3,'domain_workstation_processes':9,'bilateral_enabled':bilateral['enabled'],'bilateral_cycle':bilateral['cycle'],'network_namespaces':[d['live']['networkNamespace'] for d in domains['domains']],'scope':'actual cloud-host deployment; repository-pinned launch configuration'}
write_json(root/'state/family-deployment.json',result);print(json.dumps(result,indent=2))
