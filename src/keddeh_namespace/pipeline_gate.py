"""Durable owner command fence shared by HTML KEX projections and multiplexers."""
from contextlib import contextmanager
import json
import threading

class PipelineGate:
    def __init__(self, state):
        self.path = state / 'pipeline-gate.json'
        self.lock = threading.RLock()
        self.agreement_path = state / 'projection-agreement.json'
        self.agreement = json.loads(self.agreement_path.read_text()) if self.agreement_path.exists() else None
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            'schema': 'keddeh.pipeline-gate.v1', 'connected': True, 'generation': 0,
            'reason': 'existing owner-local pipeline'}
        if (type(self.data.get('connected')) is not bool or
                type(self.data.get('generation')) is not int or self.data['generation'] < 0):
            raise ValueError('invalid durable pipeline gate')

    def status(self):
        with self.lock:
            return dict(self.data)

    def configure(self, connected, reason):
        if type(connected) is not bool or type(reason) is not str or not 1 <= len(reason) <= 256:
            raise ValueError('boolean connected and bounded reason required')
        from .web4_runtime import write_json
        with self.lock:
            updated = {**self.data, 'connected': connected,
                       'generation': self.data['generation'] + 1, 'reason': reason}
            # The disconnect is acknowledged only after its durable fence is saved.
            write_json(self.path, updated)
            self.data = updated
            return dict(updated)

    @contextmanager
    def admission(self, generation=None):
        with self.lock:
            if not self.data['connected']:
                raise RuntimeError('pipeline disconnected; explicit owner reconnect required')
            if generation is not None and (type(generation) is not int or generation != self.data['generation']):
                raise ValueError('stale projection generation')
            # A committed in-flight operation may finish before disconnect returns.
            # No new admission can pass after a successful disconnect acknowledgement.
            yield

    def dispatch(self, operation, generation=None):
        with self.admission(generation):
            return operation()

    def terms(self):
        return {'version':'1.0', 'space':'owner', 'principal':'authenticated runtime owner',
                'services':['html-kex','html-carrier','resident-projection','r36-multiplexer'],
                'purpose':'Inspect owner runtime and explicitly execute owner-local commands',
                'execution_location':'current owner cloud host and browser',
                'data':'Owner telemetry and command receipts remain in private runtime state and owner VFS; no off-site transfer is enabled by this agreement',
                'retention':'Durable receipts and acceptance remain until owner-managed archival or deletion; no automatic expiry is claimed',
                'withdrawal':'Revoke projection permission or disconnect the pipeline; committed operations and receipts remain',
                'disconnect':'Stops new gateway and bilateral actor admission after acknowledgement; already admitted work may complete; does not sever the host network',
                'authority':'Owner-only token; customer registration does not grant runtime access',
                'offsite':'Unavailable until a specific host, transfer policy and scoped credentials are configured',
                'legal_status':'Operational permission record; no negotiated legal service contract or certification is implied'}

    def agreement_status(self):
        with self.lock:
            return {'terms':self.terms(), 'acceptance':dict(self.agreement) if self.agreement else None}

    def accept(self, version, accepted):
        if version != self.terms()['version'] or type(accepted) is not bool:
            raise ValueError('current agreement version and boolean accepted required')
        from datetime import datetime, timezone
        from .web4_runtime import write_json
        with self.lock:
            record={'version':version,'accepted':accepted,'space':'owner',
                    'principal':'authenticated runtime owner','recorded_at':datetime.now(timezone.utc).isoformat()}
            write_json(self.agreement_path,record)
            self.agreement=record
            return self.agreement_status()

    def require_agreement(self, context):
        if type(context) is not dict or context != {'space':'owner','agreement_version':self.terms()['version']}:
            raise ValueError('invalid projection user-space or agreement version')
        if not self.agreement or not self.agreement['accepted'] or self.agreement['version'] != context['agreement_version']:
            raise ValueError('projection service agreement acceptance required')

    def projection(self):
        return {'schema': 'keddeh.kex-projection-plan.v1', 'gate': self.status(), 'user_space':self.agreement_status(),
                'services': [
                    {'id':'html-kex', 'execution':'browser-local', 'route':'/terminal', 'actor_access':'fenced'},
                    {'id':'html-carrier', 'execution':'browser-local', 'route':'/carrier', 'actor_access':'fenced'},
                    {'id':'resident-projection', 'execution':'browser-local', 'route':'/research', 'actor_access':'fenced'},
                    {'id':'r36-multiplexer', 'execution':'owner-local', 'actor_access':'fenced'},
                    {'id':'offsite-observation', 'execution':'offsite-candidate', 'actor_access':'none',
                     'deployment':'not deployed; no remote endpoint or credentials configured'}],
                'disconnect_contract':'Durable command-admission fence; already committed work is retained. Not a host firewall or physical network disconnect.'}
