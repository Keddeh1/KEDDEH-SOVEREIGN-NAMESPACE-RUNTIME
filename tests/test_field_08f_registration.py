"""08F registration gates exercised against the actual LaunchController."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import test_web4_runtime
from keddeh_namespace import field_08f_registration as field
from keddeh_namespace.web4_runtime import LaunchController, write_json


class Field08FRegistrationTests(unittest.TestCase):
    setUp = test_web4_runtime.Web4RuntimeTests.setUp
    fixture_controller = test_web4_runtime.Web4RuntimeTests.fixture_controller

    def fixture(self):
        c = self.fixture_controller()
        self.addCleanup(c.close)
        self.entry = self.root / field.ENTRY_RELATIVE
        self.entry.parent.mkdir(parents=True, exist_ok=True)
        # A synthetic source pin exercises the exact admission mechanism without
        # copying the owner's private package or running its broker loop.
        self.entry.write_text("print('registration fixture; no broker execution')\n")
        self.pin = hashlib.sha256(self.entry.read_bytes()).hexdigest()
        pin = patch.object(field, 'ENTRY_SHA256', self.pin); pin.start(); self.addCleanup(pin.stop)
        host = patch.object(field, 'HOST_ID', c.host_id); host.start(); self.addCleanup(host.stop)
        workspace = self.root / 'state/08f-volume'; workspace.mkdir(exist_ok=True)
        self.state = self.root / 'state/08f-enrollment.json'
        self.enrollment = {
            'broker': 'https://keddeh.com', 'nodeId': 'synthetic-node',
            'credential': 'synthetic-enrollment-credential', 'nextSequence': 7,
            'name': 'test worker', 'workspace': str(workspace),
        }
        write_json(self.state, self.enrollment)
        c.config['files'][field.ENTRY_RELATIVE] = self.pin
        c.config['field_08f'] = {'state_file': str(self.state)}
        return c

    def register(self, c):
        return field.register_configured_08f(c)

    def test_registration_retains_enrollment_and_existing_specs_without_spawning(self):
        c = self.fixture()
        prior = {'worker': ([sys.executable, '-c', 'pass'], str(self.root), None, False)}
        c.specs.update(prior)
        before = self.state.read_bytes()
        with patch.object(c, 'spawn') as spawn, patch.object(c, 'activate_host_binding') as activate:
            result = self.register(c)
        spawn.assert_not_called(); activate.assert_not_called()
        self.assertEqual(before, self.state.read_bytes())
        self.assertEqual(prior['worker'], c.specs['worker'])
        self.assertEqual(c.specs[field.SERVICE_NAME],
            ([sys.executable, str(self.entry), '--state-file', str(self.state), '--poll-interval', '5'],
             str(self.entry.parent), None, False))
        self.assertEqual(set(c.processes), set())
        self.assertFalse(result['process_started']); self.assertFalse(result['pairing_performed'])
        self.assertNotIn('credential', json.dumps(result))

    def test_absent_configuration_does_not_register(self):
        c = self.fixture(); del c.config['field_08f']
        self.assertIsNone(self.register(c)); self.assertNotIn(field.SERVICE_NAME, c.specs)

    def test_null_incomplete_and_unknown_configuration_reject(self):
        c = self.fixture()
        for options in (None, {}, {'state_file': str(self.state), 'command': 'not accepted'}):
            with self.subTest(options=options):
                c.config['field_08f'] = options
                with self.assertRaises(ValueError): self.register(c)
                self.assertNotIn(field.SERVICE_NAME, c.specs)

    def test_foreign_host_rejects(self):
        c = self.fixture(); c.host_id = 'foreign'
        with self.assertRaisesRegex(ValueError, 'host identity'): self.register(c)

    def test_missing_or_wrong_manifest_pin_rejects(self):
        c = self.fixture()
        for value in (None, '0' * 64):
            with self.subTest(value=value):
                c.config['files'][field.ENTRY_RELATIVE] = value
                with self.assertRaisesRegex(ValueError, 'launch manifest'): self.register(c)

    def test_changed_source_rejects_before_registration(self):
        c = self.fixture(); self.entry.write_text('modified')
        with self.assertRaisesRegex(ValueError, 'source digest'): self.register(c)
        self.assertNotIn(field.SERVICE_NAME, c.specs)

    def test_source_symlink_rejects_even_with_matching_bytes(self):
        c = self.fixture(); data = self.entry.read_bytes()
        outside = self.root / 'retained.py'; outside.write_bytes(data)
        self.entry.unlink(); self.entry.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'admitted packages'): self.register(c)

    def test_state_must_be_existing_absolute_file(self):
        c = self.fixture()
        for value in ('state/08f-enrollment.json', '', str(self.root / 'missing.json'), str(self.root)):
            with self.subTest(value=value):
                c.config['field_08f']['state_file'] = value
                with self.assertRaises((ValueError, FileNotFoundError)): self.register(c)

    def test_state_symlink_and_standard_agent_hardlink_reject(self):
        c = self.fixture(); alias = self.root / 'state/alias.json'; alias.symlink_to(self.state)
        c.config['field_08f']['state_file'] = str(alias)
        with self.assertRaisesRegex(ValueError, 'symlink'): self.register(c)
        c.config['field_08f']['state_file'] = str(self.state)
        os.link(self.state, self.root / 'state/agent.json')
        with self.assertRaisesRegex(ValueError, 'standard agent'): self.register(c)

    def test_enrollment_inside_readonly_packages_rejects(self):
        c = self.fixture(); staged = self.entry.parent / 'state.json'; staged.write_bytes(self.state.read_bytes())
        c.config['field_08f']['state_file'] = str(staged)
        with self.assertRaisesRegex(ValueError, 'mutable enrollment'): self.register(c)

    def test_incomplete_enrollment_and_invalid_sequence_reject(self):
        c = self.fixture()
        for changed in ({'credential': ''}, {'nextSequence': True}, {'nextSequence': 0}, {'nodeId': None}):
            with self.subTest(changed=changed):
                write_json(self.state, {**self.enrollment, **changed})
                with self.assertRaises(ValueError): self.register(c)

    def test_incompatible_broker_and_workspace_reject(self):
        c = self.fixture()
        for changed in ({'broker': 'http://127.0.0.1:18777'}, {'broker': 'https://user:pass@keddeh.com'},
                        {'broker': 'https://keddeh.com?token=untrusted'}, {'broker': 'https://keddeh.com/not-an-origin'}, {'workspace': 'relative'},
                        {'workspace': str(self.root / 'does-not-exist')}):
            with self.subTest(changed=changed):
                write_json(self.state, {**self.enrollment, **changed})
                with self.assertRaises(ValueError): self.register(c)

    def test_state_collision_with_other_service_rejects(self):
        c = self.fixture()
        alias = self.root / 'state/other.json'; os.link(self.state, alias)
        c.specs['existing-worker'] = ([sys.executable, 'worker.py', '--state-file', 'state/other.json'], str(self.root), None, False)
        with self.assertRaisesRegex(ValueError, 'another service'): self.register(c)

    def test_conflicting_owned_specification_and_unowned_process_reject(self):
        c = self.fixture()
        c.specs[field.SERVICE_NAME] = (['foreign'], str(self.root), None, False)
        with self.assertRaisesRegex(ValueError, 'specification collision'): self.register(c)
        del c.specs[field.SERVICE_NAME]
        c.processes[field.SERVICE_NAME] = Mock()
        with self.assertRaisesRegex(ValueError, 'no owned specification'): self.register(c)
        c.processes.clear()

    def test_exact_registration_retry_is_observational(self):
        c = self.fixture(); first = self.register(c)
        snapshot = copy.deepcopy(c.specs); state = self.state.read_bytes()
        self.assertEqual(first, self.register(c)); self.assertEqual(snapshot, c.specs)
        self.assertEqual(state, self.state.read_bytes())

    def test_host_environment_requires_explicit_allowlisted_names(self):
        c = self.fixture()
        values = {'BRAINK_MCP_HMAC_KEY_HEX': 'a1' * 32, 'KEX_RECEIPT_HMAC_KEY_HEX': 'b2' * 32,
                  'BRAINK_MCP_DATA_DIR': str(self.root / 'state/mcp'), 'UNRELATED_SECRET': 'retain-private'}
        with patch.dict(os.environ, values):
            self.register(c); self.assertIsNone(c.specs[field.SERVICE_NAME][2])
            del c.specs[field.SERVICE_NAME]
            c.config['field_08f']['pass_host_env_names'] = ['BRAINK_MCP_HMAC_KEY_HEX', 'BRAINK_MCP_DATA_DIR']
            result = self.register(c)
            self.assertEqual(c.specs[field.SERVICE_NAME][2], {k: values[k] for k in c.config['field_08f']['pass_host_env_names']})
            self.assertNotIn(values['BRAINK_MCP_HMAC_KEY_HEX'], json.dumps(result))
            (c.state / 'pairing-code').write_text('test-only')
            self.assertNotIn('BRAINK_MCP_HMAC_KEY_HEX', c.env())

    def test_missing_invalid_or_unknown_environment_rejects(self):
        c = self.fixture()
        for names, env in [(['UNRELATED_SECRET'], {}), (['PATH'], {}),
                           (['BRAINK_MCP_HMAC_KEY_HEX'] * 2, {}),
                           (['BRAINK_MCP_HMAC_KEY_HEX'], {'BRAINK_MCP_HMAC_KEY_HEX': ''}),
                           (['BRAINK_MCP_HMAC_KEY_HEX'], {'BRAINK_MCP_HMAC_KEY_HEX': 'bad'}),
                           (['BRAINK_MCP_DATA_DIR'], {'BRAINK_MCP_DATA_DIR': 'relative'})]:
            with self.subTest(names=names), patch.dict(os.environ, env):
                c.config['field_08f']['pass_host_env_names'] = names
                with self.assertRaises(ValueError): self.register(c)
                self.assertNotIn(field.SERVICE_NAME, c.specs)

    def test_actual_start_rejects_invalid_registration_before_activation(self):
        c = self.fixture(); c.config['field_08f'] = {}
        with patch.object(c, 'activate_host_binding') as activation, patch.object(c, 'spawn') as spawn:
            with self.assertRaises(ValueError): c.start()
        activation.assert_not_called(); spawn.assert_not_called()

    def test_actual_start_preserves_fifteen_services_and_never_starts_08f(self):
        c = self.fixture()
        c.ports.update(gateway=18087, network=18086, http=4055, broker=18777,
                       mesh=list(range(19100, 19110)))
        c.config['packages'] = {'network': str(self.root / 'packages/network'),
                                'http': str(self.root / 'packages/http')}
        nodes = [{'id': str(i), 'port': port, 'candidates': ['fixture.js']}
                 for i, port in enumerate(c.ports['mesh'])]
        script = c.estate / 'mesh/nodes/fixture.js'; script.parent.mkdir(parents=True); script.write_text('fixture')
        write_json(c.estate / 'mesh/registry.json', {'nodes': nodes})
        options = c.config.pop('field_08f')
        calls = []
        def register_only(name, argv, cwd, extra=None, stdio=False):
            calls.append(name); c.specs[name] = (argv, str(cwd), extra, stdio)
        domains = {node['port']: node['id'] for node in nodes}
        with patch('keddeh_namespace.web4_runtime.socket.socket'), \
             patch.object(c, 'spawn', side_effect=register_only), \
             patch.object(c, 'wait_health', side_effect=lambda name, port, path: {'domain': domains.get(port)}), \
             patch.object(c, 'pair_agent'):
            c.start(); existing = copy.deepcopy(c.specs)
            self.assertEqual(len(existing), 15)
            c.config['field_08f'] = options; calls.clear()
            def activated_after_registration():
                self.assertIn(field.SERVICE_NAME, c.specs)
            with patch.object(c, 'activate_host_binding', side_effect=activated_after_registration): c.start()
        self.assertEqual({k: c.specs[k] for k in existing}, existing)
        self.assertEqual(len(c.specs), 16); self.assertNotIn(field.SERVICE_NAME, calls)
        self.assertFalse(c.service_readback(field.SERVICE_NAME)['alive'])
        self.assertIsNone(c.service_readback(field.SERVICE_NAME)['pid'])

    def test_registration_only_does_not_auto_resume_after_reconstruction(self):
        c = self.fixture(); self.register(c)
        with patch.object(c, 'spawn') as spawn, patch.object(c, 'restart') as restart:
            c.recover_services()
        spawn.assert_not_called(); restart.assert_not_called()
        self.assertEqual(c.service_readback(field.SERVICE_NAME)['state'], 'not started')


if __name__ == '__main__':
    unittest.main(verbosity=2)
