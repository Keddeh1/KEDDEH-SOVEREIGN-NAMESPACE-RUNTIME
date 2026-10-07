"""Verify a private archive snapshot and publish bounded regular files write-once."""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path
from .envelope import canonical_bytes
from .logical_vfs import logical_path, sync_directory

RECEIPT = '.keddeh-admission.json'


def archive_snapshot(source, snapshot, expected):
    if type(expected) is not dict or type(expected.get('bytes')) is not int or expected['bytes']<0:
        raise ValueError('invalid expected archive size')
    digest=expected.get('sha256')
    if type(digest) is not str or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid expected digest')
    fd=os.open(source,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    size=0;hasher=hashlib.sha256()
    with os.fdopen(fd,'rb') as stream, open(snapshot,'xb') as output:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('source must be regular file')
        while chunk:=stream.read(1024*1024):
            size+=len(chunk)
            if size>expected['bytes']: raise ValueError('archive exceeds expected size')
            hasher.update(chunk);output.write(chunk)
        output.flush();os.fsync(output.fileno())
    if size!=expected['bytes'] or hasher.hexdigest()!=digest:
        raise ValueError('archive byte/hash mismatch')


def verify_admission(destination, expected):
    destination=Path(destination)
    receipt=json.loads((destination/RECEIPT).read_text())
    if receipt.get('source')!=expected: raise ValueError('admission source mismatch')
    actual={}
    for path in destination.rglob('*'):
        if path.is_symlink(): raise ValueError('symlink in admitted volume')
        if path.is_file() and path!=destination/RECEIPT:
            actual[str(path.relative_to(destination))]={'bytes':path.stat().st_size,
                   'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':stat.S_IMODE(path.stat().st_mode)}
        elif not path.is_dir() and path!=destination/RECEIPT:
            raise ValueError('nonregular volume entry')
    if actual!=receipt['files']: raise ValueError('admitted volume readback mismatch')
    return receipt


def hydrate(source, root, expected, *, max_bytes=1024**3, max_files=10000):
    if type(max_bytes) is not int or max_bytes<=0 or type(max_files) is not int or max_files<=0:
        raise ValueError('positive extraction bounds required')
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    if type(expected) is not dict: raise ValueError('expected custody object required')
    # Hold a cooperating-writer lock; root must be operator-controlled.
    with open(root/'.admission.lock','a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with tempfile.TemporaryDirectory(prefix='.admission-',dir=root) as temp:
            staging=Path(temp);snapshot=staging/'source.archive'
            archive_snapshot(source,snapshot,expected)
            destination=root/expected['sha256']
            if destination.is_symlink(): raise ValueError('admission destination symlink rejected')
            output=staging/'volume';output.mkdir()
            files={};declared=set();total=0
            def entry(name,size,is_directory):
                nonlocal total
                normalized=name.rstrip('/') if is_directory else name
                logical_path(normalized)
                if normalized==RECEIPT or any(p==RECEIPT for p in normalized.split('/')):
                    raise ValueError('reserved receipt path')
                if normalized in declared: raise ValueError('duplicate archive entry')
                declared.add(normalized)
                if len(declared)>max_files: raise ValueError('archive entry limit exceeded')
                if type(size) is not int or size<0: raise ValueError('invalid entry size')
                total+=size
                if total>max_bytes: raise ValueError('expanded archive exceeds bound')
                target=output/normalized
                if is_directory: target.mkdir(parents=True,exist_ok=True)
                else: target.parent.mkdir(parents=True,exist_ok=True)
                return normalized,target
            def write_file(name,target,stream,size,source_mode):
                count=0;hasher=hashlib.sha256()
                with target.open('xb') as sink:
                    while chunk:=stream.read(1024*1024):
                        count+=len(chunk)
                        if count>size: raise ValueError('entry exceeds declared size')
                        sink.write(chunk);hasher.update(chunk)
                    sink.flush();os.fsync(sink.fileno())
                if count!=size: raise ValueError('truncated archive entry')
                mode=0o555 if source_mode&0o111 else 0o444
                target.chmod(mode)
                files[name]={'bytes':count,'sha256':hasher.hexdigest(),'mode':mode}
            if zipfile.is_zipfile(snapshot):
                with zipfile.ZipFile(snapshot) as archive:
                    for info in archive.infolist():
                        mode=info.external_attr>>16
                        kind=stat.S_IFMT(mode)
                        if kind not in (0,stat.S_IFREG,stat.S_IFDIR): raise ValueError('archive links/devices not admitted')
                        if info.flag_bits&1: raise ValueError('encrypted archive not admitted')
                        name,target=entry(info.filename,info.file_size,info.is_dir())
                        if not info.is_dir():
                            with archive.open(info) as stream: write_file(name,target,stream,info.file_size,mode)
            else:
                with tarfile.open(snapshot,'r:*') as archive:
                    for info in archive:
                        if not (info.isfile() or info.isdir()): raise ValueError('archive links/devices not admitted')
                        name,target=entry(info.name,info.size,info.isdir())
                        if info.isfile():
                            with archive.extractfile(info) as stream: write_file(name,target,stream,info.size,info.mode)
            if not files: raise ValueError('empty service archive')
            receipt={'schema':'keddeh.admission.v1','source':expected,'files':files,
                     'expanded_bytes':total,'status':'verified_source_and_extraction'}
            if destination.exists():
                observed=verify_admission(destination,expected)
                if observed!=receipt: raise ValueError('existing extraction diverges from exact source')
                return observed
            with (output/RECEIPT).open('xb') as stream:
                stream.write(canonical_bytes(receipt));stream.flush();os.fsync(stream.fileno())
            (output/RECEIPT).chmod(0o444)
            for path in sorted(output.rglob('*'),key=lambda p:len(p.parts),reverse=True):
                if path.is_dir(): sync_directory(path);path.chmod(0o555)
            sync_directory(output)
            os.rename(output,destination);destination.chmod(0o555);sync_directory(root)
            return verify_admission(destination,expected)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest');parser.add_argument('name');parser.add_argument('archive');parser.add_argument('root')
    args=parser.parse_args()
    try:
        with open(args.manifest) as stream: expected=json.load(stream)['archives'][args.name]
        receipt=hydrate(args.archive,args.root,expected)
    except (OSError,ValueError,KeyError,tarfile.TarError,zipfile.BadZipFile) as exc:
        parser.exit(1,f'Admission rejected: {exc}\n')
    print(json.dumps(receipt,sort_keys=True))


if __name__ == '__main__': main()
