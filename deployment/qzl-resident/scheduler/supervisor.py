#!/usr/bin/env python3
import argparse,datetime as dt,fcntl,json,os,signal,subprocess,sys,time
from pathlib import Path
from zoneinfo import ZoneInfo
ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args()
cfg=json.loads(Path(a.config).read_text());root=Path(cfg['runtime']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
sys.path.insert(0,str(Path(__file__).parent));from scheduler import seal,encode
command=[cfg['python'],str(Path(__file__).parent/'scheduler.py'),'--config',str(Path(a.config).resolve()),'--serve']
stopping=False;child=None
def stop(*args):
 global stopping
 stopping=True
 if child and child.poll() is None:child.terminate()
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
with (root/'supervisor.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 failures=0
 while not stopping:
  started=time.monotonic()
  with (root/'scheduler-supervised.log').open('ab') as log:child=subprocess.Popen(command,stdout=log,stderr=log)
  while not stopping and child.poll() is None:
   seal(root/'supervisor-heartbeat.json',encode({'pid':os.getpid(),'worker_pid':child.pid,'restarts':failures,'time':dt.datetime.now(ZoneInfo('Australia/Adelaide')).isoformat(),'status':'RUNNING'}));time.sleep(2)
  if stopping:
   try:child.wait(timeout=15)
   except subprocess.TimeoutExpired:child.kill();child.wait()
   break
  failures=0 if time.monotonic()-started>300 else failures+1
  event={'at':dt.datetime.now(ZoneInfo('Australia/Adelaide')).isoformat(),'exit_code':child.returncode,'restart_attempt':failures,'pid':child.pid}
  with (root/'recovery.jsonl').open('ab') as ledger:ledger.write(encode(event)+b'\n');ledger.flush();os.fsync(ledger.fileno())
  if failures>=5:
   seal(root/'supervisor-heartbeat.json',encode({'pid':os.getpid(),'status':'FAILED','error':'Five rapid worker exits; recovery circuit opened'}));raise SystemExit(1)
  time.sleep(min(30,2**failures))
