"""Loopback-only registry with authenticated writes and durable signed observations."""
import argparse
import hashlib
import hmac
import ipaddress
import json
import os
import urllib.parse
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .envelope import canonical_bytes, content_root
from .logical_vfs import Conflict, LogicalVFS, logical_path
from .signatures import verify_observation, verify_assessment

MAX_REQUEST = 1024 * 1024


class Registry:
    def __init__(self, root, trust):
        self.vfs=LogicalVFS(root)
        self.trust=trust
        with self.vfs.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests '
                       '(request_id TEXT PRIMARY KEY, body_digest TEXT NOT NULL, result BLOB NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS observations '
                       '(digest TEXT PRIMARY KEY, runtime_id TEXT NOT NULL, signed BLOB NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS assessments '
                       '(digest TEXT PRIMARY KEY, verifier_id TEXT NOT NULL, signed BLOB NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS observation_heads '
                       '(runtime_id TEXT PRIMARY KEY, digest TEXT NOT NULL)')

    def commit(self, request):
        if type(request) is not dict or set(request) != {'request_id','path','expected_version','signed','desired_state','phase_state'}:
            raise ValueError('invalid request fields')
        request_id=request['request_id']
        if type(request_id) is not str or not request_id.strip() or len(request_id)>128:
            raise ValueError('invalid request_id')
        path=logical_path(request['path'])
        expected=request['expected_version']
        if type(expected) is not int or expected<0:
            raise ValueError('invalid expected_version')
        signed=request['signed']
        digest=verify_observation(signed,self.trust)
        if signed['envelope']['stateRoot']!=content_root('state',request['desired_state']) or signed['envelope']['phaseRoot']!=content_root('phase',request['phase_state']):
            raise ValueError('signed roots do not bind to desired/phase data')
        raw=canonical_bytes(request)
        body_digest=hashlib.sha256(raw).hexdigest()
        payload=canonical_bytes({'signed':signed,'desired_state':request['desired_state'],'phase_state':request['phase_state']})
        object_digest=self.vfs.put_object(payload)
        runtime=signed['envelope']['runtime_id']
        if signed['envelope']['metric']!='registry-generation:'+path:
            raise ValueError('signed observation does not bind to namespace path')
        with self.vfs.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous_request=db.execute('SELECT * FROM requests WHERE request_id=?',(request_id,)).fetchone()
            if previous_request:
                if previous_request['body_digest'] != body_digest:
                    raise Conflict('idempotency key reused for different request')
                return json.loads(previous_request['result'])
            if db.execute('SELECT 1 FROM observations WHERE digest=?',(digest,)).fetchone():
                raise Conflict('observation replay')
            head=db.execute('SELECT * FROM heads WHERE path=?',(path,)).fetchone()
            current=head['version'] if head else 0
            if current != expected: raise Conflict('stale generation')
            chain_head=db.execute('SELECT digest FROM observation_heads WHERE runtime_id=?',(runtime,)).fetchone()
            if signed['envelope']['parent_envelope_sha256'] != (chain_head['digest'] if chain_head else None):
                raise Conflict('observation chain diverges')
            last=db.execute('SELECT sequence,receipt FROM events ORDER BY sequence DESC LIMIT 1').fetchone()
            event=dict(sequence=last['sequence']+1 if last else 1,path=path,version=current+1,
                       digest=object_digest,parent=last['receipt'] if last else None)
            receipt=hashlib.sha256(canonical_bytes(event)).hexdigest()
            result=dict(event,receipt=receipt,envelope_sha256=digest)
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(*event.values(),receipt))
            db.execute('INSERT INTO heads VALUES(?,?,?,?) ON CONFLICT(path) DO UPDATE SET '
                       'version=excluded.version,digest=excluded.digest,receipt=excluded.receipt',
                       (path,current+1,object_digest,receipt))
            db.execute('INSERT INTO observations VALUES(?,?,?)',(digest,runtime,canonical_bytes(signed)))
            db.execute('INSERT INTO observation_heads VALUES(?,?) ON CONFLICT(runtime_id) '
                       'DO UPDATE SET digest=excluded.digest',(runtime,digest))
            db.execute('INSERT INTO requests VALUES(?,?,?)',(request_id,body_digest,canonical_bytes(result)))
        return result

    def assess(self, assessment):
        if type(assessment) is not dict: raise ValueError('assessment object required')
        digest=assessment.get('envelope_sha256')
        raw=canonical_bytes(assessment)
        with self.vfs.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT signed FROM observations WHERE digest=?',(digest,)).fetchone()
            if row is None: raise ValueError('observation not committed')
            verify_assessment(json.loads(row['signed']),assessment,self.trust)
            existing=db.execute('SELECT signed FROM assessments WHERE digest=?',(digest,)).fetchone()
            if existing:
                if existing['signed']!=raw: raise Conflict('assessment already recorded')
            else:
                db.execute('INSERT INTO assessments VALUES(?,?,?)',(digest,assessment['verifier_id'],raw))
        return {'envelope_sha256':digest,'verifier_id':assessment['verifier_id'],'status':'assessment_signature_verified'}

    def replay(self):
        events=self.vfs.history()
        with self.vfs.connect() as db:
            observations={row['digest']:dict(row) for row in db.execute('SELECT * FROM observations')}
            persisted_heads={row['runtime_id']:row['digest'] for row in db.execute('SELECT * FROM observation_heads')}
            assessments=[dict(row) for row in db.execute('SELECT * FROM assessments')]
        chain_heads={}
        seen=set()
        for event in events:
            generation=json.loads(self.vfs.read_object(event['digest']))
            if set(generation)!={'signed','desired_state','phase_state'}: raise ValueError('invalid generation object')
            signed=generation['signed']
            if signed['envelope']['stateRoot']!=content_root('state',generation['desired_state']) or signed['envelope']['phaseRoot']!=content_root('phase',generation['phase_state']):
                raise ValueError('stored generation data/root mismatch')
            digest=verify_observation(signed,self.trust)
            envelope=signed['envelope'];runtime=envelope['runtime_id']
            if envelope['metric']!='registry-generation:'+event['path']:
                raise ValueError('signed registry path mismatch')
            if digest in seen or envelope['parent_envelope_sha256'] != chain_heads.get(runtime):
                raise ValueError('invalid observation replay chain')
            if observations.get(digest,{}).get('signed') != canonical_bytes(signed):
                raise ValueError('observation projection divergence')
            chain_heads[runtime]=digest;seen.add(digest)
        if seen != set(observations) or chain_heads != persisted_heads:
            raise ValueError('registry projections diverge')
        for assessment in assessments:
            row=observations.get(assessment['digest'])
            if row is None: raise ValueError('orphan assessment')
            verified=json.loads(assessment['signed'])
            if assessment['verifier_id']!=verified['verifier_id']: raise ValueError('assessment projection divergence')
            verify_assessment(json.loads(row['signed']),verified,self.trust)
        return events


