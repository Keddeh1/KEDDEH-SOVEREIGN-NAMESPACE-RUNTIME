"""Write-ahead recovery for release pointers and prepared receipt publication."""
import os,json,uuid
from pathlib import Path

def flush_dir(root):
 fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def recover(root,seal,encode,read,switch):
 pending=root/'transaction.json'
 if not pending.exists():return
 tx=json.loads(pending.read_bytes())
 if tx['phase']=='PREPARED':
  # Redo is byte-identical: safe after any interrupted projection/head write.
  for rel,payload in tx['writes']:
   seal(root/rel,payload.encode())
 else:
  # No prepared receipt: restore release pointers before admitting other work.
  for name,target in tx['pointers'].items():
   path=root/name
   if target is None:
    if path.is_symlink():path.unlink();flush_dir(root)
   else:switch(root,name,Path(target))
  state=read(root/'schedule-state.json') if (root/'schedule-state.json').exists() else {}
  entry={'slot':tx['slot'],'status':'FAIL','error':'INTERRUPTED_BEFORE_COMMIT','transaction':tx['id']}
  state[tx['slot'] if tx['slot'].startswith('queue-') else tx['job']]=entry
  seal(root/'schedule-state.json',encode(state))
  seal(root/'transaction-incidents'/(tx['id']+'.json'),encode({**tx,'status':'ROLLED_BACK_INTERRUPTED'}))
 pending.unlink();flush_dir(root)

def begin(root,job,slot,seal,encode):
 tx={'id':uuid.uuid4().hex,'phase':'STARTED','job':job,'slot':slot,'pointers':{n:str((root/n).resolve(strict=True)) if (root/n).is_symlink() else None for n in ['current','previous','canary']}}
 seal(root/'transaction.json',encode(tx));return tx

def prepare(root,tx,writes,seal,encode):
 tx.update(phase='PREPARED',writes=[(str(path.relative_to(root)),payload.decode()) for path,payload in writes]);seal(root/'transaction.json',encode(tx))
