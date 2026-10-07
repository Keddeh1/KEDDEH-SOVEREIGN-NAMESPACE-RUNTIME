import json,subprocess,time
from pathlib import Path
from keddeh_namespace.web4_runtime import http_json
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--root',default='/workspace/braink-setup/web4-runtime');ap.add_argument('--output',required=True);args=ap.parse_args()
root=Path(args.root);cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text()
def call(**body):return http_json(cfg['ports']['gateway'],'/api/web4/control',dict(action='domains',**body),token)
status=call()
for i in range(len(status['domains']),3):
    print(call(operation='spawn',parent='domain-'+str(i-1) if i else None))
status=call();domains=status['domains'];assert len(domains)==3
if domains[2]['topology']['parent']!='domain-1':call(operation='reanchor',domain='domain-2',parent='domain-1');time.sleep(2)
status=call();domains=status['domains']
ns=[d['live']['networkNamespace'] for d in domains];assert len(set(ns))==3
assert domains[1]['topology']['upstream']==domains[0]['topology']['downstream']
assert domains[2]['topology']['upstream']==domains[1]['topology']['downstream']
assert all(d['live']['ownerAlive'] and len(d['live']['ownerPids'])==3 and len(d['live']['workstations'])==3 for d in domains)
assert all(all(w['computeCycles']>0 for w in d['live']['workstations']) for d in domains)
prefix='keddeh-'+__import__('hashlib').sha256(str(root).encode()).hexdigest()[:10]
def docker(*args):subprocess.run(['docker',*args],check=True,stdout=subprocess.DEVNULL)
before=domains[2]['live']['epoch'];phase_before=domains[2]['live']['elapsed']
docker('stop',prefix+'-domain-1')
try:
    time.sleep(3)
    lost=call()['domains'];assert lost[0]['live']['ownerAlive'];assert lost[2]['live']['mode']=='FLYWHEEL'
    assert lost[2]['live']['epoch']>before and lost[2]['live']['elapsed']>phase_before
    call(operation='reanchor',domain='domain-2',parent='domain-0')
    end=time.monotonic()+12
    while time.monotonic()<end:
        live=call()['domains'][2]['live']
        if live.get('anchor',{} ) and live['anchor']['domain']=='domain-0':break
        time.sleep(.5)
    assert live['anchor']['domain']=='domain-0';assert live['epoch']>before
    assert call()['domains'][2]['topology']['downstream']==domains[2]['topology']['downstream']
finally:
    docker('start',prefix+'-domain-1')
    call(operation='reanchor',domain='domain-2',parent='domain-1')
evidence={'status':'passed','checks':['three distinct actual network namespaces','recursive upstream/downstream network membership','owner workstation code executes in every domain','intermediate domain loss leaves genesis and child alive','child epoch and software phase advance in flywheel','child reanchors without resetting its state or downstream domain'],'namespaces':ns,'child_epoch_before':before,'child_epoch_after':live['epoch'],'scope':'local dual-homed virtual network domains; same host'}
Path(args.output).write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence,indent=2))
