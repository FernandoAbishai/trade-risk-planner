import json,threading,unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from app import Handler
class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.port=cls.server.server_address[1];cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def post(self,payload):
        req=Request(f'http://127.0.0.1:{self.port}/api/calculate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req,timeout=2) as r:return r.status,json.loads(r.read())
        except HTTPError as e:return e.code,json.loads(e.read())
    def test_health(self):
        with urlopen(f'http://127.0.0.1:{self.port}/api/health',timeout=2) as r:body=json.loads(r.read())
        self.assertEqual(body['version'],'5')
    def test_frontend_english_slider_ui(self):
        with urlopen(f'http://127.0.0.1:{self.port}/',timeout=2) as r:html=r.read().decode()
        self.assertIn('Capital allocation',html);self.assertIn('Account risk per trade',html);self.assertIn('value="100"',html);self.assertIn('Spot Simple',html);self.assertNotIn('BTC',html)
    def test_api(self):
        status,body=self.post({'trade_type':'spot','capital':100,'allocation_percent':50,'risk_percent':.5,'entry':100,'rr':2});self.assertEqual(status,200);self.assertAlmostEqual(body['result']['plan']['stop_price'],99)
    def test_bad_allocation(self):
        status,body=self.post({'trade_type':'spot','capital':100,'allocation_percent':120,'risk_percent':.5,'entry':100});self.assertEqual(status,400);self.assertFalse(body['ok'])
if __name__=='__main__':unittest.main()
