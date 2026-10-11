"""Local content-addressed VFS with SQLite version journal and readback integrity."""
from contextlib import contextmanager
import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path, PurePosixPath
from .envelope import canonical_bytes


class Conflict(ValueError):
    pass


def logical_path(value):
    if type(value) is not str or not value or '\\' in value or '\x00' in value:
        raise ValueError('invalid logical path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('logical paths must be canonical relative paths')
    return value


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class LogicalVFS:
    """Use an operator-controlled private root; permissions are not a tamper-proof seal."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.objects = self.root / 'objects'
        self.objects.mkdir(mode=0o700,parents=True, exist_ok=True)
        self.database = self.root / 'journal.sqlite3'
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY, path TEXT NOT NULL,
                    version INTEGER NOT NULL, digest TEXT NOT NULL,
                    parent TEXT, receipt TEXT NOT NULL UNIQUE,
                    UNIQUE(path, version));
                CREATE TABLE IF NOT EXISTS heads (
                    path TEXT PRIMARY KEY, version INTEGER NOT NULL,
                    digest TEXT NOT NULL, receipt TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def put_object(self, payload):
        if type(payload) is not bytes:
            raise ValueError('payload must be bytes')
        digest = hashlib.sha256(payload).hexdigest()
        target = self.objects / digest
        fd, staging = tempfile.mkstemp(prefix='.staging-', dir=self.objects)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(staging, 0o444)
            try:
                os.link(staging, target)  # exclusive publication, no replacement
                sync_directory(self.objects)
            except FileExistsError:
                pass
            if self.read_object(digest) != payload:
                raise ValueError('object readback mismatch')
        finally:
            Path(staging).unlink(missing_ok=True)
        return digest

    def read_object(self, digest):
        if type(digest) is not str or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('invalid object digest')
        target = self.objects / digest
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            payload = stream.read()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError('corrupt object')
        return payload

    def write(self, path, payload, *, expected_version):
        path = logical_path(path)
        if type(expected_version) is not int or expected_version < 0:
            raise ValueError('expected_version must be a nonnegative integer')
        digest = self.put_object(payload)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            head = db.execute('SELECT * FROM heads WHERE path=?', (path,)).fetchone()
            current = head['version'] if head else 0
            if current != expected_version:
                raise Conflict(f'expected {expected_version}, observed {current}')
            last = db.execute('SELECT sequence, receipt FROM events ORDER BY sequence DESC LIMIT 1').fetchone()
            event = dict(sequence=last['sequence'] + 1 if last else 1, path=path,
                         version=current + 1, digest=digest, parent=last['receipt'] if last else None)
            receipt = hashlib.sha256(canonical_bytes(event)).hexdigest()
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',
                       (*event.values(), receipt))
            db.execute('INSERT INTO heads VALUES(?,?,?,?) ON CONFLICT(path) DO UPDATE SET '
                       'version=excluded.version,digest=excluded.digest,receipt=excluded.receipt',
                       (path,current+1,digest,receipt))
        return dict(event, receipt=receipt)

    def read(self, path):
        path = logical_path(path)
        with self.connect() as db:
            head = db.execute('SELECT * FROM heads WHERE path=?', (path,)).fetchone()
        if head is None:
            raise KeyError(path)
        return dict(head), self.read_object(head['digest'])

    def history(self):
        with self.connect() as db:
            events = [dict(row) for row in db.execute('SELECT * FROM events ORDER BY sequence')]
            actual_heads = {row['path']: dict(row) for row in db.execute('SELECT * FROM heads')}
        previous = None
        heads = {}
        for sequence, event in enumerate(events, 1):
            raw = {k:v for k,v in event.items() if k != 'receipt'}
            if event['sequence'] != sequence or event['parent'] != previous:
                raise ValueError('broken journal chain')
            if hashlib.sha256(canonical_bytes(raw)).hexdigest() != event['receipt']:
                raise ValueError('invalid journal receipt')
            if event['version'] != heads.get(event['path'], {}).get('version',0) + 1:
                raise ValueError('invalid path version')
            self.read_object(event['digest'])
            previous = event['receipt']
            heads[event['path']] = {k:event[k] for k in ('path','version','digest','receipt')}
        if heads != actual_heads:
            raise ValueError('head projection diverges from journal')
        return events
