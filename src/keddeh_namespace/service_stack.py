"""Render deployment files only from admitted exact sources and explicit pinned images."""
import json
import re
from pathlib import Path
from .hydrate_service_volumes import verify_admission

SERVICES=('storespace','serverspace-mine','braink-full','braink-light')
ARCHIVES=('storespace','serverspace-mine','braink-2.1-full','braink-2.1-light')
IMAGE=re.compile(r'[a-z0-9./:_-]+@sha256:[0-9a-f]{64}')
ROUTE=re.compile(r'/[a-z0-9/_-]+/')


def render_stack(manifests,source_manifest,proxy):
    if type(manifests) is not dict or set(manifests)!=set(SERVICES): raise ValueError('four verified service manifests required')
    if not IMAGE.fullmatch(proxy.get('image','')): raise ValueError('proxy image digest pin required')
    port=proxy.get('listen_port')
    if type(port) is not int or not 1024<=port<=65535: raise ValueError('unprivileged proxy listen port required')
    config_path=Path(proxy.get('config_path','')).resolve(strict=True)
    if not config_path.is_file() or config_path.is_symlink(): raise ValueError('proxy configuration file required')
    compose={'services':{},'networks':{'services':{'internal':True}},'name':'keddeh-services'}
    routes=set();nginx=['pid /tmp/nginx.pid;','error_log stderr warn;','events {}','http {','  access_log /dev/stdout;','  server {',f'    listen {port};','    server_name _;','    location / { return 404; }']
    for name,archive_name in zip(SERVICES,ARCHIVES):
        manifest=manifests[name]
        if type(manifest) is not dict or set(manifest)!={'image','volume','entrypoint','port','route','state_bytes','state_policy','admission_receipt_sha256'}:
            raise ValueError('explicit service deployment manifest required')
        if not IMAGE.fullmatch(manifest['image']): raise ValueError('service image digest pin required')
        volume=Path(manifest['volume']).resolve(strict=True)
        receipt=verify_admission(volume,source_manifest['archives'][archive_name])
        import hashlib
        from .envelope import canonical_bytes
        if hashlib.sha256(canonical_bytes(receipt)).hexdigest()!=manifest['admission_receipt_sha256']:
            raise ValueError('admission receipt does not match trusted manifest pin')
        if volume.name!=source_manifest['archives'][archive_name]['sha256']: raise ValueError('hash-addressed service volume required')
        entrypoint=manifest['entrypoint']
        if type(entrypoint) is not list or not entrypoint or any(type(s) is not str or not s for s in entrypoint): raise ValueError('explicit argv entrypoint required')
        service_port=manifest['port'];route=manifest['route'];state=manifest['state_bytes']
        if type(service_port) is not int or not 1024<=service_port<=65535: raise ValueError('unprivileged service port required')
        if type(route) is not str or not ROUTE.fullmatch(route) or route in routes: raise ValueError('distinct explicit route required')
        if any(route.startswith(r) or r.startswith(route) for r in routes): raise ValueError('overlapping routes rejected')
        if manifest['state_policy']!='ephemeral': raise ValueError('persistent state needs independently verified quota backend')
        if type(state) is not int or not 0<state<=256*1024**2: raise ValueError('bounded writable state required')
        routes.add(route)
        compose['services'][name]={'image':manifest['image'],'user':'10001:10001','entrypoint':entrypoint,
           'read_only':True,'cap_drop':['ALL'],'security_opt':['no-new-privileges:true'],
           'pids_limit':128,'mem_limit':'512m','cpus':1.0,'networks':['services'],
           'volumes':[{'type':'bind','source':str(volume),'target':'/app','read_only':True}],
           'tmpfs':[f'/state:rw,noexec,nosuid,size={state},uid=10001,gid=10001','/tmp:rw,noexec,nosuid,size=16777216,uid=10001,gid=10001']}
        nginx += [f'    location {route} {{',f'      proxy_pass http://{name}:{service_port}/;','      proxy_set_header Host $host;',
                  '      proxy_set_header X-Forwarded-Proto $scheme;','      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;','    }']
    nginx += ['  }','}']
    compose['services']['proxy']={'image':proxy['image'],'user':'10001:10001','read_only':True,
         'cap_drop':['ALL'],'security_opt':['no-new-privileges:true'],'pids_limit':64,'mem_limit':'128m','cpus':0.5,
         'networks':['services'],'ports':[f'127.0.0.1:{port}:{port}/tcp'],
         'volumes':[{'type':'bind','source':str(config_path),'target':'/etc/nginx/nginx.conf','read_only':True}],
         'tmpfs':['/tmp:rw,noexec,nosuid,size=16777216,uid=10001,gid=10001','/var/cache/nginx:rw,noexec,nosuid,size=16777216,uid=10001,gid=10001','/var/run:rw,noexec,nosuid,size=1048576,uid=10001,gid=10001']}
    return json.dumps(compose,indent=2)+'\n','\n'.join(nginx)+'\n'
