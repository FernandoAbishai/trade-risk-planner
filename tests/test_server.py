import json, threading, unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app import Handler

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler); cls.port=cls.server.server_address[1]; cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
    @classmethod
    def tearDownClass(cls): cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)
    def post(self,payload):
        req=Request(f'http://127.0.0.1:{self.port}/api/calculate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req,timeout=2) as response: return response.status,json.loads(response.read())
        except HTTPError as exc: return exc.code,json.loads(exc.read())
    def test_health(self):
        with urlopen(f'http://127.0.0.1:{self.port}/api/health',timeout=2) as response: body=json.loads(response.read())
        self.assertEqual(body['version'],'4')
    def test_frontend_default_100_and_reverse_mode(self):
        with urlopen(f'http://127.0.0.1:{self.port}/',timeout=2) as response: html=response.read().decode()
        self.assertIn('value="100"',html); self.assertIn('Sé mi Target',html); self.assertIn('Calcula Stop + Size',html)
    def test_target_api(self):
        status,body=self.post({'mode':'target','capital':100,'available_capital':100,'risk_profile':'medium','side':'long','entry':100,'target':110,'desired_rr':2}); self.assertEqual(status,200); self.assertAlmostEqual(body['result']['plan']['stop'],95.0)
    def test_bad_target(self):
        status,body=self.post({'mode':'target','capital':100,'available_capital':100,'risk_profile':'medium','side':'long','entry':100,'target':90,'desired_rr':2}); self.assertEqual(status,400); self.assertFalse(body['ok'])

if __name__=='__main__': unittest.main()
