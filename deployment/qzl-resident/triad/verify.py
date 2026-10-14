import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'deps'))
import grpc,triad_mesh_pb2 as pb,triad_mesh_pb2_grpc as rpc
cfg=json.loads(Path(sys.argv[1]).read_text())['triad_grpc'];token=(Path(cfg['owner_root'])/'state/token').read_text().strip();meta=[('authorization','Bearer '+token)]
with grpc.insecure_channel('unix:'+cfg['socket']) as channel:
 grpc.channel_ready_future(channel).result(timeout=15);client=rpc.TriadMeshOrchestratorStub(channel)
 request=pb.TriadMatrixHopRequest(raw_word_input='Observe actual runtime state without truncation.',target_git_revision=cfg['source_revision'])
 result=client.TraversalMatrixHop(request,metadata=meta,timeout=10)
 assert result.status==pb.MATRIX_STATUS_VERIFIED_OPERATIONAL and result.vfs_readback_verified and not result.integration.sdk_commit_verified and not result.execution.HasField('kex_memory_allocation_offset') and not result.integration.provenance.HasField('empirical_saturation_ratio')
 assert result.concept.word_processed==request.raw_word_input
 for req,auth,expected in [(request,[],grpc.StatusCode.UNAUTHENTICATED),(pb.TriadMatrixHopRequest(raw_word_input='x',target_git_revision='0'*40),meta,grpc.StatusCode.FAILED_PRECONDITION),(pb.TriadMatrixHopRequest(raw_word_input='x',target_git_revision=cfg['source_revision'],current_load_factor=float('nan')),meta,grpc.StatusCode.INVALID_ARGUMENT)]:
  try:client.TraversalMatrixHop(req,metadata=auth,timeout=5)
  except grpc.RpcError as e:assert e.code()==expected
  else:raise AssertionError('Invalid admission')
 stream=client.StreamMatrixTelemetry(request,metadata=meta,timeout=5);assert next(stream).vfs_readback_verified;assert next(stream).vfs_readback_verified;stream.cancel()
 report={'status':'PASS','socket':cfg['socket'],'source_revision':cfg['source_revision'],'readback_digest':result.observed_digest_sha256,'gates':['actual protobuf and gRPC UDS request','observed runtime and VFS digest verified','unauthenticated rejected','revision mismatch rejected','NaN load rejected','bounded cancellable stream','no invented SDK commit or KEX allocation or saturation']}
 Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
