"""Ed25519 envelopes and independently signed assessments with explicit trust roles."""
import base64
import json
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .envelope import canonical_bytes, envelope_digest

DOMAIN = b'keddeh.signed-observation.v1\0'
ASSESSMENT_DOMAIN = b'keddeh.assessment.v1\0'


def sign_observation(envelope, private_key):
    envelope_digest(envelope)
    # Copy through canonical bytes; later caller mutations cannot change this object.
    payload = json.loads(canonical_bytes(envelope))
    return {'envelope':payload,
            'signature':base64.b64encode(private_key.sign(DOMAIN+canonical_bytes(payload))).decode()}


def trusted_key(trust, identity, role):
    if type(trust) is not dict: raise ValueError('explicit trust mapping required')
    entry = trust.get(identity)
    if not isinstance(entry, dict) or type(entry.get('roles')) is not list or role not in entry.get('roles', []):
        raise ValueError('identity is not trusted for this role')
    try:
        raw = base64.b64decode(entry['public_key'], validate=True)
        return Ed25519PublicKey.from_public_bytes(raw)
    except (KeyError, ValueError, TypeError):
        raise ValueError('invalid trusted public key') from None


def verify_signature(key, signature, payload):
    try:
        key.verify(base64.b64decode(signature,validate=True),payload)
    except (InvalidSignature, ValueError, TypeError):
        raise ValueError('invalid signature') from None


def verify_observation(signed, trust):
    if type(signed) is not dict or set(signed) != {'envelope','signature'}:
        raise ValueError('invalid signed observation fields')
    envelope = signed['envelope']
    digest = envelope_digest(envelope)
    key = trusted_key(trust,envelope['generator_id'],'generator')
    allowed=trust[envelope['generator_id']].get('runtime_ids')
    if type(allowed) is not list or envelope['runtime_id'] not in allowed:
        raise ValueError('signer is not trusted for this runtime identity')
    verify_signature(key,signed['signature'],DOMAIN+canonical_bytes(envelope))
    return digest


def sign_assessment(signed, verifier_id, private_key):
    digest=envelope_digest(signed['envelope'])
    if verifier_id == signed['envelope']['generator_id']:
        raise ValueError('generator cannot independently assess itself')
    payload={'schema':'keddeh.assessment.v1','envelope_sha256':digest,'verifier_id':verifier_id}
    return dict(payload,signature=base64.b64encode(private_key.sign(ASSESSMENT_DOMAIN+canonical_bytes(payload))).decode())


def verify_assessment(signed, assessment, trust):
    digest=verify_observation(signed,trust)
    if type(assessment) is not dict or set(assessment) != {'schema','envelope_sha256','verifier_id','signature'}:
        raise ValueError('invalid assessment fields')
    verifier=assessment['verifier_id']
    if assessment['schema'] != 'keddeh.assessment.v1' or assessment['envelope_sha256'] != digest:
        raise ValueError('assessment does not bind to observation')
    if verifier == signed['envelope']['generator_id']:
        raise ValueError('independent assessor required')
    generator_key=trusted_key(trust,signed['envelope']['generator_id'],'generator')
    verifier_key=trusted_key(trust,verifier,'verifier')
    if verifier_key.public_bytes_raw() == generator_key.public_bytes_raw():
        raise ValueError('independent assessor key required')
    payload={k:v for k,v in assessment.items() if k!='signature'}
    verify_signature(verifier_key,assessment['signature'],ASSESSMENT_DOMAIN+canonical_bytes(payload))
    return digest
