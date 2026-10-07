"""Owned recursive dual-network domains carrying owner workstation execution."""
import fcntl
import ipaddress
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time

IMAGE='node@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20'
class DomainMesh:
    def __init__(self, controller):
        self.controller=controller;self.root=controller.state/'domains';self.root.mkdir(exist_ok=True)
        self.path=self.root/'topology.json'
        self.data=json.loads(self.path.read_text()) if self.path.exists() else {'enabled':False,'domains':[]}
        self.prefix='keddeh-'+hashlib.sha256(str(controller.root).encode()).hexdigest()[:10]
        self.label='keddeh.owner-root='+str(controller.root)

    def run(self,*args):
        p=subprocess.run(['docker',*args],text=True,capture_output=True,timeout=40)
        if p.returncode:raise RuntimeError('owned domain Docker operation failed: '+p.stderr.strip()[:400])
        return p.stdout.strip()
    def save(self):
        from .web4_runtime import write_json
        write_json(self.path,self.data)
    def network(self,name):
        with open("/tmp/keddeh-domain-network-allocator.lock","a+b") as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            return self._network_locked(name)
    def _network_locked(self,name):
        existing=self.run('network','ls','--filter','name=^'+name+'$','-q')
        if existing:
            obj=json.loads(self.run('network','inspect',name))[0]
            if obj.get('Labels',{}).get('keddeh.owner-root')!=str(self.controller.root):raise ValueError('foreign network name collision')
        else:
            ids=self.run('network','ls','-q').split()
            existing=json.loads(self.run('network','inspect',*ids)) if ids else []
            occupied=[ipaddress.ip_network(c['Subnet']) for n in existing for c in (n.get('IPAM',{}).get('Config') or []) if c.get('Subnet')]
            subnet=next((ipaddress.ip_network(f'10.240.{i}.0/24') for i in range(256) if not any(ipaddress.ip_network(f'10.240.{i}.0/24').overlaps(s) for s in occupied if s.version==4)),None)
            if subnet is None:raise RuntimeError('declared domain subnet pool exhausted')
            self.run('network','create','--internal','--subnet',str(subnet),'--label',self.label,name)
    def container(self,domain):return self.prefix+'-'+domain
    def spawn(self,parent=None):
        from .web4_runtime import write_json
        if len(self.data['domains'])>=8:raise ValueError('declared eight-domain local capacity reached')
        rows=self.data['domains'];known={r['id']:r for r in rows}
        if parent is not None and parent not in known:raise ValueError('unknown parent domain')
        if rows and parent is None:raise ValueError('only one genesis domain')
        ident='domain-'+str(len(rows));directory=self.root/ident;directory.mkdir(exist_ok=True)
        code=directory/'code';state=directory/'state';code.mkdir(exist_ok=True);state.mkdir(exist_ok=True)
        shutil.copyfile(Path(__file__).with_name('web4_domain.mjs'),code/'bridge.mjs')
        owner=self.controller.estate/'mesh/nodes/kex_server_space_workstation.js'
        shutil.copyfile(owner,code/'owner.mjs')
        token=self.root/'token'
        if not token.exists():token.write_text(secrets.token_hex(32));token.chmod(0o600)
        shutil.copyfile(token,state/'token');(state/'token').chmod(0o600)
        upstream=known[parent]['downstream'] if parent else self.prefix+'-genesis'
        downstream=self.prefix+'-'+ident+'-network'
        self.network(upstream);self.network(downstream)
        row={'id':ident,'parent':parent,'upstream':upstream,'downstream':downstream,'image':IMAGE,
             'owner_source_sha256':hashlib.sha256(owner.read_bytes()).hexdigest(),'bridge_sha256':hashlib.sha256((code/'bridge.mjs').read_bytes()).hexdigest()}
        write_json(state/'config.json',{'domain':ident,'upstream':('http://'+self.container(parent)+':19000') if parent else None})
        self.data['domains'].append(row);self.data['enabled']=True;self.save()
        self.create_domain(row)
        end=time.monotonic()+15
        while time.monotonic()<end:
            try:
                result=self.read(ident)
                if result.get('workstation') and result['ownerAlive']:return row
            except RuntimeError:pass
            time.sleep(.2)
        raise RuntimeError('new domain failed owner-workstation readback')
    def create_domain(self,row):
        ident=row['id'];name=self.container(ident);directory=self.root/ident
        self.network(row['upstream']);self.network(row['downstream'])
        self.run('create','--name',name,'--label',self.label,'--network',row['upstream'],
                 '--restart','unless-stopped','--user',f'{os.getuid()}:{os.getgid()}',
                 '--cap-drop','ALL','--security-opt','no-new-privileges','--read-only',
                 '--memory','128m','--cpus','0.5','--pids-limit','64','--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
                 '--mount',f'type=bind,src={directory / "code"},dst=/code,readonly',
                 '--mount',f'type=bind,src={directory / "state"},dst=/state',row['image'],'node','/code/bridge.mjs')
        self.run('network','connect',row['downstream'],name)
        self.run('start',name)
    def read(self,ident):
        if ident not in {r['id'] for r in self.data['domains']}:raise ValueError('unknown domain')
        script="const fs=require('fs');fetch('http://127.0.0.1:19000/state',{headers:{Authorization:'Bearer '+fs.readFileSync('/state/token','utf8').trim()},signal:AbortSignal.timeout(2000)}).then(async r=>{if(!r.ok)process.exit(1);console.log(await r.text())}).catch(()=>process.exit(1))"
        return json.loads(self.run('exec',self.container(ident),'node','-e',script))
    def resume(self):
        if not self.data['enabled']:return
        for row in self.data['domains']:
            name=self.container(row['id'])
            existing=self.run('ps','-a','--filter','name=^'+name+'$','-q')
            if not existing:
                self.create_domain(row)
            info=json.loads(self.run('inspect',name))[0]
            if info['Config']['Labels'].get('keddeh.owner-root')!=str(self.controller.root):raise ValueError('foreign container')
            if info['HostConfig']['PidsLimit']!=64:self.run('update','--pids-limit','64',name)
            code=self.root/row['id']/'code/bridge.mjs'
            desired=Path(__file__).with_name('web4_domain.mjs').read_bytes()
            changed=code.read_bytes()!=desired
            if changed:code.write_bytes(desired);row['bridge_sha256']=hashlib.sha256(desired).hexdigest();self.save()
            if not info['State']['Running']:self.run('start',name)
            elif changed:self.run('restart',name)
    def reanchor(self,ident,parent):
        from .web4_runtime import write_json
        rows={r['id']:r for r in self.data['domains']}
        if ident not in rows or parent not in rows or ident==parent:raise ValueError('invalid reanchor')
        cursor=parent
        while cursor is not None:
            if cursor==ident:raise ValueError('cyclic lineage')
            cursor=rows[cursor]['parent']
        row=rows[ident];new=rows[parent]['downstream'];name=self.container(ident)
        self.run('network','connect',new,name)
        write_json(self.root/ident/'state/config.json',{'domain':ident,'upstream':'http://'+self.container(parent)+':19000'})
        old=row['upstream'];row.update(parent=parent,upstream=new);self.save()
        self.run('network','disconnect',old,name)
        return row
    def control(self,body):
        op=body.get('operation','status')
        if op=='spawn':return self.spawn(body.get('parent'))
        if op=='reanchor':return self.reanchor(body['domain'],body['parent'])
        if op=='status':
            result=[]
            for row in self.data['domains']:
                try:live=self.read(row['id'])
                except RuntimeError:live={'status':'unavailable'}
                result.append({'topology':row,'live':live})
            return {'schema':'keddeh.dual-homed-domain-mesh.v1','domains':result,'enabled':self.data['enabled'],'scope':'independent local network namespaces and recursive bridges; same physical host'}
        raise ValueError('unsupported domain operation')
