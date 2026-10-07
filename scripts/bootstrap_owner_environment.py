#!/usr/bin/env python3
"""Idempotently activate the owner's persistent execution and recursive domains."""
import argparse
import json
from pathlib import Path
from keddeh_namespace.web4_runtime import http_json
ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);a=ap.parse_args()
root=Path(a.root);cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text()
def control(body):return http_json(cfg['ports']['gateway'],'/api/web4/control',body,token)
view=control({'action':'domains'})
for i in range(len(view['domains']),3):
    request={'action':'domains','operation':'spawn'}
    if i:request['parent']='domain-'+str(i-1)
    control(request)
marker=root/'state/owner-environment-admitted.json'
if not marker.exists():
    control({'action':'bilateral','enabled':True})
    marker.write_text(json.dumps({'schema':'keddeh.owner-environment-admission.v1','activated':True})+'\n')
print(json.dumps({'healthy_nodes':http_json(cfg['ports']['gateway'],'/api/web4/status',token=token)['healthy_nodes'],'domains':len(control({'action':'domains'})['domains']),'bilateral_enabled':control({'action':'bilateral'})['enabled']}))
