"""Authenticated local gRPC observation of the existing owner runtime, no mutation."""
import base64,hashlib,hmac,json,math,os,time,urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import grpc,triad_mesh_pb2 as pb,triad_mesh_pb2_grpc as rpc
class Service(rpc.TriadMeshOrchestratorServicer):
 def __init__(self,cfg):
  self.root=Path(cfg['owner_root']);self.launch=json.loads((self.root/'launch.json').read_text());self.token=(self.root/'state/token').read_text().strip();self.cfg=cfg
 def get(self,port,path):
  req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,headers={'Authorization':'Bearer '+self.token})
  with urllib.request.urlopen(req,timeout=3) as r:return json.load(r)
 def TraversalMatrixHop(self,request,context):
  auth=dict(context.invocation_metadata()).get('authorization','')
  if not hmac.compare_digest(auth,'Bearer '+self.token):context.abort(grpc.StatusCode.UNAUTHENTICATED,'Bearer authentication required')
  if not request.raw_word_input or len(request.raw_word_input.encode())>4096 or not math.isfinite(request.current_load_factor) or request.current_load_factor<0:context.abort(grpc.StatusCode.INVALID_ARGUMENT,'Invalid input boundary')
  revision=self.cfg['source_revision']
  if request.target_git_revision!=revision:context.abort(grpc.StatusCode.FAILED_PRECONDITION,'Source revision mismatch')
  try:
   view=self.get(self.launch['ports']['gateway'],'/api/web4/status')
   sub=json.loads((self.root/'state/vfs-subscription/subscription.json').read_text());digest=sub['published_digest']
   artifact=self.get(self.cfg['vfs_port'],'/artifacts/'+digest);raw=base64.b64decode(artifact['content_b64'],validate=True)
   actor=sub['actor_receipt'];observer=sub['observer_receipt']
   verified=hashlib.sha256(raw).hexdigest()==digest and actor['artifact_digest']==digest and observer['artifact_digest']==digest and observer['detail']['observed_digest']==digest and observer['status']=='VISIBLE'
   operational=view['healthy_nodes']==10 and view['qzl_scheduler']['healthy'] and verified
   return pb.TriadMatrixHopResponse(status=pb.MATRIX_STATUS_VERIFIED_OPERATIONAL if operational else pb.MATRIX_STATUS_PENDING,concept=pb.ConceptTier(word_processed=request.raw_word_input,assigned_node_id=self.launch['family'],vfs_mount_path=actor['path']),execution=pb.ExecutionTier(il_llm_state='NOT_EXECUTED',braink_verdict='OBSERVATION_ONLY'),integration=pb.IntegrationTier(sdk_commit_verified=False,provenance=pb.ResearchProvenance(source_git_revision=revision)),timestamp_epoch_ns=time.time_ns(),vfs_readback_verified=verified,observed_digest_sha256=digest,scope='Local bearer-authenticated UDS observation; no SDK mutation, KEX allocation, measured saturation or regional deployment')
  except Exception:
   context.abort(grpc.StatusCode.UNAVAILABLE,'Runtime or readback unavailable; no verified success')
 def StreamMatrixTelemetry(self,request,context):
  for _ in range(20):
   if not context.is_active():return
   yield self.TraversalMatrixHop(request,context)
   time.sleep(.5)
def start(cfg):
 socket=Path(cfg['socket']);socket.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 if socket.exists():socket.unlink()
 server=grpc.server(ThreadPoolExecutor(max_workers=4),maximum_concurrent_rpcs=8,options=[('grpc.max_receive_message_length',8192),('grpc.max_send_message_length',65536)])
 rpc.add_TriadMeshOrchestratorServicer_to_server(Service(cfg),server)
 if not server.add_insecure_port('unix:'+str(socket)):raise RuntimeError('UDS binding failed')
 server.start();os.chmod(socket,0o600)
 meta={'transport':'gRPC over secured local UDS','socket':str(socket),'authentication':'local bearer token; not OAuth or mTLS','source_revision':cfg['source_revision'],'pid':os.getpid()}
 from scheduler import seal,encode
 seal(socket.parent/'triad-daemon.json',encode(meta));return server
