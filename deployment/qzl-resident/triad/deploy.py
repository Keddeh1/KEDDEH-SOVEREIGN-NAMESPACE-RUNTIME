import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
from keddeh_namespace.web4_runtime import http_json
base=Path(__file__).parent;rev=subprocess.check_output(['git','-C','/workspace/work/qzl-resident-git','rev-parse','HEAD'],text=True).strip()
results=[]
for role,container,owner,vfsport in [('canary','keddeh-qzl-resident-canary','/workspace/deployments/owner-qzl-resident/canary-owner',21887),('resident','keddeh-qzl-owner-resident','/workspace/deployments/owner-qzl-web4',20887)]:
 root=Path(owner);launch=root/'launch.json';cfg=json.loads(launch.read_text());app=Path(cfg['qzl_scheduler']['app_root']);conf=Path(cfg['qzl_scheduler']['config_file']);saved={launch:launch.read_bytes(),conf:conf.read_bytes(),app/'scheduler.py':(app/'scheduler.py').read_bytes()}
 backup=base/(role+'-baseline-'+str(time.time_ns()));backup.mkdir(exist_ok=False)
 for p,data in saved.items():(backup/p.name).write_bytes(data)
 assert json.loads(subprocess.check_output(['docker','inspect',container]))[0]['Config']['Labels']['keddeh.owner-root']==owner
 subprocess.run(['docker','stop',container],check=True)
 try:
  shutil.copytree(base/'deps',app/'triad-deps',dirs_exist_ok=True)
  for name in ['scheduler.py','triad_server.py','triad_mesh_pb2.py','triad_mesh_pb2_grpc.py']:
   temp=app/(name+'.new');shutil.copy2(base/name,temp);os.replace(temp,app/name);cfg['qzl_scheduler']['files'][name]=hashlib.sha256((app/name).read_bytes()).hexdigest()
  manifest=json.loads((base/'dependency-manifest.json').read_text())
  for rel,digest in manifest['files'].items():
   if hashlib.sha256((app/'triad-deps'/rel).read_bytes()).hexdigest()!=digest:raise ValueError('Dependency readback mismatch')
   cfg['qzl_scheduler']['files']['triad-deps/'+rel]=digest
  c=json.loads(conf.read_text());c['triad_grpc']={'owner_root':owner,'socket':str(root/'state/triad-grpc/triad.sock'),'dependency_path':str(app/'triad-deps'),'vfs_port':vfsport,'source_revision':rev}
  for p,data in [(launch,json.dumps(cfg,indent=2).encode()),(conf,json.dumps(c,indent=2).encode())]:
   temp=p.with_suffix('.new');temp.write_bytes(data);os.replace(temp,p)
  subprocess.run(['docker','start',container],check=True);token=(root/'state/token').read_text();end=time.monotonic()+90
  while True:
   try:
    view=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token)
    if view['healthy_nodes']==10 and view['qzl_scheduler']['healthy'] and Path(c['triad_grpc']['socket']).exists():break
   except Exception:pass
   if time.monotonic()>end:raise RuntimeError('Canary readiness timeout')
   time.sleep(1)
  subprocess.run(['python3',str(base/'verify.py'),str(conf),str(base/(role+'-qualification.json'))],check=True)
  results.append(json.loads((base/(role+'-qualification.json')).read_text()))
  (base/'deployment-evidence.json').write_text(json.dumps({'status':'PASS','rollouts':results},indent=2)+'\n')
 except BaseException:
  subprocess.run(['docker','stop',container],check=True)
  for p,data in saved.items():p.write_bytes(data)
  subprocess.run(['docker','start',container],check=True);raise
