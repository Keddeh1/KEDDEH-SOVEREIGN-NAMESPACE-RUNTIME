from pathlib import Path
import tomllib, json, urllib.request, hashlib, shutil, subprocess
import argparse, os
ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--qualification',required=True);args=ap.parse_args()
root=Path(args.output).resolve();root.mkdir(exist_ok=True,parents=True);wheels=root/'wheels';wheels.mkdir(exist_ok=True)
engine=Path(__file__).resolve().parents[1];lock=tomllib.load(open(engine/'uv.lock','rb'));artifacts=[]
for p in lock['package']:
 candidates=[w for w in p.get('wheels',[]) if 'none-any' in w['url'] or ('x86_64' in w['url'] and 'manylinux' in w['url'] and ('cp312' in w['url'] or 'abi3' in w['url']))]
 if not candidates:continue
 item=candidates[0];dest=wheels/item['url'].split('/')[-1]
 if not dest.exists():
  with urllib.request.urlopen(item['url'],timeout=60) as response:dest.write_bytes(response.read())
 digest=hashlib.sha256(dest.read_bytes()).hexdigest();assert 'sha256:'+digest==item['hash']
 artifacts.append({'name':p['name'],'version':p['version'],'file':dest.name,'sha256':digest})
qualified=Path(args.qualification).resolve();q=json.loads((qualified/'qualification.json').read_text());assert q['status']=='passed'
wheel=qualified/'wheel'/q['artifact']['name'];assert hashlib.sha256(wheel.read_bytes()).hexdigest()==q['artifact']['sha256'];shutil.copy2(wheel,wheels/wheel.name)
shutil.copy2('/usr/local/bin/docker',root/'docker')
(root/'DEPENDENCIES.json').write_text(json.dumps(artifacts,indent=2)+'\n')
(root/'Dockerfile').write_text('''FROM node@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS node
FROM python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /lib/x86_64-linux-gnu/libstdc++.so.6 /lib/x86_64-linux-gnu/libstdc++.so.6
COPY --from=node /lib/x86_64-linux-gnu/libgcc_s.so.1 /lib/x86_64-linux-gnu/libgcc_s.so.1
COPY docker /usr/local/bin/docker
COPY wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels /wheels/OWNER_WHEEL && python -m pip check
RUN groupadd --gid 1000 keddeh && useradd --uid 1000 --gid 1000 --home-dir /tmp/keddeh-owner keddeh
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1
ENTRYPOINT ["python", "-m", "keddeh_namespace.web4_runtime", "serve", "--root"]
'''.replace('OWNER_WHEEL',wheel.name))
env=dict(os.environ);env['DOCKER_CONFIG']=str(root/'docker-config')
subprocess.run(['docker','build','--network','none','-t','keddeh-owner-controller:qualified',str(root)],check=True,env=env)
image=subprocess.check_output(['docker','image','inspect','keddeh-owner-controller:qualified','--format','{{.Id}}'],text=True).strip()
(root/'CONTROLLER_IMAGE.json').write_text(json.dumps({'schema':'keddeh.resident-controller-image.v1','image_id':image,'qualified_commit':q['commit'],'qualified_wheel_sha256':q['artifact']['sha256'],'docker_cli_sha256':hashlib.sha256((root/'docker').read_bytes()).hexdigest(),'python_base':'python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258','node_base':'node@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20'},indent=2)+'\n')
print('qualified wheels installed into pinned Python/Node owner-controller image')
