import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import unittest

from keddeh_namespace._web4_exec import file_policy


class NativeFilePolicyTests(unittest.TestCase):
    wrapper = Path(__file__).resolve().parents[1] / 'src/keddeh_namespace/_web4_exec.py'

    def child(self, command, cwd=None, inherited_limit=None):
        def limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (inherited_limit, inherited_limit))
        return subprocess.run([sys.executable, str(self.wrapper), *command], cwd=cwd,
                              text=True, capture_output=True, check=True,
                              preexec_fn=limits if inherited_limit is not None else None)

    def fixture_module(self, root):
        package = root / 'vfs_server'
        package.mkdir()
        (package / '__init__.py').write_text('')
        (package / 'server.py').write_text(
            'import json,resource,sqlite3\n'
            'print(json.dumps({"fsize":resource.getrlimit(resource.RLIMIT_FSIZE),'
            '"nofile":resource.getrlimit(resource.RLIMIT_NOFILE),'
            '"core":resource.getrlimit(resource.RLIMIT_CORE)}),flush=True)\n')

    def test_policy_requires_exact_native_command(self):
        self.assertEqual(file_policy([sys.executable, '-m', 'vfs_server.server']), 'persistent-vfs')
        for argv in ([sys.executable, '-m', 'other.server'],
                     [sys.executable, '-u', '-m', 'vfs_server.server'],
                     ['/bin/echo', '-m', 'vfs_server.server'],
                     [sys.executable, '-c', 'vfs_server.server']):
            self.assertEqual(file_policy(argv), 'bounded-file')

    def test_other_native_commands_keep_actual_process_guards(self):
        reply = self.child([sys.executable, '-c',
                           'import json,resource; print(json.dumps([resource.getrlimit(resource.RLIMIT_FSIZE),'
                           'resource.getrlimit(resource.RLIMIT_NOFILE),resource.getrlimit(resource.RLIMIT_CORE)]))'])
        self.assertEqual(json.loads(reply.stdout), [[64 * 1024 * 1024] * 2, [256, 256], [0, 0]])

    def test_persistent_command_preserves_inherited_limit_and_other_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture_module(root)
            for inherited in (resource.getrlimit(resource.RLIMIT_FSIZE)[1], 32 * 1024 * 1024):
                reply = self.child([sys.executable, '-m', 'vfs_server.server'], root, inherited)
                limits = json.loads(reply.stdout)
                self.assertEqual(limits['fsize'], [inherited, inherited])
                self.assertEqual(limits['nofile'], [256, 256])
                self.assertEqual(limits['core'], [0, 0])


if __name__ == '__main__':
    unittest.main()
