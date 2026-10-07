import hashlib
import io
import json
import os
import stat
import tarfile
import zipfile
from pathlib import Path
import unittest
import test_runtime_foundation
from keddeh_namespace.hydrate_service_volumes import hydrate,verify_admission
from keddeh_namespace.registry_service import Registry
from keddeh_namespace.envelope import envelope_digest,canonical_bytes
from keddeh_namespace.propagation_runtime import archive_registry,restore_registry,backward_lineage
from keddeh_namespace.logical_vfs import LogicalVFS


class AdmissionPropagationTests(unittest.TestCase):
    setUp = test_runtime_foundation.RuntimeTests.setUp
    signed = test_runtime_foundation.RuntimeTests.signed
    def tearDown(self):
        for path in self.root.rglob('*'):
            if path.is_dir(): path.chmod(0o755)
            elif not path.is_symlink(): path.chmod(0o644)

    def make_zip(self,entries):
        path=self.root/'source.zip'
        with zipfile.ZipFile(path,'w') as archive:
            for name,data in entries: archive.writestr(name,data)
        payload=path.read_bytes()
        return path,{'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}

    def test_archive_admission_repeat_and_corrupt_readback(self):
        path,expected=self.make_zip([('service/main.txt',b'exact data')])
        root=self.root/'volumes'
        first=hydrate(path,root,expected)
        self.assertEqual(hydrate(path,root,expected),first)
        target=root/expected['sha256']/'service/main.txt'
        target.chmod(0o644);target.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): hydrate(path,root,expected)

    def test_archive_traversal_duplicates_and_bounds(self):
        for entries in [[('../escape',b'x')],[('/absolute',b'x')],[('a',b'x'),('a',b'y')],[('.keddeh-admission.json',b'x')]]:
            path,expected=self.make_zip(entries)
            with self.assertRaises(ValueError): hydrate(path,self.root/'volumes',expected)
        path,expected=self.make_zip([('file',b'payload')])
        with self.assertRaises(ValueError): hydrate(path,self.root/'volumes',expected,max_bytes=1)
        wrong=dict(expected,sha256='a'*64)
        with self.assertRaises(ValueError): hydrate(path,self.root/'volumes',wrong)

    def test_archive_links_and_device_rejected(self):
        path=self.root/'bad.tar'
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.CHRTYPE):
            with tarfile.open(path,'w') as archive:
                info=tarfile.TarInfo('link');info.type=kind;info.linkname='/outside';archive.addfile(info)
            payload=path.read_bytes();expected={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
            with self.assertRaises(ValueError): hydrate(path,self.root/'volumes',expected)
        path=self.root/'bad.zip'
        with zipfile.ZipFile(path,'w') as archive:
            info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
            archive.writestr(info,'/outside')
        payload=path.read_bytes();expected={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
        with self.assertRaises(ValueError): hydrate(path,self.root/'volumes',expected)

    def test_archive_restore_and_backward_source_lineage(self):
        registry=Registry(self.root/'registry',self.trust)
        first=self.signed()
        registry.commit(dict(desired_state={'generation':1},phase_state={'generation':1},request_id='1',path='state',expected_version=0,signed=first))
        second=self.signed(envelope_digest(first['envelope']))
        registry.commit(dict(desired_state={'generation':1},phase_state={'generation':1},request_id='2',path='state',expected_version=1,signed=second))
        receipt=archive_registry(registry,self.root/'archive')
        restored=restore_registry(self.root/'archive',receipt['archive_manifest_sha256'],self.root/'restored',self.trust)
        self.assertEqual(registry.replay(),restored.replay())
        self.assertEqual(len(backward_lineage(restored,'state')),2)
        self.assertEqual(backward_lineage(restored,'state')[-1]['source_sha256'],'a'*64)

    def test_corrupt_archive_rejected_before_restore(self):
        registry=Registry(self.root/'registry',self.trust)
        registry.commit(dict(desired_state={'generation':1},phase_state={'generation':1},request_id='1',path='state',expected_version=0,signed=self.signed()))
        receipt=archive_registry(registry,self.root/'archive')
        archive=LogicalVFS(self.root/'archive');target=archive.objects/registry.replay()[0]['digest']
        target.chmod(0o644);target.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): restore_registry(self.root/'archive',receipt['archive_manifest_sha256'],self.root/'restored',self.trust)
        self.assertEqual(Registry(self.root/'restored',self.trust).replay(),[])

    def test_divergent_manifest_head_rejected_before_restore(self):
        registry=Registry(self.root/'registry',self.trust)
        registry.commit(dict(desired_state={'generation':1},phase_state={'generation':1},request_id='1',path='state',expected_version=0,signed=self.signed()))
        receipt=archive_registry(registry,self.root/'archive');archive=LogicalVFS(self.root/'archive')
        manifest=json.loads(archive.read_object(receipt['archive_manifest_sha256']))
        manifest['journal_head']='f'*64
        digest=archive.put_object(canonical_bytes(manifest))
        with self.assertRaises(ValueError): restore_registry(self.root/'archive',digest,self.root/'restored',self.trust)
        self.assertEqual(Registry(self.root/'restored',self.trust).replay(),[])

    def test_independent_assessment_survives_archive_restore(self):
        from keddeh_namespace.signatures import sign_assessment
        registry=Registry(self.root/'registry',self.trust);signed=self.signed()
        registry.commit(dict(desired_state={'generation':1},phase_state={'generation':1},request_id='1',path='state',expected_version=0,signed=signed))
        registry.assess(sign_assessment(signed,'verifier-1',self.verifier))
        receipt=archive_registry(registry,self.root/'archive')
        restored=restore_registry(self.root/'archive',receipt['archive_manifest_sha256'],self.root/'restored',self.trust)
        self.assertEqual(len(restored.replay()),1)
        with restored.vfs.connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM assessments').fetchone()[0],1)

    def test_forged_receipt_cannot_change_existing_source_admission(self):
        path,expected=self.make_zip([('service/main.txt',b'exact data')])
        root=self.root/'volumes';hydrate(path,root,expected)
        target=root/expected['sha256']/'service/main.txt';target.chmod(0o644);target.write_bytes(b'forged')
        receipt_path=root/expected['sha256']/'.keddeh-admission.json';receipt_path.chmod(0o644)
        receipt=json.loads(receipt_path.read_text())
        receipt['files']['service/main.txt']={'bytes':6,'sha256':hashlib.sha256(b'forged').hexdigest(),'mode':0o644}
        receipt_path.write_bytes(canonical_bytes(receipt))
        with self.assertRaises(ValueError): hydrate(path,root,expected)
