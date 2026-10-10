"""Typed read/recovery adapter for the actual Keddeh LogicalVFS.

No altered algebra, mock carriers, firmware guarantees or process-memory restoration.
"""
from dataclasses import dataclass, asdict
import hashlib
from keddeh_namespace.logical_vfs import LogicalVFS, Conflict, logical_path

@dataclass(frozen=True)
class Observation:
    identity: str
    status: str
    version: int | None = None
    digest: str | None = None
    receipt: str | None = None
    payload: bytes | None = None
    reason: str | None = None

class ContinuityVFS:
    def __init__(self, root):
        self.vfs = LogicalVFS(root)

    def observe(self, identity):
        identity = logical_path(identity)
        try:
            with self.vfs.connect() as db:
                head = db.execute('SELECT * FROM heads WHERE path=?', (identity,)).fetchone()
                if head is None:
                    return Observation(identity, 'ABSENT')
                # Check metadata against its committed event. This is local integrity,
                # not authentication against an attacker rewriting the entire journal.
                event = db.execute('SELECT * FROM events WHERE path=? AND version=?',
                                   (identity, head['version'])).fetchone()
                if event is None or any(head[k] != event[k] for k in ('path','version','digest','receipt')):
                    return Observation(identity, 'METADATA_REJECTED', reason='head/event mismatch')
                from keddeh_namespace.envelope import canonical_bytes
                raw = {k: event[k] for k in ('sequence','path','version','digest','parent')}
                if hashlib.sha256(canonical_bytes(raw)).hexdigest() != event['receipt']:
                    return Observation(identity, 'METADATA_REJECTED', reason='event receipt mismatch')
            metadata = dict(version=head['version'], digest=head['digest'], receipt=head['receipt'])
            try:
                payload = self.vfs.read_object(head['digest'])
                return Observation(identity, 'AVAILABLE', payload=payload, **metadata)
            except FileNotFoundError:
                return Observation(identity, 'REHYDRATABLE', reason='backing object missing; verified bytes required', **metadata)
            except (ValueError, OSError) as exc:
                return Observation(identity, 'CARRIER_REJECTED', reason=type(exc).__name__, **metadata)
        except Exception:
            # Metadata/database failures must not be disguised as recoverable payload loss.
            raise

    def recover(self, identity, payload, *, expected_version):
        identity = logical_path(identity)
        if type(payload) is not bytes:
            raise ValueError('recovery payload must be bytes')
        before = self.observe(identity)
        if before.status not in ('AVAILABLE', 'REHYDRATABLE'):
            raise ValueError('recovery requires trusted retained metadata and a missing or valid object')
        if before.version != expected_version:
            raise Conflict('recovery version changed')
        if hashlib.sha256(payload).hexdigest() != before.digest:
            raise ValueError('recovery bytes do not match retained content identity')
        # Hold the existing journal's write lock during publication/readback so another
        # version cannot become current between validation and our observed result.
        with self.vfs.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            head = db.execute('SELECT * FROM heads WHERE path=?', (identity,)).fetchone()
            if head is None or any(head[k] != getattr(before,k) for k in ('version','digest','receipt')):
                raise Conflict('recovery head changed')
            self.vfs.put_object(payload)
            observed = self.vfs.read_object(before.digest)
            return Observation(identity, 'AVAILABLE', before.version, before.digest, before.receipt, observed)
