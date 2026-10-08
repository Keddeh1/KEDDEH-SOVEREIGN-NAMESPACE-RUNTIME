import unittest,tempfile,pathlib,json,os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from signed_boot import make_manifest,verify,activate,ledger
class SignedBootTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=pathlib.Path(self.temp.name);self.slot=self.base/'slot';self.slot.mkdir();(self.slot/'program.py').write_text('VALUE=1\n');(self.slot/'config.json').write_text('{}');self.key=Ed25519PrivateKey.generate();self.public=self.key.public_key().public_bytes_raw();self.signed=make_manifest(self.slot,'A',2,'program.py',self.key)
 def tearDown(self):self.temp.cleanup()
 def test_valid_full_manifest(self):self.assertEqual(verify(self.slot,self.signed,self.public)['state'],'verified')
 def test_modified_content(self):
  (self.slot/'program.py').write_text('VALUE=9\n')
  with self.assertRaises(ValueError):verify(self.slot,self.signed,self.public)
 def test_extra_binary(self):
  (self.slot/'payload.bin').write_bytes(b'x')
  with self.assertRaises(ValueError):verify(self.slot,self.signed,self.public)
 def test_missing_file(self):
  (self.slot/'config.json').unlink()
  with self.assertRaises(ValueError):verify(self.slot,self.signed,self.public)
 def test_empty_directory(self):
  for p in self.slot.iterdir():p.unlink()
  with self.assertRaises(ValueError):verify(self.slot,self.signed,self.public)
 def test_wrong_key_and_mock_signature(self):
  with self.assertRaises(Exception):verify(self.slot,self.signed,Ed25519PrivateKey.generate().public_key().public_bytes_raw())
  self.signed['signature']='MOCK_FROST_SIG_A'
  with self.assertRaises(Exception):verify(self.slot,self.signed,self.public)
 def test_rollback_and_slot_confusion(self):
  with self.assertRaises(ValueError):verify(self.slot,self.signed,self.public,minimum_version=3)
  with self.assertRaises(ValueError):verify(self.slot,self.signed,self.public,expected_slot='B')
 def test_symlink(self):
  (self.slot/'link').symlink_to(self.slot/'program.py')
  with self.assertRaises(ValueError):verify(self.slot,self.signed,self.public)
 def test_activation_and_rollback(self):
  state=self.base/'boot.json';r=activate(self.slot,self.signed,self.public,state,'A');self.assertEqual(json.loads(state.read_text())['minimumVersion'],2);self.assertEqual(r['state'],'verified');old=make_manifest(self.slot,'A',1,'program.py',self.key)
  with self.assertRaises(ValueError):activate(self.slot,old,self.public,state,'A')
 def test_ledger_history_is_not_overwritten(self):
  p=self.base/'history';a=ledger(p,{'action':'same','result':'one'});b=ledger(p,{'action':'same','result':'two'});self.assertEqual(b['previous'],a['sha256']);self.assertEqual(len(p.read_text().splitlines()),2);p.write_text(p.read_text().replace('one','bad'))
  with self.assertRaises(ValueError):ledger(p,{'action':'next'})
if __name__=='__main__':unittest.main()
