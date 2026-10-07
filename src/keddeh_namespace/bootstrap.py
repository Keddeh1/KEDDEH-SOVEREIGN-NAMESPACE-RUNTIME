"""Fail-closed preflight using authenticated gate bundles and measured prerequisites."""
import argparse
import hashlib
import ipaddress
import json
import os
import stat
import dns.exception
import time
from datetime import datetime
from pathlib import Path
from .envelope import envelope_digest,verify_chain
from .evidence import GATES,validate
from .healthcheck import authority_probe
from .logical_vfs import logical_path
from .signatures import verify_observation,verify_assessment
from .verify_vfs import verify_volume
from .compile_zones import validate_nodes,zone_name


def read_private_artifact(root,path,*,max_bytes=1024**2):
    logical_path(path)
    candidate=root/path
    # Operator-controlled root, reject symlinks in every path component.
    current=root
    for part in Path(path).parts:
        current=current/part
        if current.is_symlink(): raise ValueError('bundle symlinks rejected')
    fd=os.open(candidate,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        status=os.fstat(stream.fileno())
        if not stat.S_ISREG(status.st_mode) or status.st_size>max_bytes: raise ValueError('bounded regular artifact required')
        payload=stream.read(max_bytes+1)
    if len(payload)>max_bytes: raise ValueError('artifact exceeds bound')
    return payload


def verify_gate_bundles(config,ledger,*,now=None):
    errors=validate(ledger)
    if errors: raise ValueError('acceptance ledger incomplete: '+'; '.join(errors))
    root=Path(config['evidence_root']).resolve(strict=True)
    trust=json.loads(read_private_artifact(root,config['trust_store']))
    max_age=config.get('max_evidence_age_seconds',300)
    if type(max_age) is not int or not 1<=max_age<=3600: raise ValueError('bounded evidence freshness required')
    now=time.time() if now is None else now
    seen=set()
    for gate in GATES:
        receipt=ledger['receipts'][gate]
        bundle=json.loads(read_private_artifact(root,receipt['signature_reference']))
        if type(bundle) is not dict or set(bundle)!={'signed','assessment','history','artifact_path'}: raise ValueError('invalid gate bundle')
        signed=bundle['signed'];envelope=signed['envelope']
        digest=verify_assessment(signed,bundle['assessment'],trust)
        if digest in seen: raise ValueError('gate receipt replay')
        seen.add(digest)
        for field in ('runtime_id','source_sha256','stateRoot','phaseRoot'):
            if envelope[field]!=ledger[field]: raise ValueError('gate generation binding mismatch')
        if envelope['generator_id']!=ledger['generator_id'] or bundle['assessment']['verifier_id']!=ledger['verifier_id']:
            raise ValueError('gate custody identity mismatch')
        if envelope['metric']!='gate:'+gate or envelope['transaction']!=receipt['command'] or envelope['readback']!=receipt['readback'] or envelope['observed_at']!=receipt['observed_at']:
            raise ValueError('gate observation binding mismatch')
        age=now-datetime.fromisoformat(envelope['observed_at'].replace('Z','+00:00')).timestamp()
        if not 0<=age<=max_age: raise ValueError('stale or future gate evidence')
        artifact=read_private_artifact(root,bundle['artifact_path'])
        if hashlib.sha256(artifact).hexdigest()!=receipt['artifact_sha256']: raise ValueError('gate artifact mismatch')
        history=bundle['history']
        if type(history) is not list or not history: raise ValueError('full signed gate history required')
        for observation in history: verify_observation(observation,trust)
        head=config['trusted_heads'][envelope['runtime_id']]
        verify_chain([observation['envelope'] for observation in history],trusted_head=head)
        if digest not in {envelope_digest(observation['envelope']) for observation in history}: raise ValueError('gate missing from signed history')
    return {'authenticated_gates':len(seen),'status':'gate_signatures_verified'}


def preflight(config,ledger):
    if type(config) is not dict or config.get('production') is not True: raise ValueError('explicit production configuration required')
    if not {'zone','nodes','evidence_root','trust_store','trusted_heads','archive_mount','dnskey_sha256'}.issubset(config):
        raise ValueError('complete production configuration required')
    authority=validate_nodes(config,zone_name(config['zone']))
    gate_receipt=verify_gate_bundles(config,ledger)
    volumes=[];mounts=[]
    for node in config['nodes']:
        path=Path(node['vfs_mount']).resolve(strict=True)
        if path in mounts: raise ValueError('distinct node storage mounts required')
        mounts.append(path)
        volumes.append(verify_volume(path,required_bytes=10_000_000_000_000))
    archive_path=Path(config['archive_mount']).resolve(strict=True)
    if archive_path in mounts: raise ValueError('separate archive mount required')
    volumes.append(verify_volume(archive_path,required_bytes=100_000_000_000_000))
    nodes=[authority_probe(address,config['zone'],pinned_dnskey_sha256=config['dnskey_sha256']) for _,address in authority]
    if nodes[0]['soa_serial']!=nodes[1]['soa_serial']: raise ValueError('authority serial divergence')
    return {'status':'preflight_passed_not_deployed','gate_receipt':gate_receipt,'volumes':volumes,'nodes':nodes}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config');parser.add_argument('ledger');args=parser.parse_args()
    try:
        with open(args.config) as stream: config=json.load(stream)
        with open(args.ledger) as stream: ledger=json.load(stream)
        receipt=preflight(config,ledger)
    except (OSError,ValueError,KeyError,TypeError,dns.exception.DNSException) as exc: parser.exit(1,f'Bootstrap not ready: {exc}\n')
    print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__': main()
