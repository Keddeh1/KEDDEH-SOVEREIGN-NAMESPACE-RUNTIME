"""Owner-pinned Ed25519 slot verification; software gate, not firmware secure boot."""
import base64,hashlib,json,os,pathlib,tempfile,fcntl
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
DOMAIN=b'keddeh.slot-manifest.v1\0'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def files(root):
 root=pathlib.Path(root)
 if root.is_symlink()or not root.is_dir():raise ValueError('Slot must be a real directory')
 result={}
 for p in root.rglob('*'):
  if p.is_symlink():raise ValueError('Symlink rejected')
  if p.is_file():result[p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  elif not p.is_dir():raise ValueError('Special file rejected')
 if not result:raise ValueError('Empty slot rejected')
 return result

def make_manifest(root,slot,version,entrypoint,key):
 if slot not in ['A','B']or type(version)is not int or version<1:raise ValueError('Invalid slot/version')
 payload={'schema':'keddeh.slot-manifest.v1','slot':slot,'version':version,'entrypoint':entrypoint,'files':files(root)}
 if entrypoint not in payload['files']:raise ValueError('Entrypoint not included')
 return {'payload':payload,'signature':base64.b64encode(key.sign(DOMAIN+canonical(payload))).decode()}

def verify(root,signed,public_key,minimum_version=1,expected_slot=None):
 if set(signed)!= {'payload','signature'}:raise ValueError('Invalid signed fields')
 v=signed['payload']
 if set(v)!= {'schema','slot','version','entrypoint','files'}or v['schema']!='keddeh.slot-manifest.v1':raise ValueError('Invalid manifest')
 if v['slot']not in ['A','B']or (expected_slot and v['slot']!=expected_slot)or type(v['version'])is not int or v['version']<minimum_version:raise ValueError('Slot or rollback policy rejected')
 if v['entrypoint']not in v['files']:raise ValueError('Missing entrypoint')
 Ed25519PublicKey.from_public_bytes(public_key).verify(base64.b64decode(signed['signature'],validate=True),DOMAIN+canonical(v))
 if files(root)!=v['files']:raise ValueError('Slot content differs from authenticated manifest')
 return {'state':'verified','slot':v['slot'],'version':v['version'],'manifestSha256':hashlib.sha256(canonical(v)).hexdigest(),'entrypoint':v['entrypoint']}

def ledger(path,event):
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a+b')as f:
  fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);previous='0'*64;sequence=0
  for line in f:
   record=json.loads(line);body={k:record[k]for k in ['sequence','previous','event']}
   if record['sequence']!=sequence+1 or record['previous']!=previous or hashlib.sha256(canonical(body)).hexdigest()!=record['sha256']:raise ValueError('Ledger history corrupted')
   sequence=record['sequence'];previous=record['sha256']
  body={'sequence':sequence+1,'previous':previous,'event':event};record={**body,'sha256':hashlib.sha256(canonical(body)).hexdigest()};f.seek(0,2);f.write(canonical(record)+b'\n');f.flush();os.fsync(f.fileno());return record

def activate(root,signed,public_key,state_path,expected_slot):
 state_path=pathlib.Path(state_path);state_path.parent.mkdir(parents=True,exist_ok=True)
 with state_path.with_suffix('.lock').open('a+b')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);old=json.loads(state_path.read_text())if state_path.exists()else {'minimumVersion':1}
  observation=verify(root,signed,public_key,old['minimumVersion'],expected_slot)
  # Prepared record precedes activation. An interrupted transaction stays inspectable.
  ledger(state_path.with_suffix('.ledger.jsonl'),{'kind':'activation-prepared','observation':observation})
  value={**observation,'minimumVersion':max(old['minimumVersion'],observation['version']),'boundary':'Software activation record; verify the slot again immediately before execution. Not firmware-secure boot or a substitute for protected key/state custody.'}
  fd,name=tempfile.mkstemp(prefix='.boot-state-',dir=state_path.parent)
  try:
   with os.fdopen(fd,'wb')as f:f.write(canonical(value));f.flush();os.fsync(f.fileno())
   os.replace(name,state_path);directory=os.open(state_path.parent,os.O_RDONLY);os.fsync(directory);os.close(directory)
  finally:
   if os.path.exists(name):os.unlink(name)
  ledger(state_path.with_suffix('.ledger.jsonl'),{'kind':'activation-observed','stateSha256':hashlib.sha256(state_path.read_bytes()).hexdigest(),'observation':observation});return value
