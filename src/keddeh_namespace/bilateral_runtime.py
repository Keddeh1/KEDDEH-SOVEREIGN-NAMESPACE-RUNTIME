"""Durable bidirectional workstation-to-R36 execution loop."""
import hashlib
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlencode

class BilateralRuntime:
    def __init__(self, controller):
        self.controller = controller
        self.path = controller.state / 'bilateral-runtime.json'
        self.lock = threading.RLock()
        self.next_due = 0
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            'schema': 'keddeh.bilateral-runtime.v1', 'enabled': False,
            'cycle': 0, 'pending': None, 'last': None, 'status': 'disabled'}

    def save(self):
        from .web4_runtime import write_json
        write_json(self.path, self.data)

    def configure(self, enabled):
        if type(enabled) is not bool: raise ValueError('enabled must be boolean')
        with self.lock:
            self.data['enabled'] = enabled
            self.data['status'] = 'waiting' if enabled else 'disabled'
            self.save()
            return dict(self.data)

    def tick(self):
        from .web4_runtime import http_json
        with self.lock:
            if not self.data['enabled'] or time.monotonic() < self.next_due: return
            self.next_due = time.monotonic() + 5
            try:
                observed = self.controller.status()
                if observed['healthy_nodes'] != 10:
                    raise RuntimeError('bilateral workstation feedback unavailable')
                if not all(s['alive'] for s in observed['services'].values()):
                    raise RuntimeError('owned actuator services unavailable')
                if self.data['pending'] is None:
                    # Both directions consume actual owner-runtime telemetry and the
                    # preceding actuator return; no fabricated resonance sample.
                    from .owner_kernel import DynamicHealingAgent, StochasticKuramotoPLL
                    import numpy as np
                    pll=StochasticKuramotoPLL(num_nodes=10)
                    saved=self.data.get('phase')
                    pll.theta=np.array(saved['theta'] if saved else [0.0]*10)
                    pll.omega=np.array(saved['omega'] if saved else [0.297]*10)
                    pll.sigma=0.0  # deployed model uses no fabricated stochastic noise
                    elapsed=saved['elapsed'] if saved else 0.0
                    for step in range(500):
                        coherence,phase=pll.step(elapsed+step*.01,(.297*(elapsed+step*.01))%(2*np.pi),True,0.0)
                    self.data['phase']={'theta':pll.theta.tolist(),'omega':pll.omega.tolist(),'elapsed':elapsed+5.0,'coherence':float(coherence),'aggregate':float(phase),'omega_star':0.297,'scope':'owner software PLL state'}
                    healer=DynamicHealingAgent()
                    previous = self.data['last']
                    returned = previous['actors'] if previous else []
                    domains=self.controller.domains.control({'operation':'status'})['domains'] if hasattr(self.controller,'domains') else []
                    if any(not d['live'].get('ownerAlive') for d in domains):raise RuntimeError('domain runtime feedback unavailable')
                    domain_feedback=[{'domain':d['topology']['id'],'epoch':d['live']['epoch'],'phase':d['live']['phase'],'owner_state_hashes':[w['stateHash'] for w in d['live']['workstations']]} for d in domains]
                    nodes = observed['nodes']; commands = []
                    for i, left in enumerate(nodes):
                        peer = nodes[i ^ 1]
                        material = json.dumps({'left': left, 'right': peer,
                                               'domain_feedback':domain_feedback,'returned': returned,'owner_phase':self.data['phase']['theta'][i],
                                               'owner_healing':healer.resolve_drift([float(not left['ok']),float(not peer['ok'])])}, sort_keys=True).encode()
                        nonce = int.from_bytes(hashlib.sha256(material).digest()[:4], 'little')
                        commands.append({'node_id': i + 1, 'nonce': nonce,
                                         'left_port': left['port'], 'right_port': peer['port']})
                    self.data['pending'] = {'cycle': self.data['cycle'] + 1,
                        'feedback': nodes,'domain_feedback':domain_feedback, 'commands': commands, 'actors': []}
                    self.save()  # Persist intent before any actuator side effect.
                pending = self.data['pending']
                for cmd in pending['commands'][len(pending['actors']):]:
                    query = urlencode({'node_id': cmd['node_id'], 'nonce': cmd['nonce'],
                                       'tenant_id': 'WEB4_BILATERAL'})
                    operation = lambda: http_json(self.controller.ports['http'], '/api/ingress?' + query, {})
                    actor = self.controller.pipeline.dispatch(operation) if hasattr(self.controller,'pipeline') else operation()
                    if actor.get('status') != 'ACTOR_COMMITTED':
                        raise RuntimeError('bilateral actuator did not commit')
                    pending['actors'].append(actor)
                    self.save()  # Interrupted retries use the same durable nonce.
                identity = 'bilateral-cycle:' + hashlib.sha256(json.dumps(pending,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                receipt = self.controller.receipt('bilateral.cycle', pending, request_id=identity)
                self.data.update(cycle=pending['cycle'], last={**pending, 'namespace_receipt': receipt},
                                 pending=None, status='operating', error=None)
                self.save()
            except Exception as exc:
                self.data.update(status='paused', error=type(exc).__name__ + ': ' + str(exc))
                self.save()  # Preserve unfinished prefix and retry on next cycle.
