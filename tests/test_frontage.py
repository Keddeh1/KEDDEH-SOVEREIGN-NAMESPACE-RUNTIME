import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from keddeh_namespace.frontage_service import make_server
class FrontageTests(unittest.TestCase):
    def test_consent_idempotency_conflict_and_restart(self):
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/'source';source.mkdir();(source/'index.html').write_text('<h1>Owner frontage</h1>')
            def start():
                server=make_server(source,Path(root)/'runtime');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();return server
            server=start()
            def request(body,origin=None):
                req=urllib.request.Request(f'http://127.0.0.1:{server.server_address[1]}/api/interest',data=json.dumps(body).encode(),headers={'Content-Type':'application/json',**({'Origin':origin} if origin else {})})
                with urllib.request.urlopen(req) as res:return json.load(res)
            payload={'name':'Controlled test','email':'test@example.test','organisation':'Test fixture','interest':'Runtime evaluation','message':'Controlled local test enquiry','request_id':'0123456789abcdef','consent':True}
            try:
                with self.assertRaises(urllib.error.HTTPError) as denied:request({**payload,'consent':False})
                self.assertEqual(denied.exception.code,400)
                receipt=request(payload)['receipt'];self.assertEqual(request(payload)['receipt'],receipt)
                with self.assertRaises(urllib.error.HTTPError) as conflict:request({**payload,'message':'Changed payload with same identity'})
                self.assertEqual(conflict.exception.code,409)
                with self.assertRaises(urllib.error.HTTPError) as foreign:request(payload,'https://foreign.example')
                self.assertEqual(foreign.exception.code,403)
                server.shutdown();server.server_close();server=start()
                self.assertEqual(request(payload)['receipt'],receipt)
            finally:server.shutdown();server.server_close()