def make_server(registry, token, host='127.0.0.1', port=0):
    if not ipaddress.ip_address(host).is_loopback:
        raise ValueError('registry must bind loopback')
    if type(token) is not str or len(token)<32 or '\n' in token or '\r' in token:
        raise ValueError('a nonempty secret token of at least 32 characters is required')
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup();self.connection.settimeout(5)
        def log_message(self,*args): pass  # never log request headers or payloads
        def reply(self,status,payload):
            data=canonical_bytes(payload)
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def authorized(self):
            return hmac.compare_digest(self.headers.get('Authorization','').encode('utf-8'), ('Bearer '+token).encode('utf-8'))
        def do_GET(self):
            if not self.authorized(): return self.reply(401,{'error':'unauthorized'})
            parsed=urllib.parse.urlsplit(self.path)
            if parsed.path=='/generations':
                try:
                    query=urllib.parse.parse_qs(parsed.query,strict_parsing=True)
                    if set(query)!={'path'} or len(query['path'])!=1: raise ValueError('one path required')
                    registry.replay()
                    head,payload=registry.vfs.read(query['path'][0])
                    return self.reply(200,{'head':head,'generation':json.loads(payload)})
                except KeyError: return self.reply(404,{'error':'generation not found'})
                except (ValueError,OSError,sqlite3.Error): return self.reply(400,{'error':'invalid generation readback'})
            if self.path != '/health': return self.reply(404,{'error':'not found'})
            try: count=len(registry.replay())
            except (ValueError,OSError,sqlite3.Error): return self.reply(503,{'status':'invalid registry'})
            self.reply(200,{'status':'ok','verified_events':count})
        def do_POST(self):
            if not self.authorized(): return self.reply(401,{'error':'unauthorized'})
            if self.path not in ('/generations','/assessments'): return self.reply(404,{'error':'not found'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0 < length <= MAX_REQUEST: return self.reply(413,{'error':'invalid request size'})
                request=json.loads(self.rfile.read(length))
                result=registry.commit(request) if self.path=='/generations' else registry.assess(request)
            except Conflict as exc: return self.reply(409,{'error':str(exc)})
            except (ValueError,TypeError,KeyError): return self.reply(400,{'error':'invalid signed generation'})
            except (OSError,sqlite3.Error): return self.reply(503,{'error':'storage failure'})
            self.reply(201,result)
    server=ThreadingHTTPServer((host,port),Handler)
    server.timeout=5
    return server


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True);parser.add_argument('--trust-store',required=True)
    parser.add_argument('--port',type=int,default=8081)
    args=parser.parse_args()
    token=os.environ.get('KEDDEH_REGISTRY_TOKEN')
    if not token: parser.error('KEDDEH_REGISTRY_TOKEN must be set securely')
    with open(args.trust_store) as stream: trust=json.load(stream)
    registry=Registry(args.root,trust);registry.replay()
    server=make_server(registry,token,port=args.port)
    try: server.serve_forever()
    finally: server.server_close()


if __name__ == '__main__': main()
