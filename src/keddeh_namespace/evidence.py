"""Check submitted ledger shape; live and cryptographic verification is external."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

GATES = (
    'exact_source', 'ns1_vfs', 'ns2_vfs', 'archive_restore',
    'ns1_authority_udp_tcp', 'ns2_authority_udp_tcp', 'recursion_refused',
    'dnssec', 'tsig_soa_convergence', 'registry_concurrency_chain',
    'forward_backward_lineage', 'genesis_topology', 'service_isolation',
    'external_dns_tls',
)
HASH = re.compile(r'[0-9a-f]{64}')


def validate(ledger):
    """Return errors; no submitted assertion is executed or authenticated here."""
    errors = []
    if not isinstance(ledger, dict):
        return ['ledger must be an object']
    for key in ('runtime_id', 'generator_id', 'verifier_id', 'transaction'):
        if not isinstance(ledger.get(key), str) or not ledger[key].strip():
            errors.append(f'{key} must be a nonempty string')
    if ledger.get('generator_id') == ledger.get('verifier_id'):
        errors.append('generator and verifier must differ')
    for key in ('source_sha256', 'stateRoot', 'phaseRoot', 'parent_stateRoot'):
        value = ledger.get(key)
        if not isinstance(value, str) or not HASH.fullmatch(value):
            errors.append(f'{key} must be a SHA-256 hex digest')
    if ledger.get('stateRoot') == ledger.get('phaseRoot'):
        errors.append('stateRoot and phaseRoot must remain distinct')
    receipts = ledger.get('receipts')
    if not isinstance(receipts, dict):
        return errors + ['receipts must be an object']
    for gate in GATES:
        receipt = receipts.get(gate)
        if not isinstance(receipt, dict):
            errors.append(f'{gate}: missing receipt')
            continue
        if receipt.get('status') != 'passed':
            errors.append(f'{gate}: not passed')
        for key in ('artifact_sha256',):
            value = receipt.get(key)
            if not isinstance(value, str) or not HASH.fullmatch(value):
                errors.append(f'{gate}: invalid {key}')
        for key in ('command', 'readback', 'signature_reference'):
            if not isinstance(receipt.get(key), str) or not receipt[key].strip():
                errors.append(f'{gate}: missing {key}')
        for key in ('runtime_id', 'source_sha256', 'stateRoot', 'phaseRoot'):
            if receipt.get(key) != ledger.get(key):
                errors.append(f'{gate}: {key} does not bind to ledger')
        if receipt.get('assessor_id') != ledger.get('verifier_id'):
            errors.append(f'{gate}: assessor does not match independent verifier')
        try:
            timestamp = datetime.fromisoformat(receipt.get('observed_at', ''))
            if timestamp.utcoffset() is None:
                raise ValueError('timezone required')
        except (ValueError, TypeError):
            errors.append(f'{gate}: invalid timezone-aware observed_at')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    args = parser.parse_args()
    try:
        errors = validate(json.loads(args.ledger.read_text()))
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Cannot read ledger: {exc}\n')
    if errors:
        print('\n'.join(errors))
        return 1
    print('Ledger structure consistent; live checks and signature authentication still required.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
