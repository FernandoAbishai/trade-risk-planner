from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from trade_risk.engine import TradeInputError, build_analysis

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"

class Handler(BaseHTTPRequestHandler):
    server_version = "TradeRiskPlanner/4.0"
    def _json(self, status: int, body: dict) -> None:
        data=json.dumps(body,separators=(",",":")).encode("utf-8"); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(data)
    def do_POST(self) -> None:
        if self.path != "/api/calculate": self._json(404,{"ok":False,"error":"not_found"}); return
        try:
            length=int(self.headers.get("Content-Length","0"))
            if not 0 < length <= 100_000: raise TradeInputError("Tamaño de request inválido.")
            payload=json.loads(self.rfile.read(length).decode("utf-8")); self._json(200,{"ok":True,"result":build_analysis(payload)})
        except (TradeInputError,KeyError,ValueError,TypeError,json.JSONDecodeError) as exc: self._json(400,{"ok":False,"error":str(exc)})
        except Exception: self._json(500,{"ok":False,"error":"internal_error"})
    def do_GET(self) -> None:
        path=urlparse(self.path).path
        if path=="/api/health": self._json(200,{"ok":True,"version":"4"}); return
        relative="index.html" if path=="/" else path.lstrip("/"); candidate=(WEB/relative).resolve()
        if WEB.resolve() not in candidate.parents and candidate != WEB.resolve(): self.send_error(403); return
        if not candidate.is_file(): self.send_error(404); return
        data=candidate.read_bytes(); mime,_=mimetypes.guess_type(str(candidate)); self.send_response(200); self.send_header("Content-Type",(mime or "application/octet-stream")+("; charset=utf-8" if (mime or "").startswith(("text/","application/javascript")) else "")); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, fmt: str, *args) -> None: pass

def main() -> None:
    parser=argparse.ArgumentParser(description="Local Trade Risk Planner"); parser.add_argument("--host",default="127.0.0.1"); parser.add_argument("--port",default=8501,type=int); args=parser.parse_args(); server=ThreadingHTTPServer((args.host,args.port),Handler); print(f"Trade Risk Planner: http://{args.host}:{args.port}"); print("Ctrl+C para detener.")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == "__main__": main()
