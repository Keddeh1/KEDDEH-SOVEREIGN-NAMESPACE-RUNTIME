"""Measure mounted storage and execute fsync/readback without claiming remote durability."""
import argparse
import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path
from .logical_vfs import sync_directory


def verify_volume(path, *, required_bytes, require_mount=True):
    path = Path(path).resolve(strict=True)
    if type(required_bytes) is not int or required_bytes <= 0:
        raise ValueError('required_bytes must be a positive integer')
    if require_mount and not os.path.ismount(path):
        raise ValueError('target is not a mount point')
    stats = os.statvfs(path)
    capacity = stats.f_frsize * stats.f_blocks
    available = stats.f_frsize * stats.f_bavail
    if capacity < required_bytes:
        raise ValueError(f'insufficient observed capacity: {capacity} < {required_bytes}')
    payload = secrets.token_bytes(4096)
    fd, probe = tempfile.mkstemp(prefix='.keddeh-readback-', dir=path)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        sync_directory(path)
        if Path(probe).read_bytes() != payload:
            raise ValueError('fsync/readback failed')
    finally:
        Path(probe).unlink(missing_ok=True)
        sync_directory(path)
    return dict(path=str(path), capacity_bytes=capacity, available_bytes=available,
                required_bytes=required_bytes, is_mount=os.path.ismount(path),
                probe_sha256=hashlib.sha256(payload).hexdigest(), fsync_readback='passed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path'); parser.add_argument('--required-bytes',type=int,required=True)
    parser.add_argument('--allow-directory',action='store_true',help='local test only; not production mount evidence')
    args=parser.parse_args()
    try: result=verify_volume(args.path,required_bytes=args.required_bytes,require_mount=not args.allow_directory)
    except (OSError,ValueError) as exc: parser.exit(1,f'Volume rejected: {exc}\n')
    print(json.dumps(result,sort_keys=True))


if __name__ == '__main__': main()
