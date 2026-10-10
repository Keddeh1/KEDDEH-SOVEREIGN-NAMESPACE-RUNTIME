"""Loopback owner-state control surface with real VFS readback.

Failure exercises operate only on a disposable copied state materialisation.
"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import argparse,hashlib,json,pathlib,secrets,shutil,tempfile,threading
from continuity import ContinuityVFS

BASE=pathlib.Path(__file__).parent
IDENTITIES=['kex/owner/observer-origin','kex/owner/relational-continuity']

def serve(root,port=3160):
    root=pathlib.Path(root);work=tempfile.TemporaryDirectory(prefix='keddeh-state-session-')
    copy=pathlib.Path(work.name)/'materialisation';shutil.copytree(root,copy)
    c=ContinuityVFS(copy);lock=threading.Lock();quarantine={};events=[];token=secrets.token_urlsafe(32)
    def state():
        entries=[]
        for identity in IDENTITIES:
            r=c.observe(identity);p=c.observe(identity+'/projection')
            projection=json.loads(p.payload) if p.status=='AVAILABLE' else None
            entries.append({'identity':identity,'status':r.status,'version':r.version,'digest':r.digest,
                            'receipt':r.receipt,'reason':r.reason,'source':r.payload.decode() if r.payload is not None else None,
                            'projection':projection})
        return {'entries':entries,'observedEvents':events,'boundary':'Real local copied VFS. Logical source identities persist; no remote/hardware success inferred.'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,body,kind='application/json'):
            raw=json.dumps(body).encode() if kind=='application/json' else body
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if self.path=='/':return self.send(200,(BASE/'console.html').read_bytes().replace(b'__TOKEN__',token.encode()),'text/html; charset=utf-8')
            if self.path=='/api/state':
                with lock:
                    try:return self.send(200,state())
                    except Exception as e:return self.send(500,{'error':type(e).__name__})
            return self.send(404,{'error':'not found'})
        def do_POST(self):
            if self.path!='/api/action':return self.send(404,{'error':'not found'})
            if self.headers.get('X-State-Token')!=token:return self.send(403,{'error':'invalid session token'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4096:raise ValueError('invalid request size')
                data=json.loads(self.rfile.read(size));identity=data['identity'];action=data['action']
                if identity not in IDENTITIES or action not in ('detach','restore'):raise ValueError('invalid identity/action')
                with lock:
                    before=c.observe(identity)
                    if action=='detach':
                        if before.status!='AVAILABLE':raise ValueError('carrier is not available')
                        quarantine[identity]=(before.payload,before.version)
                        (c.vfs.objects/before.digest).unlink()
                    else:
                        if identity not in quarantine:raise ValueError('no retained recovery payload')
                        raw,version=quarantine[identity];c.recover(identity,raw,expected_version=version)
                        del quarantine[identity]
                    after=c.observe(identity)
                    events.append({'sequence':len(events)+1,'identity':identity,'action':action,'before':before.status,
                                   'observed':after.status,'digest':after.digest,'receipt':after.receipt})
                    return self.send(200,state())
            except (KeyError,ValueError) as e:return self.send(409,{'error':str(e)})
            except Exception as e:return self.send(500,{'error':type(e).__name__})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Owner-state console: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    finally:server.server_close();work.cleanup()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(BASE/'owner-state-vfs'));p.add_argument('--port',type=int,default=3160);a=p.parse_args();serve(a.root,a.port)
