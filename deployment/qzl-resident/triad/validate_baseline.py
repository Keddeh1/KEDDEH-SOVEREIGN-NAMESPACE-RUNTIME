"""Read-only staging gate; unsupported or falsified budgets never pass."""
import json,sys,math,re
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text());samples=r['latency_ns']
assert re.fullmatch('[0-9a-f]{40}',r['source_revision'])
assert r['workload']['calls']==len(samples)==100
assert all(type(n)is int and n>0 for n in samples)
assert abs(max(samples)/1e6-r['max_ms'])<1e-9
passed=all(n<=15000000 for n in samples)
print(json.dumps({'status':'PASS' if passed else 'FALSIFIED','budget_ms':15,'exceedances':sum(n>15000000 for n in samples),'max_ms':max(samples)/1e6,'production_mutation':False}))
raise SystemExit(0 if passed else 1)
