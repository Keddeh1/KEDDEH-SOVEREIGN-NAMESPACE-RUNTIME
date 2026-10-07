#!/usr/bin/env python3
"""Recover exact uploaded originals using existing private GitHub proxy access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from keddeh_namespace.web4_runtime import PINS, write_json


def restore(checkout,destination):
    checkout=Path(checkout).resolve();destination=Path(destination);rows=json.loads((checkout/'library/2026-10-07/manifest.json').read_text())['files'];by_name={r['name']:r for r in rows};out=[]
    for _,(name,sha) in PINS.items():
        row=by_name[name];rel=Path(row['repository_path']);source=checkout/rel
        if rel.is_absolute() or '..' in rel.parts or source.is_symlink() or not source.resolve().is_relative_to(checkout):raise ValueError('invalid source custody path')
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha or len(raw)!=row['bytes']:raise ValueError('repository original does not match pinned upload')
        target=destination/sha/name;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=raw:raise ValueError('existing library object differs; retain for diagnosis')
        if not target.exists():shutil.copyfile(source,target)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
        out.append({'name':name,'sha256':sha,'bytes':len(raw),'library_path':str(target.absolute()),'origin':'verified private deployment-queue Git originals'})
    manifest=destination/'manifest.json'
    if manifest.exists():raise ValueError('refusing to overwrite an existing library manifest')
    write_json(manifest,{'status':'verified repository restoration of exact originals','files':out})
    return {'files':len(out),'bytes':sum(r['bytes'] for r in out),'manifest':str(manifest)}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--queue-checkout');ap.add_argument('--destination',default='/workspace/library-files/KEDDEH/2026-10-07');args=ap.parse_args()
    if (Path(args.destination)/'manifest.json').exists():raise SystemExit('Library manifest already exists; preserve it and use launch verification.')
    if args.queue_checkout:result=restore(args.queue_checkout,args.destination)
    else:
        with tempfile.TemporaryDirectory(prefix='keddeh-web4-library-') as temp:
            checkout=Path(temp)/'queue'
            subprocess.run(['git','clone','--depth','1','https://github.com/Keddeh1/SYSTEMS-SERVICES-FOR-DEPLOYMENT-QUEUE.git',str(checkout)],check=True)
            result=restore(checkout,args.destination)
    print(json.dumps(result,indent=2))
