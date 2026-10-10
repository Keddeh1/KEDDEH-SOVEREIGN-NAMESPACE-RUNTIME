"""Matched full-payload reads. No dict-vs-filesystem speedup substitution."""
import argparse,hashlib,json,pathlib,platform,statistics,tempfile,time
from continuity import ContinuityVFS
P=pathlib.Path(__file__).parent
parser=argparse.ArgumentParser();parser.add_argument('source');args=parser.parse_args();raw=pathlib.Path(args.source).read_bytes()
with tempfile.TemporaryDirectory() as td:
    p=pathlib.Path(td)/'posix-source';p.write_bytes(raw);c=ContinuityVFS(pathlib.Path(td)/'vfs');c.vfs.write('owner/state',raw,expected_version=0)
    digest=hashlib.sha256(raw).hexdigest()
    def posix():
        payload=p.read_bytes()
        if hashlib.sha256(payload).hexdigest()!=digest:raise ValueError('readback mismatch')
        return payload
    def vfs():
        r=c.observe('owner/state')
        if r.status!='AVAILABLE':raise ValueError(r.status)
        return r.payload
    values={'posix':[],'vfs':[]};n=1000
    for batch in range(5):
        for name,fn in ([('posix',posix),('vfs',vfs)] if batch%2==0 else [('vfs',vfs),('posix',posix)]):
            t=time.perf_counter_ns()
            for _ in range(n):
                if fn()!=raw:raise ValueError('payload differs')
            values[name].append((time.perf_counter_ns()-t)/n/1000)
    out={'schema':'keddeh.matched-payload-read.v1','python':platform.python_version(),'payloadBytes':len(raw),'iterationsPerBatch':n,'batches':5,'microsecondsPerRead':values,'medianMicroseconds':{k:statistics.median(v) for k,v in values.items()},'boundary':'Warm local full-payload read and SHA256 verification for both paths. VFS additionally validates retained journal metadata. Not equivalent feature costs, cold boot, power, physical unmount, kernel dentry memory or remote recovery. No universal O(1) or zero-overhead inference.'}
    (P/'benchmark-results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
