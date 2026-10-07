"""Same-origin customer frontage with scoped live readbacks and durable consent."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit, unquote
from .web4_runtime import http_json

def make_server(source,root,port=0):
    source=Path(source).resolve();root=Path(root);state=root/'state/frontage';state.mkdir(parents=True,exist_ok=True);state.chmod(0o700)
    database=state/'interest.sqlite3'
    def connect():
        db=sqlite3.connect(database,timeout=10);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        return db
    initial=connect()
    try:
        with initial:initial.execute('CREATE TABLE IF NOT EXISTS interests(request_id TEXT PRIMARY KEY,receipt TEXT NOT NULL,digest TEXT NOT NULL,created REAL NOT NULL,payload TEXT NOT NULL)')
    finally:initial.close()
    database.chmod(0o600)
    rates={}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,data,content='application/json'):
            raw=json.dumps(data).encode() if content=='application/json' else data
            self.send_response(status);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store' if content=='application/json' else 'no-cache')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            path=unquote(urlsplit(self.path).path)
            if path=='/api/runtime':
                try:
                    cfg=json.loads((root/'launch.json').read_text());token=(root/'state/token').read_text()
                    live=http_json(cfg['ports']['gateway'],'/api/web4/status',token=token)
                    return self.reply(200,{'repository':live.get('repository'),'family':live.get('family_id'),'healthy_workstations':live['healthy_nodes'],'boot_status':live['boot_status'],'scope':'local cloud-host family','observed_at':datetime.now(timezone.utc).isoformat()})
                except Exception:return self.reply(503,{'status':'readback_unavailable','scope':'local cloud-host family'})
            if path=='/api/claims':
                return self.reply(200,json.loads((source/'claims.json').read_text()))
            if path=='/api/health':return self.reply(200,{'status':'ready','customer_data':'private durable consent store','public_site_publication':'not asserted by this local service'})
            if '..' in path.split('/') or '\x00' in path:return self.reply(400,{'error':'invalid_path'})
            file=(source/(path.lstrip('/') or 'index.html')).resolve()
            if not file.is_relative_to(source):return self.reply(400,{'error':'invalid_path'})
            if file.is_dir():file=file/'index.html'
            if not file.is_file():return self.reply(404,{'error':'not_found'})
            return self.reply(200,file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        def do_POST(self):
            if urlsplit(self.path).path!='/api/interest':return self.reply(404,{'error':'not_found'})
            origin=self.headers.get('Origin')
            if origin and urlsplit(origin).netloc!=self.headers.get('Host'):return self.reply(403,{'error':'origin_not_allowed'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=16384:raise ValueError('Please keep this enquiry within the form limits.')
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict):raise ValueError('Please submit the enquiry form.')
                for key in ('name','email','organisation','interest','message','request_id'):
                    if not isinstance(data.get(key,''),str):raise ValueError('Please check the form fields.')
                    data[key]=data.get(key,'').strip()
                if not 1<=len(data['name'])<=100:raise ValueError('Please enter your name (up to 100 characters).')
                if len(data['email'])>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['email']):raise ValueError('Please enter a valid email address.')
                if data['interest'] not in ('Runtime evaluation','Enterprise deployment','Research collaboration','Developer integration','General enquiry'):raise ValueError('Please select an enquiry topic.')
                if len(data['organisation'])>150 or not 10<=len(data['message'])<=3000:raise ValueError('Please describe your use case in 10–3000 characters.')
                if data.get('consent') is not True:raise ValueError('Please agree to the enquiry privacy terms before submitting.')
                if data.get('website'):raise ValueError('Please use the visible form fields.')
                if not re.fullmatch(r'[A-Za-z0-9-]{16,80}',data['request_id']):raise ValueError('Please reload the form and retry.')
                stored={k:data[k] for k in ('name','email','organisation','interest','message','request_id','consent')};stored['privacy_version']='1.0'
                raw=json.dumps(stored,sort_keys=True);digest=hashlib.sha256(raw.encode()).hexdigest()
                db=connect()
                try:
                    db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM interests WHERE created<?',(time.time()-90*86400,))
                    old=db.execute('SELECT receipt,digest FROM interests WHERE request_id=?',(stored['request_id'],)).fetchone()
                    if old:
                        if old[1]!=digest:db.rollback();return self.reply(409,{'error':'This submission identifier already belongs to another enquiry. Please start a new enquiry.'})
                        receipt=old[0]
                    else:
                        key=self.client_address[0];recent=[t for t in rates.get(key,[]) if time.time()-t<3600]
                        if len(recent)>=10:db.rollback();return self.reply(429,{'error':'Please wait before submitting another enquiry.'})
                        recent.append(time.time());rates[key]=recent
                        receipt='KEDDEH-'+secrets.token_hex(12).upper()
                        db.execute('INSERT INTO interests VALUES(?,?,?,?,?)',(stored['request_id'],receipt,digest,time.time(),raw))
                    db.commit()
                finally:db.close()
                return self.reply(201,{'receipt':receipt,'status':'registered','message':'Your interest has been recorded. This is an enquiry, not an account, purchase or deployment commitment.'})
            except (ValueError,KeyError,json.JSONDecodeError,UnicodeError) as exc:return self.reply(400,{'error':str(exc)})
            except Exception:return self.reply(503,{'error':'We could not record this enquiry. Your form is still available; please retry.'})
    class FrontageServer(ThreadingHTTPServer):
        last_cleanup=0
        def service_actions(self):
            if time.monotonic()-self.last_cleanup>=300:
                db=connect()
                try:
                    with db:db.execute('DELETE FROM interests WHERE created<?',(time.time()-90*86400,))
                finally:db.close()
                self.last_cleanup=time.monotonic()
    return FrontageServer(('127.0.0.1',port),Handler)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--root',required=True);ap.add_argument('--port',type=int,required=True);a=ap.parse_args()
    make_server(a.source,a.root,a.port).serve_forever()
if __name__=='__main__':main()
