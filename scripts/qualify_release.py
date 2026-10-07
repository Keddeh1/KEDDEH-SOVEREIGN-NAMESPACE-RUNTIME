#!/usr/bin/env python3
"""Fail-closed candidate qualification; outputs are evidence, not production approval."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

repo = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--output', required=True)
ap.add_argument('--runtime-root')
ap.add_argument('--container-no-sandbox', action='store_true')
a = ap.parse_args()
out = Path(a.output).resolve()
if out == repo or repo in out.parents:
    ap.error('Evidence output must be outside the source checkout')
out.mkdir(parents=True, exist_ok=False)
report = {'schema': 'keddeh.release-qualification.v1', 'status': 'running', 'gates': [],
          'scope': 'local candidate qualification', 'production_approval': False}
def run(name, command, cwd=repo, env=None):
    with (out / (name + '.log')).open('w') as log:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    report['gates'].append({'name': name, 'exit_code': result.returncode,
                            'status': 'passed' if result.returncode == 0 else 'failed'})
    if result.returncode:
        raise RuntimeError(f'{name} failed; see {out / (name + ".log")}')
try:
    report['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip():
        raise RuntimeError('Commit candidate changes before qualification')
    if subprocess.check_output(['uv', '--version'], text=True).split()[1] != '0.12.19':
        raise RuntimeError('Qualification requires uv 0.12.19')
    run('governance', [sys.executable, 'scripts/check_governance.py'])
    run('frozen-install', ['uv', 'sync', '--frozen'])
    run('dependency-check', ['uv', 'pip', 'check'])
    python = str(repo / '.venv/bin/python')
    run('source-tests', [python, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    run('wheel-build', ['uv', 'build', '--wheel', '--out-dir', str(out / 'wheel'),
                       '--build-constraint', str(repo / 'build-constraints.txt')])
    wheel, = (out / 'wheel').glob('*.whl')
    report['artifact'] = {'name': wheel.name, 'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(), 'bytes': wheel.stat().st_size}
    run('isolated-venv', ['uv', 'venv', str(out / 'installed')])
    installed = str(out / 'installed/bin/python')
    lock = tomllib.loads((repo / 'uv.lock').read_text())
    dependencies = [f"{p['name']}=={p['version']}" for p in lock['package'] if p['name'] != 'keddeh-sovereign-namespace-runtime']
    run('artifact-install', ['uv', 'pip', 'install', '--python', installed, str(wheel), *dependencies])
    env = dict(os.environ); env.pop('PYTHONPATH', None)
    run('installed-tests', [installed, '-m', 'unittest', 'discover', '-s', str(repo / 'tests'), '-v'], cwd=out, env=env)
    run('installed-dependencies', ['uv', 'pip', 'check', '--python', installed])
    inventory = "import importlib.metadata as m,json; print(json.dumps([{'name':d.metadata['Name'],'version':d.version,'license_expression':d.metadata.get('License-Expression'),'license':d.metadata.get('License'),'requires':d.requires or []} for d in m.distributions()],indent=2))"
    (out / 'dependency-inventory.json').write_bytes(subprocess.check_output([installed, '-c', inventory]))
    if a.runtime_root:
        run('live-integration', [installed, str(repo / 'scripts/verify_web4_runtime.py'), '--root', a.runtime_root, '--output', str(out / 'integration.json')], cwd=out, env=env)
        command = ['node', str(repo / 'scripts/test_web4_browser.mjs'), '--root', a.runtime_root]
        if a.container_no_sandbox: command.append('--container-no-sandbox')
        run('browser-integration', command, cwd=out, env=env)
        report['runtime_qualification'] = 'passed'
    else:
        report['runtime_qualification'] = 'not_run_requires_owner_package_runtime'
    report['status'] = 'passed'
except Exception as exc:
    report['status'] = 'failed'; report['error'] = str(exc)
finally:
    report['evidence_hashes'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
if report['status'] != 'passed': sys.exit(1)
