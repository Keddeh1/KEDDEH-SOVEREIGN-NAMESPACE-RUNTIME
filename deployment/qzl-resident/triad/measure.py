import json,sys,time,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'deps'))
import grpc,triad_mesh_pb2 as pb,triad_mesh_pb2_grpc as rpc
cfg=json.loads(Path('/workspace/deployments/qzl-scheduler/config.json').read_text())['triad_grpc'];token=(Path(cfg['owner_root'])/'state/token').read_text().strip();samples=[]
with grpc.insecure_channel('unix:'+cfg['socket']) as channel:
 grpc.channel_ready_future(channel).result(timeout=10);client=rpc.TriadMeshOrchestratorStub(channel)
 for i in range(100):
  start=time.perf_counter_ns();result=client.TraversalMatrixHop(pb.TriadMatrixHopRequest(raw_word_input='Empirical observation '+str(i),target_git_revision=cfg['source_revision']),metadata=[('authorization','Bearer '+token)],timeout=10);elapsed=time.perf_counter_ns()-start
  if result.status!=pb.MATRIX_STATUS_VERIFIED_OPERATIONAL or not result.vfs_readback_verified:raise RuntimeError('Observed invariant failure')
  samples.append(elapsed)
sorted_ns=sorted(samples);r={'status':'MEASURED','source_revision':cfg['source_revision'],'workload':{'calls':100,'concurrency':1,'transport':'local gRPC UDS plus live authenticated gateway and VFS HTTP readback','timer':'perf_counter_ns','warmup':'channel ready; no requests excluded'},'latency_ns':samples,'p50_ms':statistics.median(samples)/1e6,'p99_ms':sorted_ns[98]/1e6,'max_ms':max(samples)/1e6,'15ms_each_call_contract_pass':all(n<=15000000 for n in samples),'throughput_capacity':'NOT_ESTABLISHED: serial latency observations do not establish maximum concurrent throughput','production_gate_changed':False,'falsification':'Any call over 15ms falsifies the proposed every-call 15ms budget for this measured workload'}
Path('/workspace/work/triad-grpc/latency-baseline.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='latency_ns'}))
