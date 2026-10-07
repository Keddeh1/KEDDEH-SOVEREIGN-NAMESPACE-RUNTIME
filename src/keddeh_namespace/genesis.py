"""Bounded topology policy and signed challenge/readback on actual return sockets."""
import json
import secrets
import socket
import sqlite3
import time
from .envelope import canonical_bytes
from .signatures import verify_observation


def validate_topology(participant,children):
    if type(participant) is not str or not participant.strip(): raise ValueError('participant identity required')
    if type(children) is not list or len(children)!=3: raise ValueError('exactly three child domains required')
    identities={participant};endpoints=set();connection_ids=set()
    for child in children:
        if type(child) is not dict or set(child)!={'identity','returns'}: raise ValueError('invalid child fields')
        identity=child['identity']
        if type(identity) is not str or not identity.strip() or identity in identities: raise ValueError('distinct child identities required')
        identities.add(identity)
        returns=child['returns']
        if type(returns) is not list or len(returns)!=2: raise ValueError('exactly two independent returns required')
        for connection in returns:
            if type(connection) is not dict or set(connection)!={'identity','host','port'}: raise ValueError('invalid return fields')
            connection_id=connection['identity'];host=connection['host'];port=connection['port']
            if type(connection_id) is not str or not connection_id.strip() or connection_id in connection_ids:
                raise ValueError('distinct connection identities required')
            if type(host) is not str or not host.strip() or type(port) is not int or not 1<=port<=65535:
                raise ValueError('invalid endpoint')
            endpoint=(host,port)
            if endpoint in endpoints: raise ValueError('return endpoints must be distinct')
            endpoints.add(endpoint);connection_ids.add(connection_id)
    if identities & connection_ids: raise ValueError('participant, child and connection identities must be distinct')
    return children


class LeaseController:
    def __init__(self,database,*,max_active=3,cooldown=30,max_lease=300):
        if type(max_active) is not int or max_active!=3: raise ValueError('Genesis child ceiling must be three')
        if type(cooldown) is not int or cooldown<0 or type(max_lease) is not int or max_lease<=0:
            raise ValueError('invalid lease bounds')
        self.database=database;self.cooldown=cooldown;self.max_lease=max_lease
        with self.connect() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS leases (identity TEXT PRIMARY KEY, expires INTEGER NOT NULL);'
                             'CREATE TABLE IF NOT EXISTS nonces (nonce TEXT PRIMARY KEY);'
                             'CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), last_spawn INTEGER NOT NULL, frozen INTEGER NOT NULL);'
                             'INSERT OR IGNORE INTO state VALUES(1,0,0);')
    def connect(self):
        db=sqlite3.connect(self.database,timeout=10);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');return db
    def admit(self,identity,nonce,*,seconds,now=None):
        now=int(time.time()) if now is None else now
        if type(identity) is not str or not identity.strip() or type(nonce) is not str or not nonce.strip():
            raise ValueError('identity/nonce required')
        if type(seconds) is not int or not 0<seconds<=self.max_lease or type(now) is not int or now<=0:
            raise ValueError('invalid bounded lease')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            last,frozen=db.execute('SELECT last_spawn,frozen FROM state WHERE id=1').fetchone()
            if frozen: raise ValueError('spawn frozen')
            if now<last+self.cooldown: raise ValueError('spawn cooldown active')
            if db.execute('SELECT 1 FROM nonces WHERE nonce=?',(nonce,)).fetchone(): raise ValueError('replayed spawn nonce')
            if db.execute('SELECT 1 FROM leases WHERE identity=? AND expires>?',(identity,now)).fetchone(): raise ValueError('identity already active')
            if db.execute('SELECT COUNT(*) FROM leases WHERE expires>?',(now,)).fetchone()[0]>=3: raise ValueError('child resource ceiling')
            db.execute('INSERT INTO nonces VALUES(?)',(nonce,))
            db.execute('INSERT INTO leases VALUES(?,?) ON CONFLICT(identity) DO UPDATE SET expires=excluded.expires',(identity,now+seconds))
            db.execute('UPDATE state SET last_spawn=? WHERE id=1',(now,))
        return now+seconds
    def freeze(self):
        with self.connect() as db: db.execute('UPDATE state SET frozen=1 WHERE id=1')
    def reanchor(self,verified_recovery):
        if verified_recovery is not True: raise ValueError('verified recovery required')
        with self.connect() as db: db.execute('UPDATE state SET frozen=0 WHERE id=1')


def probe_returns(participant,children,trust,*,timeout=3):
    validate_topology(participant,children)
    receipts=[];resolved=set()
    for child in children:
        for connection in child['returns']:
            challenge=secrets.token_hex(32)
            with socket.create_connection((connection['host'],connection['port']),timeout=timeout) as stream:
                peer=stream.getpeername()[:2]
                if peer in resolved: raise ValueError('return endpoints resolve to same connection')
                resolved.add(peer)
                request={'participant':participant,'child':child['identity'],'connection':connection['identity'],'challenge':challenge}
                stream.sendall(canonical_bytes(request)+b'\n')
                data=b''
                while not data.endswith(b'\n'):
                    chunk=stream.recv(min(4096,65537-len(data)))
                    if not chunk: raise ValueError('return connection closed without readback')
                    data+=chunk
                    if len(data)>65536: raise ValueError('return readback exceeds bound')
                signed=json.loads(data)
                digest=verify_observation(signed,trust);envelope=signed['envelope']
                if envelope['runtime_id']!=child['identity'] or envelope['transaction']!=challenge or envelope['metric']!='genesis-return':
                    raise ValueError('return identity/challenge mismatch')
                if envelope['readback']!=connection['identity']: raise ValueError('return connection identity mismatch')
                receipts.append({'child':child['identity'],'connection':connection['identity'],'envelope_sha256':digest,'peer':list(peer)})
    return receipts
