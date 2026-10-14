from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,unquote,parse_qs
import argparse,base64,json
from .model import ArtifactWrite
from .store import VFSStore
from .auth import MutationAuthorizer
from .health import readiness
MAX_REQUEST_BYTES=70*1024*1024

class Handler(BaseHTTPRequestHandler):
    store=None
    authorizer=MutationAuthorizer()
    def log_message(self,*args): pass
    def send_json(self,status,obj):
        b=json.dumps(obj,separators=(",",":"),sort_keys=True).encode()
        self.send_response(status); self.send_header("content-type","application/json")
        self.send_header("content-length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        n=int(self.headers.get("content-length","0") or 0)
        if n<1:return {}
        if n>MAX_REQUEST_BYTES:raise ValueError("request_too_large")
        return json.loads(self.rfile.read(n))
    def do_GET(self):
        p=unquote(urlparse(self.path).path)
        try:
            if p=="/status":return self.send_json(200,self.store.status())
            if p=="/ready":
                state=readiness(self.store)
                return self.send_json(200 if state["ready"] else 503,state)
            if not self.authorizer.allowed(self.headers.get("authorization")):
                return self.send_json(401,{"error":"unauthorized"})
            if p=="/events":
                query=parse_qs(urlparse(self.path).query);after=int(query.get('after',['0'])[0]);limit=int(query.get('limit',['100'])[0])
                if after<0 or not 1<=limit<=1000:raise ValueError('invalid_event_window')
                with self.store._connect() as db:rows=[dict(row) for row in db.execute('SELECT seq,kind,artifact_digest,path FROM receipts WHERE seq>? ORDER BY seq LIMIT ?',(after,limit))]
                return self.send_json(200,{'events':rows})
            if p.startswith("/artifacts/"):
                digest=p.split("/",2)[2]; rec=self.store.get_artifact(digest)
                if not rec:return self.send_json(404,{"error":"artifact_not_found"})
                return self.send_json(200,{"artifact":rec.as_dict(),"content_b64":base64.b64encode(self.store.read_content(digest)).decode()})
            if p.startswith("/paths/"):
                rec=self.store.resolve_path(p[len("/paths"):])
                return self.send_json(200,{"artifact":rec.as_dict()}) if rec else self.send_json(404,{"error":"path_not_found"})
            if p.startswith("/lineage/"):
                digest=p.split("/",2)[2]; return self.send_json(200,{"digest":digest,"edges":self.store.lineage(digest)})
            return self.send_json(404,{"error":"not_found"})
        except (ValueError,KeyError) as e:return self.send_json(400,{"error":str(e)})
        except Exception:return self.send_json(500,{"error":"internal_error"})
    def do_POST(self):
        p=urlparse(self.path).path
        try:
            if not self.authorizer.allowed(self.headers.get("authorization")):
                return self.send_json(401,{"error":"unauthorized"})
            data=self.body()
            if p=="/subscriptions":
                subscriber=data['subscriber'];prefix=data['prefix'];cursor=data['cursor']
                if type(subscriber) is not str or not 1<=len(subscriber)<=256 or type(prefix) is not str or not prefix.startswith('/') or type(cursor) is not int or cursor<0:raise ValueError('invalid_subscription')
                with self.store._connect() as db:
                    prior=db.execute('SELECT cursor,prefix FROM owner_subscriptions WHERE subscriber=?',(subscriber,)).fetchone()
                    maximum=db.execute('SELECT COALESCE(MAX(seq),0) FROM receipts').fetchone()[0]
                    if cursor>maximum or prior and (cursor<prior['cursor'] or prefix!=prior['prefix']):raise ValueError('subscription_cursor_or_context_conflict')
                    db.execute('INSERT INTO owner_subscriptions VALUES(?,?,?) ON CONFLICT(subscriber) DO UPDATE SET cursor=excluded.cursor',(subscriber,prefix,cursor))
                return self.send_json(200,{'subscriber':subscriber,'prefix':prefix,'cursor':cursor})
            if p=="/artifacts":
                raw=base64.b64decode(data["content_b64"],validate=True)
                rec,receipt=self.store.write(ArtifactWrite(data["path"],raw,data["source"],data.get("predecessor"),data.get("media_type","application/octet-stream")))
                return self.send_json(201,{"artifact":rec.as_dict(),"actor_receipt":receipt.as_dict(),"verification":"PENDING_OBSERVER_READBACK"})
            if p=="/verify":return self.send_json(200,self.store.verify(data["digest"]))
            return self.send_json(404,{"error":"not_found"})
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:return self.send_json(400,{"error":str(e)})
        except Exception:return self.send_json(500,{"error":"internal_error"})

def create_server(root,host="127.0.0.1",port=8787,token_file=None):
    class BoundHandler(Handler):
        pass
    BoundHandler.store=VFSStore(root)
    with BoundHandler.store._connect() as db:db.execute('CREATE TABLE IF NOT EXISTS owner_subscriptions(subscriber TEXT PRIMARY KEY,prefix TEXT NOT NULL,cursor INTEGER NOT NULL)')
    BoundHandler.authorizer=MutationAuthorizer(token_file)
    return ThreadingHTTPServer((host,port),BoundHandler)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=".vfs-server")
    ap.add_argument("--host",default="127.0.0.1"); ap.add_argument("--port",type=int,default=8787)
    ap.add_argument("--token-file",default=None)
    a=ap.parse_args()
    server=create_server(a.root,a.host,a.port,a.token_file)
    try:server.serve_forever()
    finally:server.server_close()
if __name__=="__main__":main()
