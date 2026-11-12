"""Trusted 08F environment names pass through the actual resident launcher."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from keddeh_namespace.web4_runtime import write_json


def launcher_module():
    source = Path(__file__).resolve().parents[1] / 'scripts/launch_resident_controller.py'
    spec = importlib.util.spec_from_file_location('field_08f_resident_launcher_test', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class Field08FResidentBindingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name); self.root = self.directory / 'runtime'
        (self.root / 'state').mkdir(parents=True)
        (self.root / 'state/token').write_text('synthetic-owner-token')
        self.module = launcher_module()
        policy = patch.object(self.module, 'OWNER_RUNTIME_PARENT', self.directory)
        policy.start(); self.addCleanup(policy.stop)
        self.image = 'sha256:' + 'a' * 64
        self.manifest = self.directory / 'family.json'
        self.config = {'files': {}, 'ports': {'gateway': 18087},
                       'vfs': {'token_file': str(self.root / 'state/token')}}
        write_json(self.root / 'launch.json', self.config)
        write_json(self.directory / 'CONTROLLER_IMAGE.json', {'image_id': self.image})
        write_json(self.manifest, {'runtime_root': str(self.root), 'repository': 'owner/runtime'})
        self.current = False; self.current_env = []; self.calls = []

    def docker_run(self, *args):
        self.calls.append(args)
        if args[:2] == ('image', 'inspect'): return json.dumps([{'Id': self.image}])
        if args[:2] == ('ps', '-a'): return 'existing-id' if self.current else ''
        if args[0] == 'inspect':
            return json.dumps([{'Config': {'Labels': {'keddeh.owner-root': str(self.root)}, 'Env': self.current_env},
                                'Image': self.image, 'RestartCount': 0, 'State': {'Pid': 12345},
                                'HostConfig': {'RestartPolicy': {'Name': 'unless-stopped'}}}])
        return 'synthetic-container'

    def execute(self):
        def http(port, path, *args, **kwargs):
            if path == '/api/web4/control': raise ConnectionRefusedError('synthetic absent prior listener')
            return {'healthy_nodes': 10, 'boot_status': 'COMPLETED', 'source_digest': 'synthetic-source'}
        with patch.object(self.module, 'run', side_effect=self.docker_run), \
             patch.object(self.module, 'http_json', side_effect=http), \
             patch.object(self.module, 'LaunchController', return_value=SimpleNamespace(source_digest='synthetic-source')):
            return self.module.launch(self.manifest)

    def options(self, names):
        doc = json.loads(self.manifest.read_text())
        doc['field_08f'] = {'state_file': str(self.root / 'state/observed-enrollment.json'),
                            'pass_host_env_names': names}
        write_json(self.manifest, doc)

    def test_no_requested_binding_preserves_default_container_environment(self):
        self.execute()
        create = next(args for args in self.calls if args[0] == 'create')
        self.assertNotIn('--env', create)
        self.assertNotIn('field_08f', json.loads((self.root / 'launch.json').read_text()))

    def test_named_host_values_are_forwarded_without_appearing_in_argv_or_config(self):
        names = ['BRAINK_MCP_HMAC_KEY_HEX', 'BRAINK_MCP_DATA_DIR']
        self.options(names)
        key = 'ac' * 32; data = str(self.root / 'state/mcp')
        with patch.dict(os.environ, {'BRAINK_MCP_HMAC_KEY_HEX': key, 'BRAINK_MCP_DATA_DIR': data}):
            self.execute()
        create = next(args for args in self.calls if args[0] == 'create')
        forwarded = [create[i + 1] for i, value in enumerate(create) if value == '--env']
        self.assertEqual(forwarded, sorted(names)); self.assertNotIn(key, create); self.assertNotIn(data, create)
        container_name = create[create.index('--name') + 1]
        self.assertIn(('start', container_name), self.calls)
        config_text = (self.root / 'launch.json').read_text()
        self.assertNotIn(key, config_text); self.assertNotIn(data, config_text)
        self.assertEqual(json.loads(config_text)['field_08f']['pass_host_env_names'], names)

    def test_missing_or_unknown_binding_fails_before_configuration_or_container_change(self):
        before = (self.root / 'launch.json').read_bytes()
        for names in (['BRAINK_MCP_HMAC_KEY_HEX'], ['PATH']):
            self.options(names); self.calls.clear()
            with patch.dict(os.environ, {'BRAINK_MCP_HMAC_KEY_HEX': ''}):
                with self.assertRaises(ValueError): self.execute()
            self.assertEqual((self.root / 'launch.json').read_bytes(), before)
            self.assertFalse(self.calls)

    def test_existing_container_binding_mismatch_requires_reconciliation(self):
        self.current = True; self.options(['BRAINK_MCP_HMAC_KEY_HEX'])
        self.current_env = ['BRAINK_MCP_HMAC_KEY_HEX=' + 'bc' * 32]
        with patch.dict(os.environ, {'BRAINK_MCP_HMAC_KEY_HEX': 'ac' * 32}):
            with self.assertRaisesRegex(ValueError, 'different 08F host bindings'): self.execute()
        self.assertFalse(any(args[0] in ('stop', 'rm', 'create', 'start') for args in self.calls))

    def test_existing_container_matching_binding_is_reused(self):
        self.current = True; self.options(['BRAINK_MCP_HMAC_KEY_HEX'])
        key = 'ac' * 32; self.current_env = ['BRAINK_MCP_HMAC_KEY_HEX=' + key]
        with patch.dict(os.environ, {'BRAINK_MCP_HMAC_KEY_HEX': key}): self.execute()
        self.assertFalse(any(args[0] in ('stop', 'rm', 'create') for args in self.calls))
        self.assertTrue(any(args[0] == 'start' for args in self.calls))


if __name__ == '__main__':
    unittest.main(verbosity=2)
