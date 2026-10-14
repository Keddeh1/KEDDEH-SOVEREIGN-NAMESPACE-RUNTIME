"""Bind scheduler persistence to custody-pinned owner LogicalVFS; no HTTP substitute."""
import hashlib,json,sys
from pathlib import Path
class OwnerBackend:
 def __init__(self,cfg):
  self.root=Path(cfg['runtime']).resolve();b=cfg['owner_backend'];src=Path(b['source_root']).resolve()
  for name,sha in b['files'].items():
   if hashlib.sha256((src/name).read_bytes()).hexdigest()!=sha:raise ValueError('Owner package custody mismatch: '+name)
  sys.path.insert(0,str(src))
  from keddeh_namespace.logical_vfs import LogicalVFS
  self.vfs=LogicalVFS(b['vfs_root']);self.namespace=b['namespace'];self.vfs.history()
 def key(self,path):
  try:rel=Path(path).resolve().relative_to(self.root)
  except ValueError:return None
  if rel.parts[0]=='receipts' or str(rel) in ['schedule-state.json','receipt-head.json','qualified.json','canary.json']:
   return self.namespace+'/'+rel.as_posix()
 def commit(self,path,payload):
  key=self.key(path)
  if not key:return
  try:head,old=self.vfs.read(key)
  except KeyError:head={'version':0};old=None
  if old!=payload:self.vfs.write(key,payload,expected_version=head['version'])
  if self.vfs.read(key)[1]!=payload:raise ValueError('Owner VFS readback mismatch')
 def read(self,path):
  key=self.key(path)
  if not key:return None
  _,payload=self.vfs.read(key)
  if Path(path).read_bytes()!=payload:raise ValueError('Owner VFS and physical projection diverge: '+key)
  return payload
 def migrate(self):
  paths=list((self.root/'receipts').glob('*.json'))+[self.root/n for n in ['schedule-state.json','receipt-head.json','qualified.json','canary.json']]
  for p in paths:
   if p.exists():
    key=self.key(p)
    try:
     _,old=self.vfs.read(key)
     if old!=p.read_bytes():raise ValueError('Refusing conflicting owner VFS migration: '+key)
    except KeyError:self.commit(p,p.read_bytes())
  self.vfs.history()
