import json,time
from pathlib import Path
from keddeh_namespace.web4_runtime import http_json
root=Path('/workspace/deployments/owner-qzl-resident/canary-owner');cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text();q=json.loads(Path(cfg['qzl_scheduler']['config_file']).read_text());done=[]
for job in ['canary','promote']:
 request=http_json(cfg['ports']['gateway'],'/api/web4/control',{'action':'qzl','job':job},token);path=Path(q['runtime'])/'request-results'/(request['id']+'.json');end=time.monotonic()+60
 while time.monotonic()<end:
  if path.exists():break
  time.sleep(.5)
 else:raise RuntimeError('Job deadline exceeded: '+job)
 result=json.loads(path.read_text());assert result['status']=='PASS',result;done.append(result)
view=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token);assert view['qzl_scheduler']['release_ready']
Path('/workspace/work/owner-qzl-resident/canary-promotion.json').write_text(json.dumps({'status':'PASS','jobs':done,'view':view},indent=2));print('Canary and tooling promotion PASS')
