"""Versioned canonical observation envelopes; hashes do not authenticate authors."""
import hashlib
import json
import re
from datetime import datetime, timezone

SCHEMA = 'keddeh.observation.v1'
DIGEST = re.compile('[0-9a-f]{64}')
FIELDS = {'schema', 'runtime_id', 'source_sha256', 'generator_id', 'observer_id',
          'metric', 'execution_plane', 'observed_at', 'transaction', 'readback',
          'stateRoot', 'phaseRoot', 'parent_envelope_sha256'}


def canonical_bytes(value):
    """Project encoding: sorted keys, UTF-8, no floats; not RFC 8785 JCS."""
    def check(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            for child in item.values():
                check(child)
            return
        raise ValueError('canonical values require JSON objects/lists and exact scalar types; floats excluded')
    check(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def content_root(kind, payload):
    if kind not in ('state', 'phase'):
        raise ValueError('root kind must be state or phase')
    return hashlib.sha256(canonical_bytes({'schema': 'keddeh.root.v1',
                                          'kind': kind, 'payload': payload})).hexdigest()


def validate(envelope):
    if type(envelope) is not dict or set(envelope) != FIELDS:
        raise ValueError('envelope fields must match v1 schema exactly')
    if envelope['schema'] != SCHEMA:
        raise ValueError('unsupported envelope schema')
    for field in ('runtime_id', 'generator_id', 'observer_id', 'metric',
                  'execution_plane', 'transaction', 'readback'):
        if type(envelope[field]) is not str or not envelope[field].strip():
            raise ValueError(f'{field} must be a nonempty string')
    for field in ('source_sha256', 'stateRoot', 'phaseRoot'):
        if type(envelope[field]) is not str or not DIGEST.fullmatch(envelope[field]):
            raise ValueError(f'{field} must be SHA-256 hex')
    parent = envelope['parent_envelope_sha256']
    if parent is not None and (type(parent) is not str or not DIGEST.fullmatch(parent)):
        raise ValueError('parent must be null for genesis or a SHA-256 digest')
    if envelope['stateRoot'] == envelope['phaseRoot']:
        raise ValueError('stateRoot and phaseRoot must be distinct')
    timestamp = envelope['observed_at']
    if type(timestamp) is not str:
        raise ValueError('observed_at must be canonical UTC text')
    try:
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if parsed.utcoffset() is None:
            raise ValueError('timezone required')
        normalized = parsed.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
    except (ValueError, OverflowError):
        raise ValueError('invalid observed_at') from None
    if parsed.utcoffset() is None or timestamp != normalized:
        raise ValueError('observed_at requires UTC YYYY-MM-DDTHH:MM:SS.ffffffZ')
    canonical_bytes(envelope)


def envelope_digest(envelope):
    validate(envelope)
    return hashlib.sha256(canonical_bytes(envelope)).hexdigest()


def verify_chain(envelopes, *, trusted_head):
    """Verify all links including genesis against an externally retained head digest.

    A matching head provides integrity relative to that checkpoint, not signature
    authentication or proof that the represented command actually ran.
    """
    if type(envelopes) is not list or not envelopes:
        raise ValueError('a complete nonempty chain from genesis is required')
    previous = None
    for envelope in envelopes:
        digest = envelope_digest(envelope)
        if envelope['parent_envelope_sha256'] != previous:
            raise ValueError('chain parent mismatch')
        previous = digest
    if type(trusted_head) is not str or not DIGEST.fullmatch(trusted_head) or previous != trusted_head:
        raise ValueError('chain does not match trusted head')
    return previous
