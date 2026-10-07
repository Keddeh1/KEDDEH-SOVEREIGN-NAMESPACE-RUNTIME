#!/usr/bin/env python3
"""Apply an explicit, bounded operational override only to admitted owner domains."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ap=argparse.ArgumentParser();ap.add_argument("--memory-mib",type=int,default=256);ap.add_argument("--apply",action="store_true");a=ap.parse_args()
if not 128<=a.memory_mib<=512:ap.error("memory ceiling must be between 128 and 512 MiB")
ceiling=a.memory_mib*1024*1024
b=Path('/workspace');roots={json.loads(f.read_text())['runtime_root'] for f in b.glob('*/.keddeh/family.json')};ids=subprocess.check_output(['docker','ps','-a','-q','--filter','label=keddeh.owner-root'],text=True).split();rows=[]
admitted=set()
for root in roots:
 path=Path(root).resolve()
 if not path.is_relative_to(b/'braink-setup'):raise ValueError('unexpected owner runtime root; preserve for review')
 topology=path/'state/domains/topology.json'
 if topology.exists():
  for domain in json.loads(topology.read_text())['domains']:
   admitted.add((root,'keddeh-'+hashlib.sha256(root.encode()).hexdigest()[:10]+'-'+domain['id']))
for ident in ids:
 item=json.loads(subprocess.check_output(['docker','inspect',ident],text=True))[0];owner=item['Config']['Labels'].get('keddeh.owner-root')
 if owner not in roots:continue
 if (owner,item['Name'].lstrip('/')) not in admitted:continue
 before=item['HostConfig']['Memory'];
 if before<=0:raise ValueError('retain an unexpected unlimited domain for explicit capacity review')
 if a.apply:subprocess.run(['docker','update','--memory',str(a.memory_mib)+'m',ident],check=True,stdout=subprocess.DEVNULL)
 rows.append({'container':item['Name'].lstrip('/'),'root':owner,'memory_before':before,'memory_after':ceiling if a.apply else before,'proposed_memory':ceiling,'restart_count_before':item['RestartCount'],'state_before':{'running':item['State']['Running'],'oom_killed':item['State']['OOMKilled'],'exit_code':item['State']['ExitCode']}})
if not rows:raise SystemExit('No existing explicitly owned domains; preserve this result and bootstrap the selected family first')
report=b/'braink-setup/research-100/domain-capacity-current.json';report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(json.dumps({'scope':'measured operational mitigation for existing owned domains; factory default still 128 MiB and must be qualified separately','containers':rows},indent=2)+'\n');print(json.dumps({'mode':'applied' if a.apply else 'dry_run','owned_domains':len(rows),'proposed_memory_mib':a.memory_mib,'state_preserved':True}))
