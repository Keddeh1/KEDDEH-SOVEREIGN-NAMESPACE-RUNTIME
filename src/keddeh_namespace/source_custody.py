"""Verify exact archive bytes without extracting or executing their contents."""
import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path


def verify_archive(path, expected):
    if not isinstance(expected, dict):
        raise ValueError('archive expectation must be an object')
    size = expected.get('bytes')
    digest = expected.get('sha256')
    if type(size) is not int or size < 0:
        raise ValueError('bytes must be a nonnegative integer')
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('sha256 must be a lowercase SHA-256 digest')
    path = Path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise ValueError('archive must be a readable regular nonsymlink file') from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError('archive must be a regular file')
    observed_size = 0
    hasher = hashlib.sha256()
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('archive must be a regular file')
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            observed_size += len(chunk)
            if observed_size > size:
                raise ValueError('archive exceeds expected byte length')
            hasher.update(chunk)
    observed_hash = hasher.hexdigest()
    if observed_size != size or observed_hash != digest:
        raise ValueError(f'archive mismatch: observed bytes={observed_size}, sha256={observed_hash}')
    return {'bytes': observed_size, 'sha256': observed_hash, 'status': 'exact_bytes_verified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('archive_name')
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        result = verify_archive(args.archive, manifest['archives'][args.archive_name])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Archive rejected: {exc}\n')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
