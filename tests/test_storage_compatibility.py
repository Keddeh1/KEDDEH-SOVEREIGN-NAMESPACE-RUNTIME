"""Retain the original configuration and storage policy without new gates."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from keddeh_namespace.bootstrap import preflight, storage_requirements
from keddeh_namespace.verify_vfs import verify_volume

class StorageCompatibilityTests(unittest.TestCase):
    def original(self):
        return json.loads((Path(__file__).parent/'fixtures/config.example.9bd3152.json').read_text())

    def test_original_retained_config_needs_no_new_fields(self):
        config=self.original()
        for value,prefix,quota in [(n,'vfs',10**13) for n in config['nodes']]+[(config,'archive',10**14)]:
            requirements=storage_requirements(value,prefix,quota)
            self.assertEqual(requirements['required_bytes'],value[prefix+'_required_bytes'])
            self.assertIsNone(requirements['reserve_bytes'])
            with tempfile.TemporaryDirectory() as root:
                stats=SimpleNamespace(f_frsize=1,f_blocks=10**14,f_bavail=8192)
                with patch('os.statvfs',return_value=stats):
                    result=verify_volume(root,require_mount=False,**requirements)
            self.assertEqual(result['fsync_readback'],'passed')
        # The retained example remains intentionally nonproduction, as before.
        with self.assertRaisesRegex(ValueError,'explicit production configuration'):preflight(config,{})

    def test_preflight_accepts_original_storage_fields_without_reserve(self):
        config=copy.deepcopy(self.original())
        with tempfile.TemporaryDirectory() as root:
            config.update(production=True,evidence_root=root,trust_store='test',trusted_heads={},dnskey_sha256='test')
            for i,node in enumerate(config['nodes']):
                mount=Path(root)/str(i);mount.mkdir();node['vfs_mount']=str(mount)
            archive=Path(root)/'archive';archive.mkdir();config['archive_mount']=str(archive)
            # Isolate storage integration from signed evidence, DNS and actual mount topology.
            with patch('keddeh_namespace.bootstrap.validate_nodes',return_value=[('primary','test1'),('secondary','test2')]),patch('keddeh_namespace.bootstrap.verify_gate_bundles',return_value={'status':'test-only'}),patch('keddeh_namespace.bootstrap.authority_probe',return_value={'soa_serial':1}),patch('os.path.ismount',return_value=True),patch('os.statvfs',return_value=SimpleNamespace(f_frsize=1,f_blocks=10**14,f_bavail=8192)):
                result=preflight(config,{})
            self.assertEqual(result['status'],'preflight_passed_not_deployed')
            self.assertEqual([v['required_bytes'] for v in result['volumes']],[10**13,10**13,10**14])
            self.assertTrue(all(v['reserve_bytes'] is None for v in result['volumes']))

    def test_absent_physical_policy_does_not_allocate_logical_capacity(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('os.statvfs',return_value=SimpleNamespace(f_frsize=1,f_blocks=16384,f_bavail=8192)):
                result=verify_volume(root,require_mount=False,**storage_requirements({},'vfs',10**13))
            self.assertEqual(result['logical_quota_bytes'],10**13)
            self.assertIsNone(result['required_bytes']);self.assertIsNone(result['reserve_bytes'])
            self.assertEqual(result['fsync_readback'],'passed')

    def test_legacy_probe_behavior_without_reserve_is_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            # Original code reports f_bavail but relies on the real write/readback.
            with patch('os.statvfs',return_value=SimpleNamespace(f_frsize=1,f_blocks=16384,f_bavail=0)):
                self.assertEqual(verify_volume(root,required_bytes=1,require_mount=False)['fsync_readback'],'passed')
                with self.assertRaisesRegex(ValueError,'reserve'):
                    verify_volume(root,required_bytes=1,reserve_bytes=0,require_mount=False)

    def test_conflicting_or_invalid_explicit_policy_rejected(self):
        for config in ({'vfs_required_bytes':8192,'vfs_backing_required_bytes':4096},
                       {'vfs_backing_required_bytes':False}, {'vfs_backing_reserve_bytes':-1}):
            with self.assertRaises(ValueError):storage_requirements(config,'vfs',10**13)
        self.assertEqual(storage_requirements({'vfs_required_bytes':8192,'vfs_backing_required_bytes':None},'vfs',10**13)['required_bytes'],8192)
