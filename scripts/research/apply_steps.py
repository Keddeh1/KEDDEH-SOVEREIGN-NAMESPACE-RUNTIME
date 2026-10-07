#!/usr/bin/env python3
"""Bind completed research results to owner VFS and R36 execution/readback."""
from pathlib import Path
import argparse,base64,hashlib,json,subprocess,sys,time,urllib.request
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from keddeh_namespace.web4_runtime import write_json
ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=20);a=ap.parse_args()
if not 1<=a.start<=a.end<=100:ap.error('require 1 <= start <= end <= 100')
count=a.end-a.start+1
base=Path('/workspace');engine=Path(__file__).resolve().parents[2];out=base/'braink-setup/research-100';root=base/'braink-setup/web4-runtime';cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text();v=cfg['vfs'];vtoken=Path(v['token_file']).read_text().strip();proof=[];requests=[]
progress=out/f'application-{a.start:03d}-{a.end:03d}.json'
if progress.exists():
    prior=json.loads(progress.read_text())
    if all(item.get('journal_observer_signature_verified') for item in prior['steps']) and len(prior['steps'])==count:
        for item in prior['steps']:
            if hashlib.sha256((out/f"step-{item['step']:03d}.json").read_bytes()).hexdigest()!=item['result_sha256']:
                raise SystemExit('Completed result changed; record a new iteration rather than overwrite its evidence')
        print('This batch already has complete actor/readback evidence; no duplicate execution');sys.exit(0)
def request(url,body=None,token=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers=headers)
 with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
for step in range(a.start,a.end+1):
 p=out/f'step-{step:03d}.json';result=json.loads(p.read_text());assert result['step']==step and result['status']=='passed';raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest();logical=f'/packages/web4/research/PLAN-100/step-{step:03d}.json'
 admitted=request(v['endpoint']+'/artifacts',{'path':logical,'content_b64':base64.b64encode(raw).decode(),'source':'Keddeh1/RND-PLAN-100','media_type':'application/json'},vtoken)
 readback=request(v['endpoint']+'/artifacts/'+digest,token=vtoken);assert base64.b64decode(readback['content_b64'])==raw
 observed=request(v['endpoint']+'/verify',{'digest':digest},vtoken);assert observed['verified']
 nonce=int.from_bytes(bytes.fromhex(digest)[:4],'little');node=(step-1)%10+1;tenant='WEB4_RND_PLAN_100'
 returned=request('http://127.0.0.1:'+str(cfg['ports']['gateway'])+'/api/web4/control',{'action':'commit','node_id':node,'nonce':nonce,'tenant_id':tenant},token);actor=returned['actor'];assert actor['status']=='ACTOR_COMMITTED'
 requests.append({'producer':'WEB4_RND_PLAN_100','transaction_id':f'plan100.step{step:03d}','correlation_id':actor['correlation_id'],'tenant_id':tenant,'node_id':node,'execution_vector':nonce,'receipt_hash':actor['receipt_hash'],'actor_identity':'WEB4_HTTP_ACTOR'})
 proof.append({'step':step,'result_sha256':digest,'vfs_path':logical,'vfs_actor_receipt_digest':admitted['actor_receipt']['receipt_digest'],'vfs_observer_receipt_digest':observed['receipt']['receipt_digest'],'byte_readback_verified':True,'owner_runtime_actor_status':actor['status'],'node_id':node,'nonce':nonce,'receipt_hash':actor['receipt_hash'],'journal_observer_status':'pending'})
 write_json(progress,{'scope':'distinct local actor/readback roles under owner authority; independent assessment unset','steps':proof});print('Step',step,'VFS and owner actuator returned',flush=True)
requests_path=out/f'plan-transaction-requests-{a.start:03d}-{a.end:03d}.jsonl';requests_path.write_text(''.join(json.dumps(r)+'\n' for r in requests));ledger=out/f'plan-transaction-observer-{a.start:03d}-{a.end:03d}.jsonl';verifier=Path(cfg['packages']['network'])/'braink-chatgpt-plugin/server/detached_journal_verifier.py'
run=subprocess.run([sys.executable,str(verifier),'--requests',str(requests_path),'--journal',str(root/'state/http-journal.bin'),'--ledger',str(ledger),'--key',str(root/'state/local-verifier.pem')],capture_output=True,text=True);(out/'detached-observer.log').write_text(run.stdout+run.stderr);assert run.returncode==0
records={record['transaction_id']:record for record in (json.loads(line) for line in ledger.read_text().splitlines())}
assert set(records)=={r['transaction_id'] for r in requests}
for expected,item in zip(requests,proof):
 record=records[expected['transaction_id']]
 assert record['receipt_hash']==item['receipt_hash']
 assert record['tx_id']==hashlib.sha256(f"{expected['tenant_id']}|{expected['node_id']}|{expected['execution_vector']}".encode()).hexdigest()
 assert record['verification_result']=='VERIFIED';signature=record.pop('signature');Ed25519PublicKey.from_public_bytes(base64.b64decode(signature['public_key_b64'])).verify(base64.b64decode(signature['value_b64']),json.dumps(record,sort_keys=True,separators=(',',':')).encode());item['journal_observer_status']='VERIFIED';item['journal_observer_signature_verified']=True
# Every repository subscriber must actually mirror the new research result bytes.
end=time.monotonic()+90
while True:
 mirrors=[]
 for f in sorted(base.glob('*/.keddeh/family.json')):
  m=json.loads(f.read_text());sroot=Path(m['runtime_root'])/'state/vfs-subscription';state=json.loads((sroot/'subscription.json').read_text());mirrored=0
  for item in proof:
   if state['objects'].get(item['vfs_path'])==item['result_sha256']:
    obj=sroot/'mirror/objects'/item['result_sha256']
    if obj.exists() and hashlib.sha256(obj.read_bytes()).hexdigest()==item['result_sha256']:mirrored+=1
  mirrors.append({'repository':m['repository'],'mirrored_step_results':mirrored,'cursor':state['cursor']})
 if all(row['mirrored_step_results']==count for row in mirrors):break
 if time.monotonic()>end:raise RuntimeError('not every subscriber mirrored all research results; retain progress')
 time.sleep(1)
write_json(progress,{'scope':'distinct local actor/readback roles under owner authority; independent external assessment unset','steps':proof,'family_mirrors':mirrors})
plan_path=engine/'docs/research/PLAN_100.json';plan=json.loads(plan_path.read_text())
for step,item in zip(plan['steps'][a.start-1:a.end],proof):step.update(status='completed',evidence=[{'result':'evidence/step-'+str(step['id']).zfill(3)+'.json','sha256':item['result_sha256'],'application':'evidence/APPLICATION.json'}])
plan['next_step']=next((step['id'] for step in plan['steps'] if step['status']!='completed'),None);write_json(plan_path,plan);print(str(count)+' steps completed with VFS readback, signed detached journal verification and nine mirrored research feeds')
