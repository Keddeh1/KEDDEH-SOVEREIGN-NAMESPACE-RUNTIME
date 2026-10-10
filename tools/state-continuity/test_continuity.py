import concurrent.futures, tempfile, unittest, pathlib
from continuity import ContinuityVFS
from keddeh_namespace.logical_vfs import Conflict

class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.c=ContinuityVFS(self.temp.name)
        self.identity='kex/owner/state';self.payload=b'{"q":0,"active":true,"frame":"owner"}'
        self.event=self.c.vfs.write(self.identity,self.payload,expected_version=0)
    def tearDown(self):self.temp.cleanup()
    def test_zero_record_retained(self):
        r=self.c.observe(self.identity);self.assertEqual(r.status,'AVAILABLE');self.assertEqual(r.payload,self.payload)
    def test_absent_is_distinct(self):self.assertEqual(self.c.observe('kex/owner/other').status,'ABSENT')
    def test_carrier_loss_restart_and_verified_recovery(self):
        (self.c.vfs.objects/self.event['digest']).unlink();c=ContinuityVFS(self.temp.name)
        r=c.observe(self.identity);self.assertEqual(r.status,'REHYDRATABLE');self.assertEqual(r.digest,self.event['digest'])
        after=c.recover(self.identity,self.payload,expected_version=1)
        self.assertEqual(after.payload,self.payload);self.assertEqual(after.receipt,self.event['receipt'])
        self.assertEqual(len(c.vfs.history()),1)
    def test_wrong_recovery_never_succeeds(self):
        (self.c.vfs.objects/self.event['digest']).unlink()
        with self.assertRaises(ValueError):self.c.recover(self.identity,b'wrong',expected_version=1)
        self.assertEqual(self.c.observe(self.identity).status,'REHYDRATABLE')
    def test_corrupt_object_is_not_accepted_or_overwritten(self):
        p=self.c.vfs.objects/self.event['digest'];p.chmod(0o600);p.write_bytes(b'corrupt')
        self.assertEqual(self.c.observe(self.identity).status,'CARRIER_REJECTED')
        with self.assertRaises(ValueError):self.c.recover(self.identity,self.payload,expected_version=1)
        self.assertEqual(p.read_bytes(),b'corrupt')
    def test_head_tamper_rejected(self):
        with self.c.vfs.connect() as db:db.execute('UPDATE heads SET digest=?',('0'*64,))
        self.assertEqual(self.c.observe(self.identity).status,'METADATA_REJECTED')
    def test_event_tamper_rejected(self):
        with self.c.vfs.connect() as db:db.execute('UPDATE events SET parent=?',('tamper',))
        self.assertEqual(self.c.observe(self.identity).status,'METADATA_REJECTED')
    def test_version_conflict(self):
        with self.assertRaises(Conflict):self.c.recover(self.identity,self.payload,expected_version=0)
    def test_concurrent_mutation_one_commit(self):
        def write(i):
            try:self.c.vfs.write(self.identity,str(i).encode(),expected_version=1);return 'committed'
            except Conflict:return 'conflict'
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(write,range(8)))
        self.assertEqual(out.count('committed'),1);self.assertEqual(out.count('conflict'),7)
        self.assertEqual(len(self.c.vfs.history()),2)
    def test_empty_bytes_are_available(self):
        self.c.vfs.write('empty',b'',expected_version=0);self.assertEqual(self.c.observe('empty').payload,b'')
    def test_invalid_identity(self):
        for p in ['../escape','/absolute','a//b']:
            with self.assertRaises(ValueError):self.c.observe(p)
    def test_metadata_database_failure_propagates(self):
        with self.c.vfs.connect() as db:db.execute('DROP TABLE heads')
        with self.assertRaises(Exception):self.c.observe(self.identity)

if __name__=='__main__':unittest.main()
