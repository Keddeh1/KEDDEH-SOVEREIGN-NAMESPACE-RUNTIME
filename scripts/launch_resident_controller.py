#!/usr/bin/env python3
"""Run the qualified owner controller under the existing Docker daemon supervisor."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from keddeh_namespace.web4_runtime import http_json, prepare, write_json, LaunchController

def run(*args):
    return subprocess.check_output(['docker',*args],text=True,stderr=subprocess.STDOUT,timeout=120).strip()

def launch(manifest_path):
    manifest_path=Path(manifest_path).resolve();manifest=json.loads(manifest_path.read_text())
    root=Path(manifest['runtime_root']).resolve()
    if not root.is_relative_to(Path('/workspace/braink-setup')):raise ValueError('owner runtime root outside admitted deployment space')
    if not (root/'launch.json').exists():prepare(root,manifest['library_manifest'],manifest['port_offset'])
    with (root/'.resident-launch.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        cfg=json.loads((root/'launch.json').read_text())
        if cfg.get('repository') not in (None,manifest['repository']):raise ValueError('runtime bound to another repository')
        for key in ('vfs','vfs_hub','frontage','repository','family_id','engine_ref'):
            if key in manifest:cfg[key]=manifest[key]
        write_json(root/'launch.json',cfg)
        admitted=json.loads((manifest_path.parent/'CONTROLLER_IMAGE.json').read_text())
        image=admitted['image_id']
        if json.loads(run('image','inspect',image))[0]['Id']!=image:raise ValueError('qualified controller image unavailable')
        name='keddeh-'+hashlib.sha256(str(root).encode()).hexdigest()[:10]+'-controller'
        current=run('ps','-a','--filter','name=^'+name+'$','-q')
        if current:
            info=json.loads(run('inspect',name))[0]
            if info['Config'].get('Labels',{}).get('keddeh.owner-root')!=str(root):raise ValueError('foreign controller container collision')
            if info['Image']!=image:
                run('stop','--time','30',name);run('rm',name);current=''
        if not current:
            token=(root/'state/token').read_text()
            try:
                http_json(cfg['ports']['gateway'],'/api/web4/control',{'action':'stop'},token,timeout=60)
                end=time.monotonic()+60
                with (root/'.controller.lock').open('a+b') as worker_lock:
                    while True:
                        try:fcntl.flock(worker_lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                        except BlockingIOError:
                            if time.monotonic()>end:raise RuntimeError('owner controller shutdown deadline')
                            time.sleep(.1)
            except ConnectionError:pass
            except OSError as exc:
                # A missing listener is safe; other failures must retain the old controller.
                if getattr(getattr(exc,'reason',exc),'errno',None)!=111:raise
            args=['create','--name',name,'--label','keddeh.owner-root='+str(root),
                  '--label','keddeh.role=resident-owner-controller','--restart','unless-stopped',
                  '--network','host','--user',f'{os.getuid()}:{os.getgid()}',
                  '--cap-drop','ALL','--security-opt','no-new-privileges','--read-only',
                  '--memory','1g','--cpus','1','--pids-limit','256',
                  '--tmpfs','/tmp:rw,noexec,nosuid,size=64m',
                  '--mount',f'type=bind,src={root},dst={root}',
                  '--mount',f'type=bind,src={root / "packages"},dst={root / "packages"},readonly',
                  '--mount','type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock',
                  '--mount',f'type=bind,src={cfg["vfs"]["token_file"]},dst={cfg["vfs"]["token_file"]},readonly']
            for binding in ('vfs_hub','frontage'):
                options=cfg.get(binding)
                if not options:continue
                directory=Path(options['code_root'] if binding=='vfs_hub' else options['source_root']).resolve()
                args+=['--mount',f'type=bind,src={directory},dst={directory},readonly']
                if binding=='vfs_hub':
                    state=Path(options['state_root']).resolve()
                    args+=['--mount',f'type=bind,src={state},dst={state}']
            run(*args,image,str(root))
        run('start',name)
        token=(root/'state/token').read_text();end=time.monotonic()+120
        while time.monotonic()<end:
            info=json.loads(run('inspect',name))[0]
            if info['RestartCount']>3:raise RuntimeError('resident controller failed repeatedly; retain logs and state')
            try:
                live=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token,timeout=10)
                if live['healthy_nodes']==10 and live['boot_status']=='COMPLETED' and live['source_digest']==LaunchController(root).source_digest:
                    result={'repository':manifest['repository'],'container':name,'image_id':image,'host_pid':info['State']['Pid'],
                            'restart_policy':info['HostConfig']['RestartPolicy']['Name'],'healthy_nodes':10,
                            'source_digest':live['source_digest'],'scope':'resident owner controller on current Docker host; trusted Docker-socket authority'}
                    write_json(root/'state/resident-controller.json',result);return result
            except OSError:pass
            time.sleep(.5)
        raise RuntimeError('resident owner controller readiness deadline; inspect owned container logs')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--manifest',required=True);args=ap.parse_args()
    print(json.dumps(launch(args.manifest),indent=2))
