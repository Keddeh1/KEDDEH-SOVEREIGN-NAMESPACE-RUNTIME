import copy
import unittest
from keddeh_namespace.evidence import GATES, validate


def fixture():
    ledger = dict(runtime_id='test-only', generator_id='generator', verifier_id='assessor',
                  transaction='test command', source_sha256='a'*64,
                  stateRoot='b'*64, phaseRoot='c'*64, parent_stateRoot='d'*64)
    ledger['receipts'] = {gate: dict(
        status='passed', artifact_sha256='e'*64, command='test-only',
        readback='synthetic test fixture', signature_reference='test-only',
        observed_at='2026-10-07T00:00:00+00:00', assessor_id='assessor',
        **{key: ledger[key] for key in ('runtime_id','source_sha256','stateRoot','phaseRoot')}
    ) for gate in GATES}
    return ledger


class EvidenceTests(unittest.TestCase):
    def test_complete_synthetic_structure(self):
        self.assertEqual(validate(fixture()), [])

    def test_missing_gates_fail_closed(self):
        for gate in GATES:
            with self.subTest(gate=gate):
                ledger = fixture()
                del ledger['receipts'][gate]
                self.assertTrue(validate(ledger))

    def test_self_assessment_rejected(self):
        ledger = fixture()
        ledger['verifier_id'] = ledger['generator_id']
        self.assertTrue(validate(ledger))

    def test_receipt_cannot_bind_another_generation(self):
        ledger = fixture()
        ledger['receipts']['dnssec']['stateRoot'] = 'f'*64
        self.assertTrue(validate(ledger))

    def test_separate_roots_required(self):
        ledger = fixture()
        ledger['phaseRoot'] = ledger['stateRoot']
        self.assertTrue(validate(ledger))

    def test_unexecuted_checks_rejected(self):
        for status in ('pending', 'skipped', 'failed', True):
            ledger = fixture()
            ledger['receipts']['dnssec']['status'] = status
            self.assertTrue(validate(ledger))

    def test_bad_input(self):
        for value in (None, [], {}, 'claimed complete'):
            self.assertTrue(validate(value))

    def test_malformed_receipt_fields(self):
        for field, value in [('observed_at', '2026-10-07'), ('artifact_sha256', 'invalid'),
                             ('signature_reference', ''), ('command', ''), ('readback', '')]:
            ledger = copy.deepcopy(fixture())
            ledger['receipts']['dnssec'][field] = value
            self.assertTrue(validate(ledger))
