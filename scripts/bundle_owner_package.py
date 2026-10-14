#!/usr/bin/env python3
"""Bundle tracked engine, wheel, documentation and exact private owner sources."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import io
import tomllib
from keddeh_namespace.web4_runtime import PINS
ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--wheel',required=True);a=ap.parse_args()
repo=Path(__file__).resolve().parents[1];destination=Path(a.output);destination.parent.mkdir(parents=True,exist_ok=True)
wheel=Path(a.wheel);members=[]
for name in subprocess.check_output(['git','ls-files'],cwd=repo,text=True).splitlines():
 p=repo/name
 if p.is_file():members.append(('engine/'+name,p))
members.append(('wheel/'+wheel.name,wheel))
library=Path('/workspace/library-files/KEDDEH/2026-10-07')
for name,sha in PINS.values():
 p=library/sha/name
 if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise ValueError('owner source custody mismatch')
 members.append(('owner-sources/'+sha+'/'+name,p))
for row in json.loads((repo/'docs/OWNER_SOURCE_MANIFEST.json').read_text())['files']:
 p=library/row['sha256']/row['name']
 if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('owner control source custody mismatch')
 members.append(('owner-sources/'+row['sha256']+'/'+row['name'],p))
manifest={'schema':'keddeh.owner-family-bundle.v1','version':tomllib.loads((repo/'pyproject.toml').read_text())['project']['version'],'engine_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'classification':'private owner-source bundle; no runtime credentials or mutable state','members':[{'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for name,p in members]}
with tarfile.open(destination,'w:gz') as archive:
 for name,p in members:
  item=tarfile.TarInfo(name);item.size=p.stat().st_size;item.mode=0o644;item.mtime=0
  with p.open('rb') as stream:archive.addfile(item,stream)
 raw=(json.dumps(manifest,indent=2)+'\n').encode();item=tarfile.TarInfo('BUNDLE_MANIFEST.json');item.size=len(raw);item.mode=0o644;archive.addfile(item,io.BytesIO(raw))
sha=hashlib.sha256(destination.read_bytes()).hexdigest()
result={'bundle':destination.name,'sha256':sha,'bytes':destination.stat().st_size,'members':len(members),'engine_commit':manifest['engine_commit'],'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()}
destination.with_suffix(destination.suffix+'.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
