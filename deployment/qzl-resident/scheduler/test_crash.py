import tempfile,subprocess,sys,json,hashlib,os
from pathlib import Path
BASE=Path(__file__).parent
live=Path('/workspace/deployments/qzl-scheduler/config.json')
if live.exists() and '--portable' not in sys.argv:OWNER=json.loads(live.read_text())['owner_backend']
else:
 src=BASE/'owner-package/src'
 OWNER={'source_root':str(src),'files':{n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ['keddeh_namespace/logical_vfs.py','keddeh_namespace/envelope.py']}}
results=[]
for phase in ['started','prepared','receipt','head','state','owner-receipt','owner-head','owner-state']:
 root=Path(tempfile.mkdtemp(prefix='qzl-crash-',dir=BASE));(root/'old').mkdir();(root/'new').mkdir();(root/'current').symlink_to(root/'old')
 cfg={'runtime':str(root),'owner_backend':{**OWNER,'vfs_root':str(root/'vfs'),'namespace':'crash-qualification'}}
 (root/'cfg.json').write_text(json.dumps(cfg))
 script='''import scheduler as s,os
from durable_transaction import begin,prepare
from pathlib import Path
r=Path(__import__('sys').argv[1]);phase=__import__('sys').argv[2]
s.bind_owner(s.read(r/'cfg.json'))
s.seal(r/'schedule-state.json',s.encode({}))
tx=begin(r,'promote','queue-realcrash',s.seal,s.encode)
s.switch(r,'current',r/'new')
if phase=='started':os._exit(91)
payload=s.encode({'status':'PASS','job':'promote','slot':'queue-realcrash','previous_sha256':None})
sha=s.hashlib.sha256(payload).hexdigest()
writes=[(r/'receipts'/ (tx['id']+'.json'),payload),(r/'receipt-head.json',s.encode({'sha256':sha})),(r/'schedule-state.json',s.encode({'queue-realcrash':{'status':'PASS','slot':'queue-realcrash','receipt_sha256':sha}}))]
prepare(r,tx,writes,s.seal,s.encode)
if phase=='prepared':os._exit(91)
for (path,data),name in zip(writes,['receipt','head','state']):
 if phase=='owner-'+name:s._owner_backend.commit(path,data);os._exit(91)
 s.seal(path,data)
 if phase==name:os._exit(91)
'''
 p=subprocess.run([sys.executable,'-c',script,str(root),phase],cwd=BASE);assert p.returncode==91
 subprocess.run([sys.executable,'-c',"import scheduler as s;from pathlib import Path;r=Path(__import__('sys').argv[1]);s.bind_owner(s.read(r/'cfg.json'));s.recover(r,s.seal,s.encode,s.read,s.switch)",str(root)],cwd=BASE,check=True)
 state=json.loads((root/'schedule-state.json').read_text());assert not (root/'transaction.json').exists()
 if phase=='started':assert state['queue-realcrash']['status']=='FAIL' and (root/'current').resolve()==root/'old'
 else:
  assert state['queue-realcrash']['status']=='PASS' and (root/'current').resolve()==root/'new'
  receipt=list((root/'receipts').glob('*.json'));assert len(receipt)==1
  assert hashlib.sha256(receipt[0].read_bytes()).hexdigest()==json.loads((root/'receipt-head.json').read_text())['sha256']
 results.append({'crash_boundary':phase,'status':'PASS'})
(BASE/'crash-qualification.json').write_text(json.dumps({'status':'PASS','real_subprocess_abrupt_exits':results},indent=2)+'\n');print(json.dumps(results))
