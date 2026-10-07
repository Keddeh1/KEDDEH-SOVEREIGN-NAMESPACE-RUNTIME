#!/usr/bin/env python3
"""Validate controlled-document register and evidence-state consistency."""
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / 'governance'

def validate():
    errors = []
    register = json.loads((GOV / 'document-register.json').read_text())
    seen = set()
    paths = set()
    for row in register['documents']:
        ident = row['document_id']
        if ident in seen:
            errors.append(f'duplicate ID: {ident}')
        seen.add(ident)
        rel = Path(row['path'])
        path = (ROOT / rel).resolve()
        if rel.is_absolute() or '..' in rel.parts or not path.is_relative_to(GOV.resolve()):
            errors.append(f'unsafe path: {ident}')
            continue
        if path in paths:
            errors.append(f'duplicate path: {ident}')
        paths.add(path)
        if not path.is_file():
            errors.append(f'missing file: {ident}')
            continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            errors.append(f'hash mismatch: {ident}; revise controlled document and register')
        text = raw.decode('utf-8')
        if not text.startswith('---\n') or '\n---\n' not in text[4:]:
            errors.append(f'missing metadata: {ident}')
            continue
        metadata = dict(line.split(': ', 1) for line in text.split('---', 2)[1].strip().splitlines() if ': ' in line)
        for key in ('document_id', 'title', 'revision', 'status', 'classification', 'accountable_owner', 'issued_on', 'review_due'):
            if metadata.get(key) != row.get(key):
                errors.append(f'metadata mismatch {ident}: {key}')
        for key in ('approval_basis', 'timezone'):
            if not metadata.get(key):
                errors.append(f'missing {key}: {ident}')
        if row['status'] not in ('Draft','In review','Approved','Issued','Superseded','Archived','Rejected','Withdrawn'):
            errors.append(f'invalid status: {ident}')
        if row['classification'] not in ('Public','Internal','Confidential','Restricted'):
            errors.append(f'invalid classification: {ident}')
        issued, review = date.fromisoformat(row['issued_on']), date.fromisoformat(row['review_due'])
        if review <= issued:
            errors.append(f'invalid review date: {ident}')
        if review < date.today() and row['status'] in ('Approved','Issued'):
            errors.append(f'overdue review: {ident}')
    standards = {p.resolve() for p in GOV.glob('*.md') if p.name != 'README.md'}
    if standards != paths:
        errors.append('unregistered or duplicate controlled standard')
    controls = json.loads((GOV / 'control-register.json').read_text())['controls']
    control_ids = set()
    for control in controls:
        if control['control_id'] in control_ids:
            errors.append('duplicate control ID')
        control_ids.add(control['control_id'])
        if control['status'] not in ('documented','partially implemented','implemented','verified operating','not applicable'):
            errors.append(f'invalid control status: {control["control_id"]}')
        if not control.get('evidence') or not control.get('owner_role'):
            errors.append(f'missing control evidence/owner: {control["control_id"]}')
        if control['status'] == 'not applicable' and not control.get('applicability_decision'):
            errors.append('not-applicable control requires decision')
    for exception in json.loads((GOV / 'exception-register.json').read_text())['exceptions']:
        if exception.get('status') == 'approved':
            if not all(exception.get(k) for k in ('approver','approval_evidence','expires_on','control_id')):
                errors.append('approved exception lacks authority/expiry')
            if date.fromisoformat(exception['expires_on']) < date.today():
                errors.append('approved exception expired')
    if errors:
        raise ValueError('\n'.join(errors))
    print(f'Governance integrity passed: {len(seen)} standards, {len(controls)} controls. Human approvals and production assurance are not validated by this check.')

if __name__ == '__main__':
    validate()
