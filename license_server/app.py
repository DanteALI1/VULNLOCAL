from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

SECRET = os.environ.get("LICENSE_SERVER_SECRET", "dev-license-secret").encode()
PORT = int(os.environ.get("LICENSE_SERVER_PORT", "8100"))


def sign(payload: dict) -> str:
    body = {k: payload[k] for k in ("org", "seats", "expires") if k in payload}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(SECRET, raw, hashlib.sha256).hexdigest()


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, data: dict) -> None:
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith("/health"):
            return self._json(200, {"status": "ok"})
        if self.path.startswith("/v1/heartbeat"):
            expires = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
            payload = {"org": "NovaTIP Dev", "seats": 25, "expires": expires}
            payload["signature"] = sign(payload)
            return self._json(200, payload)
        return self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"license_server listening on :{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
