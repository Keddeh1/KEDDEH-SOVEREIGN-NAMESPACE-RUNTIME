from pathlib import Path
import tomllib,json,hashlib,urllib.request
root=Path(__file__).parent;out=root/'wheels';out.mkdir(exist_ok=True);pins=[]
for p in tomllib.load((root/'uv.lock').open('rb'))['package']:
 candidates=[w for w in p.get('wheels',[]) if 'none-any' in w['url'] or ('x86_64' in w['url'] and 'manylinux' in w['url'] and ('cp312' in w['url'] or 'abi3' in w['url']))]
 if not candidates:continue
 w=candidates[0];dst=out/w['url'].split('/')[-1]
 with urllib.request.urlopen(w['url'],timeout=45) as r:dst.write_bytes(r.read())
 sha=hashlib.sha256(dst.read_bytes()).hexdigest();assert 'sha256:'+sha==w['hash']
 pins.append({'name':p['name'],'version':p['version'],'sha256':sha,'file':dst.name})
(root/'owner-dependencies.json').write_text(json.dumps(pins,indent=2));print(json.dumps({'owner_lock_verified_wheels':len(pins)}))
