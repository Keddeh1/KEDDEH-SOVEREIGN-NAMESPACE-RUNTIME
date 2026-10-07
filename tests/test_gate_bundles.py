import base64
import copy
import hashlib
import json
import unittest
from pathlib import Path
import test_runtime_foundation
from test_envelope import observation
from keddeh_namespace.bootstrap import verify_gate_bundles
from keddeh_namespace.envelope import canonical_bytes,envelope_digest
from keddeh_namespace.evidence import GATES
from keddeh_namespace.signatures import sign_observation,sign_assessment


class GateBundleTests(unittest.TestCase):
    setUp=test_runtime_foundation.RuntimeTests.setUp
    def bundle_fixture(self):
        now=1791331200  # synthetic fixed UTC clock, not a production receipt
        observations=[];parent=None
        ledger={'runtime_id':'node-1','generator_id':'generator-1','verifier_id':'verifier-1',
                'transaction':'synthetic gate suite','source_sha256':'a'*64,
                'stateRoot':observation()['stateRoot'],'phaseRoot':observation()['phaseRoot'],
                'parent_stateRoot':'d'*64,'receipts':{}}
        for gate in GATES:
            envelope=observation(parent);envelope.update(metric='gate:'+gate,transaction='synthetic '+gate,readback='fixture '+gate)
            signed=sign_observation(envelope,self.generator);parent=envelope_digest(envelope);observations.append(signed)
        config={'evidence_root':str(self.root),'trust_store':'trust.json','max_evidence_age_seconds':300,
                'trusted_heads':{'node-1':parent}}
        (self.root/'trust.json').write_bytes(canonical_bytes(self.trust))
        for gate,signed in zip(GATES,observations):
            envelope=signed['envelope'];artifact_path=gate+'.artifact';payload=('synthetic '+gate).encode()
            (self.root/artifact_path).write_bytes(payload)
            bundle={'signed':signed,'assessment':sign_assessment(signed,'verifier-1',self.verifier),
                    'history':observations,'artifact_path':artifact_path}
            ref=gate+'.json';(self.root/ref).write_bytes(canonical_bytes(bundle))
            ledger['receipts'][gate]={'status':'passed','artifact_sha256':hashlib.sha256(payload).hexdigest(),
                'command':envelope['transaction'],'readback':envelope['readback'],'signature_reference':ref,
                'observed_at':envelope['observed_at'],'assessor_id':'verifier-1',
                **{k:ledger[k] for k in ('runtime_id','source_sha256','stateRoot','phaseRoot')}}
        from datetime import datetime
        now=datetime.fromisoformat(observations[0]['envelope']['observed_at'].replace('Z','+00:00')).timestamp()
        return config,ledger,now

    def test_all_authenticated_gate_bundles(self):
        config,ledger,now=self.bundle_fixture()
        self.assertEqual(verify_gate_bundles(config,ledger,now=now)['authenticated_gates'],len(GATES))
        with self.assertRaises(ValueError): verify_gate_bundles(config,ledger,now=now+301)
        with self.assertRaises(ValueError): verify_gate_bundles(config,ledger,now=now-1)

    def test_artifact_history_and_assessment_tampering(self):
        config,ledger,now=self.bundle_fixture();gate=GATES[0]
        artifact=self.root/(gate+'.artifact');original=artifact.read_bytes();artifact.write_bytes(b'altered')
        with self.assertRaises(ValueError): verify_gate_bundles(config,ledger,now=now)
        artifact.write_bytes(original)
        path=self.root/(gate+'.json');original=path.read_bytes();bundle=json.loads(original)
        bundle['history']=bundle['history'][:-1];path.write_bytes(canonical_bytes(bundle))
        with self.assertRaises(ValueError): verify_gate_bundles(config,ledger,now=now)
        bundle=json.loads(original);bundle['assessment']['signature']='wrong';path.write_bytes(canonical_bytes(bundle))
        with self.assertRaises(ValueError): verify_gate_bundles(config,ledger,now=now)

    def test_path_escape_and_changed_gate_claim(self):
        config,ledger,now=self.bundle_fixture()
        altered=copy.deepcopy(ledger);altered['receipts'][GATES[0]]['signature_reference']='../escape'
        with self.assertRaises(ValueError): verify_gate_bundles(config,altered,now=now)
        altered=copy.deepcopy(ledger);altered['receipts'][GATES[0]]['readback']='claimed health'
        with self.assertRaises(ValueError): verify_gate_bundles(config,altered,now=now)
