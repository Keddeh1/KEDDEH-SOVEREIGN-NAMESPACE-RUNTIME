import copy
import unittest
from keddeh_namespace.envelope import (SCHEMA, canonical_bytes, content_root,
                                      envelope_digest, verify_chain)
from keddeh_namespace.native_labels import displacement, native_label, add_labels


def observation(parent=None):
    return dict(schema=SCHEMA, runtime_id='node-1', source_sha256='a'*64,
                generator_id='generator-1', observer_id='observer-1', metric='direct-readback',
                execution_plane='local-test', observed_at='2026-10-07T00:00:00.000000Z',
                transaction='synthetic test only', readback='fixture',
                stateRoot=content_root('state', {'generation':1}),
                phaseRoot=content_root('phase', {'generation':1}),
                parent_envelope_sha256=parent)


class EnvelopeTests(unittest.TestCase):
    def test_key_order_is_irrelevant(self):
        envelope = observation()
        self.assertEqual(envelope_digest(envelope), envelope_digest(dict(reversed(list(envelope.items())))))
        self.assertEqual(canonical_bytes({'b':2,'a':1}), b'{"a":1,"b":2}')

    def test_domain_separated_roots(self):
        self.assertNotEqual(content_root('state', {}), content_root('phase', {}))

    def test_full_chain(self):
        first = observation()
        second = observation(envelope_digest(first))
        head = envelope_digest(second)
        self.assertEqual(verify_chain([first, second], trusted_head=head), head)
        with self.assertRaises(ValueError):
            verify_chain([second], trusted_head=head)

    def test_genesis_tampering_rejected(self):
        first = observation()
        second = observation(envelope_digest(first))
        head = envelope_digest(second)
        first['readback'] = 'tampered'
        with self.assertRaises(ValueError):
            verify_chain([first, second], trusted_head=head)

    def test_truncation_rejected(self):
        first = observation()
        second = observation(envelope_digest(first))
        with self.assertRaises(ValueError):
            verify_chain([first], trusted_head=envelope_digest(second))

    def test_invalid_envelopes(self):
        for key, value in [('schema','v2'), ('source_sha256','bad'), ('observer_id',''),
                           ('observed_at','2026-10-07'), ('observed_at','2026-10-07T00:00:00+00:00'),
                           ('parent_envelope_sha256','bad')]:
            envelope=observation()
            envelope[key]=value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                envelope_digest(envelope)
        envelope=observation()
        envelope['extra']='not in schema'
        with self.assertRaises(ValueError): envelope_digest(envelope)

    def test_ambiguous_json_rejected(self):
        for value in (1.0, float('nan'), {1:'value'}, (1,2)):
            with self.assertRaises(ValueError): canonical_bytes(value)


class NativeLabelTests(unittest.TestCase):
    def test_bijection(self):
        for offset in range(-100,101):
            label=native_label(offset)
            self.assertNotIn(label,(0,-1))
            self.assertEqual(displacement(label),offset)

    def test_research_examples(self):
        self.assertEqual(native_label(0),1)
        self.assertEqual(add_labels(2,2),3)
        self.assertEqual(add_labels(3,-2),2)
        self.assertEqual(add_labels(2,-2),1)
        for label in (-3,-2,1,2,3): self.assertEqual(add_labels(1,label),label)

    def test_invalid_labels(self):
        for label in (0,-1,True,1.0,'1',None):
            with self.assertRaises(ValueError): displacement(label)
        for offset in (True,1.0,'0',None):
            with self.assertRaises(ValueError): native_label(offset)
