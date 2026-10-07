"""Apply the native process policy for an exact owner package command.

The persistent VFS has its own per-artifact size contract. Its aggregate SQLite
database and WAL retain the controller's inherited filesystem limits instead
of applying an artifact-sized process limit to every persistence file.
"""
import os
import resource
import sys


def file_policy(argv):
    """Identify the one native persistent VFS command, without an environment override."""
    if (len(argv) >= 3 and os.path.realpath(argv[0]) == os.path.realpath(sys.executable)
            and argv[1:3] == ['-m', 'vfs_server.server']):
        return 'persistent-vfs'
    return 'bounded-file'


def apply_limits(policy):
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    if policy == 'bounded-file':
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024, 64 * 1024 * 1024))
    elif policy != 'persistent-vfs':
        raise ValueError('unknown native file policy')


def main():
    if len(sys.argv)<2:raise SystemExit('an executable argv is required')
    apply_limits(file_policy(sys.argv[1:]))
    os.execvpe(sys.argv[1],sys.argv[1:],os.environ)

if __name__=='__main__':main()
