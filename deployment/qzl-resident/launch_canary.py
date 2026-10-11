import json,subprocess
name='keddeh-qzl-resident-canary';base='/workspace/deployments/owner-qzl-resident';root=base+'/canary-owner'
def run(*args):return subprocess.check_output(['docker',*args],text=True).strip()
info=json.loads(run('inspect',name))[0]
if info['State']['Running'] or info['Config']['Labels'].get('keddeh.owner-root')!=root:raise ValueError('Canary ownership/state mismatch')
run('rm',name)
args=['create','--name',name,'--label','keddeh.owner-root='+root,'--restart','unless-stopped','--network','host','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--memory','2g','--cpus','2','--pids-limit','256','--tmpfs','/tmp:rw,nosuid,size=256m']
for src,ro in [(base,False),(root+'/packages',True),('/workspace/work/owner-qzl-integration/hub',True),('/var/run/docker.sock',False)]:args+=['--mount','type=bind,src='+src+',dst='+src+(',readonly' if ro else '')]
args+=['-e','PYTHONPATH=/workspace/work/owner-qzl-integration/hub','keddeh-owner-qzl:canary',root]
run(*args);print(run('start',name))
