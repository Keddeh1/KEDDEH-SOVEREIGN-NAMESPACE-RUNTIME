import base64,hashlib,json,os,time,urllib.error,urllib.request
from pathlib import Path
from keddeh_namespace.web4_runtime import http_json
root=Path('/workspace/deployments/owner-qzl-resident/canary-owner');cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text();port=cfg['ports']['gateway']
view=http_json(port,'/api/web4/status',token=token);assert view['healthy_nodes']==10 and view['qzl_scheduler']['healthy']
try:http_json(port,'/api/web4/control',{'action':'qzl','job':'qualification'},'invalid')
except urllib.error.HTTPError as e:assert e.code==401
else:raise AssertionError('Unauthenticated request admitted')
request=http_json(port,'/api/web4/control',{'action':'qzl','job':'qualification'},token);assert request['status']=='QUEUED' and not request['executed']
resultfile=Path('/workspace/deployments/owner-qzl-resident/canary-qzl/state/request-results')/(request['id']+'.json');end=time.monotonic()+120
while time.monotonic()<end:
 if resultfile.exists():break
 time.sleep(.5)
else:raise AssertionError('Owner queue execution timed out')
result=json.loads(resultfile.read_text());assert result['status']=='PASS' and result['slot']=='queue-'+request['id']
end=time.monotonic()+25
while time.monotonic()<end:
 sub=json.loads((root/'state/vfs-subscription/subscription.json').read_text())
 if sub['status']=='subscribed':
  digest=sub['published_digest'];req=urllib.request.Request(cfg['vfs']['endpoint']+'/artifacts/'+digest,headers={'Authorization':'Bearer '+token})
  with urllib.request.urlopen(req,timeout=5) as response:artifact=json.load(response)
  raw=base64.b64decode(artifact['content_b64']);assert hashlib.sha256(raw).hexdigest()==digest;data=json.loads(raw)
  if data.get('qzl_scheduler',{}).get('healthy') and data['qzl_scheduler']['jobs'].get('manual:qualification',{}).get('slot')==result['slot']:break
 time.sleep(.5)
else:raise AssertionError('Owner VFS published readback did not include execution')
status=http_json(port,'/api/web4/control',{'action':'qzl'},token);assert status['healthy']
report={'schema':'keddeh.qzl.owner-integration.v1','status':'PASS','ten_owner_packages':len(cfg['packages']),'healthy_workstations':view['healthy_nodes'],'controller_pid':json.loads((root/'controller.json').read_text())['pid'],'owner_gateway':port,'owner_service':status,'unauthenticated_mutation':'REJECTED_HTTP_401','queued_request':request,'executed_receipt':result,'vfs_publication':{'digest':digest,'actor':sub['actor_receipt'],'observer':sub['observer_receipt'],'cursor':sub['cursor'],'exact_readback':True},'scope':'Current workspace host; supplied WEB4 packages, authenticated gateway and VFS hub; no claim of external ServerSpace host or FPGA deployment'}
Path('/workspace/work/owner-qzl-resident/canary-qualification.json').write_text(json.dumps(report,indent=2));print(json.dumps({'status':'PASS','healthy_workstations':view['healthy_nodes'],'queued_request':request['id'],'vfs_digest':digest}))
