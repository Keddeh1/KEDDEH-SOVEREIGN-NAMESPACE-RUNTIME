import hashlib
import tempfile
import unittest
from pathlib import Path
from keddeh_namespace.source_custody import verify_archive


class SourceCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'archive.bin'
        self.path.write_bytes(b'exact source fixture')
        self.expected = {'bytes': self.path.stat().st_size,
                         'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest()}

    def test_exact_match(self):
        self.assertEqual(verify_archive(self.path, self.expected)['status'], 'exact_bytes_verified')

    def test_same_size_corruption(self):
        self.path.write_bytes(b'Exact source fixture')
        with self.assertRaises(ValueError):
            verify_archive(self.path, self.expected)

    def test_truncated_archive(self):
        self.path.write_bytes(b'exact')
        with self.assertRaises(ValueError):
            verify_archive(self.path, self.expected)

    def test_symlink_rejected(self):
        link = self.path.with_name('link')
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            verify_archive(link, self.expected)

    def test_directory_rejected(self):
        with self.assertRaises(ValueError):
            verify_archive(self.path.parent, self.expected)

    def test_invalid_expectations(self):
        for expectation in (None, {}, {'bytes':True,'sha256':'a'*64},
                            {'bytes':1,'sha256':'bad'}):
            with self.subTest(expectation=expectation), self.assertRaises(ValueError):
                verify_archive(self.path, expectation)
