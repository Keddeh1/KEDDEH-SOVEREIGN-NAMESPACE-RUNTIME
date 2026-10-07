"""Archive verified signed history and rehydrate by replaying actual object bytes."""
import hashlib
import json
from .envelope import canonical_bytes,content_root
from .logical_vfs import LogicalVFS, logical_path
from .registry_service import Registry
from .signatures import verify_observation, verify_assessment


def archive_registry(registry, archive_root):
    events=registry.replay()
    if not events: raise ValueError('no generation to archive')
    archive=LogicalVFS(archive_root)
    entries=[]
    for event in events:
        payload=registry.vfs.read_object(event['digest'])
        if archive.put_object(payload)!=event['digest']: raise ValueError('archive copy mismatch')
        entries.append({'path':event['path'],'version':event['version'],'object_sha256':event['digest']})
    with registry.vfs.connect() as db:
        assessments=[archive.put_object(row['signed']) for row in db.execute('SELECT signed FROM assessments ORDER BY digest')]
    manifest={'schema':'keddeh.archive.v1','entries':entries,'journal_head':events[-1]['receipt'],'assessments':assessments}
    payload=canonical_bytes(manifest)
    digest=archive.put_object(payload)
    return {'archive_manifest_sha256':digest,'events':len(entries),'journal_head':manifest['journal_head']}


def restore_registry(archive_root, manifest_digest, target_root, trust):
    archive=LogicalVFS(archive_root)
    manifest=json.loads(archive.read_object(manifest_digest))
    if type(manifest) is not dict or set(manifest)!={'schema','entries','journal_head','assessments'} or manifest['schema']!='keddeh.archive.v1':
        raise ValueError('invalid archive manifest')
    registry=Registry(target_root,trust)
    if registry.replay(): raise ValueError('restore target must have empty history')
    # Validate all archive bytes and signature bindings before replay begins.
    requests=[];heads={};versions={};journal_head=None;seen=set();signed_by_digest={}
    for index,entry in enumerate(manifest['entries']):
        if type(entry) is not dict or set(entry)!={'path','version','object_sha256'}: raise ValueError('invalid archive entry')
        logical_path(entry['path'])
        original=archive.read_object(entry['object_sha256'])
        generation=json.loads(original)
        if type(generation) is not dict or set(generation)!={'signed','desired_state','phase_state'}: raise ValueError('invalid archived generation')
        if canonical_bytes(generation)!=original: raise ValueError('noncanonical archived generation')
        signed=generation['signed']
        if signed['envelope']['stateRoot']!=content_root('state',generation['desired_state']) or signed['envelope']['phaseRoot']!=content_root('phase',generation['phase_state']):
            raise ValueError('archive data/root mismatch')
        digest=verify_observation(signed,trust)
        if digest in seen: raise ValueError('archive observation replay')
        seen.add(digest);signed_by_digest[digest]=signed
        runtime=signed['envelope']['runtime_id']
        if signed['envelope']['parent_envelope_sha256']!=heads.get(runtime): raise ValueError('archive lineage divergence')
        version=versions.get(entry['path'],0)
        if entry['version']!=version+1: raise ValueError('archive version divergence')
        heads[runtime]=digest;versions[entry['path']]=version+1
        event=dict(sequence=index+1,path=entry['path'],version=version+1,
                   digest=entry['object_sha256'],parent=journal_head)
        journal_head=hashlib.sha256(canonical_bytes(event)).hexdigest()
        requests.append(dict(desired_state=generation['desired_state'],phase_state=generation['phase_state'],request_id=f'restore:{manifest_digest}:{index}',path=entry['path'],expected_version=version,signed=signed))
    if not requests: raise ValueError('empty archive')
    if journal_head!=manifest['journal_head']: raise ValueError('archive journal head divergence')
    if type(manifest['assessments']) is not list: raise ValueError('invalid archive assessments')
    assessments=[];assessed=set()
    for object_digest in manifest['assessments']:
        payload=archive.read_object(object_digest);assessment=json.loads(payload)
        if canonical_bytes(assessment)!=payload: raise ValueError('noncanonical archived assessment')
        digest=assessment.get('envelope_sha256')
        if digest not in signed_by_digest or digest in assessed: raise ValueError('invalid assessment archive binding')
        verify_assessment(signed_by_digest[digest],assessment,trust)
        assessed.add(digest);assessments.append(assessment)
    for request in requests: registry.commit(request)
    for assessment in assessments: registry.assess(assessment)
    events=registry.replay()
    if events[-1]['receipt']!=manifest['journal_head']: raise ValueError('restored journal head mismatch')
    return registry


def backward_lineage(registry,path):
    registry.replay()
    head,payload=registry.vfs.read(path)
    generation=json.loads(payload)
    signed=generation['signed']
    result=[]
    with registry.vfs.connect() as db:
        observations={row['digest']:json.loads(row['signed']) for row in db.execute('SELECT * FROM observations')}
    while signed is not None:
        digest=verify_observation(signed,registry.trust);envelope=signed['envelope']
        result.append({'envelope_sha256':digest,'source_sha256':envelope['source_sha256'],
                       'stateRoot':envelope['stateRoot'],'phaseRoot':envelope['phaseRoot'],
                       'generator_id':envelope['generator_id'],'runtime_id':envelope['runtime_id']})
        parent=envelope['parent_envelope_sha256']
        signed=observations[parent] if parent else None
    return result
