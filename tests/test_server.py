import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import Handler

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def post(self, payload):
        req = Request(
            f"http://127.0.0.1:{self.port}/api/calculate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=2) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_health(self):
        with urlopen(f"http://127.0.0.1:{self.port}/api/health", timeout=2) as response:
            body = json.loads(response.read())
        self.assertEqual(body["version"], "6")

    def test_budget_stop_api(self):
        status, body = self.post({
            "trade_type":"spot", "calculation_mode":"budget_stop",
            "capital":100, "allocation_percent":50, "risk_percent":.5,
            "entry":100, "rr":2, "quantity_precision":8,
        })
        self.assertEqual(status, 200)
        self.assertAlmostEqual(body["result"]["plan"]["stop_price"], 99)

    def test_chart_stop_api(self):
        status, body = self.post({
            "trade_type":"spot", "calculation_mode":"chart_stop",
            "capital":100, "risk_percent":1, "entry":100,
            "chart_stop":95, "rr":2, "quantity_precision":8,
        })
        self.assertEqual(status, 200)
        self.assertAlmostEqual(body["result"]["plan"]["allocation_percent"], 20)

    def test_frontend_is_english_and_has_simple_sliders(self):
        with urlopen(f"http://127.0.0.1:{self.port}/", timeout=2) as response:
            html = response.read().decode()
        self.assertIn("Capital allocation", html)
        self.assertIn("Account risk", html)
        self.assertIn("I already know my chart stop", html)
        self.assertIn("Quantity precision", html)
        self.assertIn('value="100"', html)
        self.assertNotIn("BTC", html)

    def test_invalid_trade_returns_400(self):
        status, body = self.post({
            "trade_type":"spot", "calculation_mode":"chart_stop",
            "capital":100, "risk_percent":1, "entry":100, "chart_stop":101,
        })
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])

if __name__ == "__main__":
    unittest.main()
