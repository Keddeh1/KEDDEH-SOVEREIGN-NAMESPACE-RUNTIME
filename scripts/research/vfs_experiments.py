#!/usr/bin/env python3
"""Isolated VFS capacity and integrity experiments; never mutate the live store."""
from pathlib import Path
import argparse,json,statistics,sys,tempfile,time,tracemalloc,hashlib,subprocess,types
sys.path.insert(0,'/workspace/Keddeh-SYSTEMS-Virtual-File-Space-ZCG-ARCHITECTURE')
baseline_ref='63489b3eee86ae2f19e9b8ba191147a5c77879f1'
baseline_source=subprocess.check_output(['git','show',baseline_ref+':vfs_server/store.py'],cwd='/workspace/Keddeh-SYSTEMS-Virtual-File-Space-ZCG-ARCHITECTURE')
baseline=types.ModuleType('vfs_server.research_baseline');baseline.__package__='vfs_server'
exec(compile(baseline_source,'qualified-pre-snapshot/vfs_server/store.py','exec'),baseline.__dict__)
VFSStore=baseline.VFSStore
from vfs_server.model import ArtifactWrite
ap=argparse.ArgumentParser();ap.add_argument('--output',default='/workspace/braink-setup/research-100');ap.add_argument('--sources',default='/workspace/braink-setup/research-100');a=ap.parse_args()
out=Path(a.output).resolve();sources=Path(a.sources).resolve();out.mkdir(parents=True,exist_ok=True)
if any((out/f'step-{n:03d}.json').exists() for n in range(11,18)):ap.error('Existing experiment evidence is immutable; select a new --output directory for the next iteration')
def save(n,result):
 (out/f'step-{n:03d}.json').write_text(json.dumps({'step':n,'status':'passed','result':result},indent=2)+'\n');print('Step',n,'passed',flush=True)
for n,p in [(11,'cpython'),(12,'sqlite')]:
 metadata=json.loads((sources/(p+'-source.json')).read_text());source=sources/('cpython-sqlite3.rst' if p=='cpython' else 'sqlite-wal.c');assert hashlib.sha256(source.read_bytes()).hexdigest()==metadata['sha256'];save(n,metadata)
save(13,{'finding':'events() fully verifies receipts on one connection, then queries delivery rows on another connection; concurrent writes can enter delivery after the verified snapshot','primary_source_lines':{'sqlite_wal_reader_snapshot':[110,116],'cpython_explicit_transactions':[2686,2693]},'hypothesis':'a single explicit read transaction binds integrity verification and returned events to one WAL snapshot','scale_constraint':'full historical verification remains O(history); this fix does not claim bounded history cost'})
measurements=[]
for count in (100,1000,10000):
 with tempfile.TemporaryDirectory(prefix='keddeh-vfs-benchmark-',dir='/tmp') as root:
  store=VFSStore(root)
  with store._connect() as db:
   db.execute('BEGIN IMMEDIATE')
   for i in range(count):store._receipt(db,'BENCHMARK','SYNTHETIC',None,'/benchmark',{'index':i})
   db.execute('COMMIT')
  times=[];tracemalloc.start()
  for _ in range(5):
   start=time.perf_counter();reply=store.events(after=max(0,count-100),limit=100);times.append(time.perf_counter()-start);assert len(reply['events'])==100 and reply['next_cursor']==count
  _,peak=tracemalloc.get_traced_memory();tracemalloc.stop();measurements.append({'receipts':count,'returned_events':100,'median_seconds':statistics.median(times),'min_seconds':min(times),'max_seconds':max(times),'python_peak_traced_bytes':peak})
save(14,{'measurements':measurements,'repeats':5,'scope':'single-host synthetic receipt history, warm OS cache, tracemalloc overhead included; not production throughput or total RSS','conclusion':'returned window is bounded at 100; full verification work and allocation grow with retained history'})
with tempfile.TemporaryDirectory(prefix='keddeh-vfs-tamper-',dir='/tmp') as root:
 store=VFSStore(root);store.write(ArtifactWrite('/test/a',b'a','research'));store.write(ArtifactWrite('/test/b',b'b','research'))
 with store._connect() as db:db.execute("UPDATE receipts SET status='CORRUPTED' WHERE seq=1")
 assert not store.verify_receipt_chain()['verified']
 try:store.events(after=1);raise AssertionError('historical corruption accepted')
 except ValueError as e:assert str(e)=='invalid_receipt_chain'
save(15,{'old_receipt_mutation_rejected':True,'delivery_after_corrupted_prefix_rejected':True,'live_store_modified':False})
with tempfile.TemporaryDirectory(prefix='keddeh-vfs-cursor-',dir='/tmp') as root:
 store=VFSStore(root);store.write(ArtifactWrite('/packages/a',b'a','research'));rejections=0
 for after,limit in [(-1,100),(True,100),(0,0),(0,1001),(0,True),('0',100)]:
  try:store.events(after,limit);raise AssertionError('invalid event cursor accepted')
  except ValueError:rejections+=1
 store.subscribe('research','/packages',1)
 for prefix,cursor in [('/packages',0),('/packages',2),('/changed',1),('/packages',True)]:
  try:store.subscribe('research',prefix,cursor);raise AssertionError('invalid subscription transition accepted')
  except ValueError:rejections+=1
 assert VFSStore(root).subscription('research')['cursor']==1
save(16,{'invalid_boundaries_rejected':rejections,'durable_cursor_after_restart':1})
with tempfile.TemporaryDirectory(prefix='keddeh-vfs-race-',dir='/tmp') as root:
 store=VFSStore(root);store.write(ArtifactWrite('/before',b'before','research'));original=store.verify_receipt_chain
 def check_then_write():
  verified=original();assert verified['verified']
  with store._connect() as db:
   db.execute('BEGIN IMMEDIATE');store._receipt(db,'CONCURRENT','COMMITTED',None,'/after',{'test':'race'});db.execute("UPDATE receipts SET status='CORRUPTED' WHERE seq=2");db.execute('COMMIT')
  return verified
 store.verify_receipt_chain=check_then_write
 reply=store.events();assert len(reply['events'])==2 and reply['events'][-1]['status']=='CORRUPTED'
save(17,{'old_implementation_delivered_unverified_concurrent_row':True,'delivered_events':2,'scope':'isolated deterministic concurrent-connection reproduction; no live receipt or artifact changed'})
