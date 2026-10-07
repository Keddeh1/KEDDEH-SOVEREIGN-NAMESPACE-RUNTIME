"""Durable family subscription to the owner's VFS_SERVER artifact graph."""
import base64
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

class VFSSubscription:
    def __init__(self,controller):
        self.controller=controller;self.config=controller.config.get('vfs');self.due=0
        self.root=controller.state/'vfs-subscription';self.root.mkdir(exist_ok=True)
        self.path=self.root/'subscription.json'
        self.state=json.loads(self.path.read_text()) if self.path.exists() else {'cursor':0,'objects':{},'status':'unconfigured'}
    def request(self,path,body=None):
        endpoint=self.config['endpoint'];parsed=urllib.parse.urlsplit(endpoint)
        if parsed.scheme!='http' or parsed.hostname!='127.0.0.1':raise ValueError('this binding requires the local owner VFS endpoint')
        token=Path(self.config['token_file']).read_text().strip()
        raw=None if body is None else json.dumps(body).encode()
        req=urllib.request.Request(endpoint+path,data=raw,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=15) as reply:return json.loads(reply.read(70*1024*1024+1))
    def save(self):
        from .web4_runtime import write_json
        write_json(self.path,self.state)
    def tick(self):
        if not self.config or time.monotonic()<self.due:return
        self.due=time.monotonic()+10
        try:
            prefix='/packages/web4';subscriber=self.controller.config['family_id']
            self.request('/subscriptions',{'subscriber':subscriber,'prefix':prefix,'cursor':self.state['cursor']})
            events=self.request('/events?'+urllib.parse.urlencode({'after':self.state['cursor'],'limit':100}))
            for event in events['events']:
                path=event.get('path') or '';digest=event.get('artifact_digest')
                if event['kind']=='VFS_ARTIFACT_WRITE' and path.startswith(prefix+'/'):
                    if self.state['objects'].get(path)!=digest:
                        observed=self.request('/artifacts/'+digest)
                        raw=base64.b64decode(observed['content_b64'],validate=True)
                        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('VFS subscription artifact readback mismatch')
                        from .logical_vfs import LogicalVFS
                        local=LogicalVFS(self.root/'mirror');local.put_object(raw)
                        self.state['objects'][path]=digest
                        self.save()
                self.state['cursor']=event['seq'];self.save()
            self.request('/subscriptions',{'subscriber':subscriber,'prefix':prefix,'cursor':self.state['cursor']})
            # Publish family execution readback under a repository-scoped path.
            view=self.controller.status()
            view.update(bilateral_cycle=self.controller.bilateral.data['cycle'],domain_count=len(self.controller.domains.data['domains']),source_digest=self.controller.source_digest)
            raw=json.dumps(view,sort_keys=True).encode();path='/families/'+subscriber+'/readback.json'
            previous=self.state.get('published_digest');digest=hashlib.sha256(raw).hexdigest()
            if digest!=previous:
                request={'path':path,'content_b64':base64.b64encode(raw).decode(),'source':self.controller.config['repository'],'media_type':'application/json'}
                if previous:request['predecessor']=previous
                actor=self.request('/artifacts',request)
                readback=self.request('/artifacts/'+digest)
                if base64.b64decode(readback['content_b64'])!=raw:raise ValueError('family VFS mirror readback differs')
                observer=self.request('/verify',{'digest':digest})
                if not observer['verified']:raise ValueError('VFS observer rejected readback')
                self.state.update(published_digest=digest,actor_receipt=actor['actor_receipt'],observer_receipt=observer['receipt'])
            self.state.update(status='subscribed',error=None,source_repository=self.controller.config['repository'])
            self.save()
        except Exception as exc:
            self.state.update(status='retrying',error=type(exc).__name__+': '+str(exc));self.save()
