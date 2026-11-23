"""Serve the review page and its items from one SQLite file.

Usage:
  python3 integrations/sqlite/serve.py DB [--port 47821] [--host 127.0.0.1]

Open http://127.0.0.1:47821 to review. Stop it with Ctrl-C. The items stay in
DB, and a run reads and writes DB with store.py whether this is up or not.

There is no login here. Everyone who can reach the address can approve, so
keep the default host, or put the address behind a login you already have.

The page can change one thing: the `decision` on an item that is not written
yet. It never sees the saved cursors.
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402

PAGE = Path(__file__).resolve().parent.parent.parent / "ui" / "review.html"
MAX_BODY = 1_000_000


class Handler(BaseHTTPRequestHandler):
    db = ""

    def log_message(self, fmt, *args):
        # The page asks every 5 seconds. Log only what changes something or fails.
        if self.command != "GET" or len(args) < 2 or not str(args[1]).startswith("2"):
            super().log_message(fmt, *args)

    def send(self, status: int, body: bytes, kind: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, data) -> None:
        self.send(status, json.dumps(data, ensure_ascii=False).encode())

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send(200, PAGE.read_bytes(), "text/html")
        elif path == "/api/proposals":
            self.send_json(200, store.list_docs(self.db, "proposals"))
        elif path == "/api/runs":
            runs = sorted(store.list_docs(self.db, "runs"), key=lambda r: str(r.get("date", "")), reverse=True)
            self.send_json(200, runs[:30])
        elif path == "/api/me":
            # Nobody is signed in here, so the page lets everyone decide.
            self.send_json(200, {})
        else:
            self.send_json(404, {"error": "not found"})

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/proposals/"):
            self.send_json(404, {"error": "not found"})
            return
        # A page on another site must not be able to approve items through a visitor's browser.
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            self.send_json(403, {"error": "this request came from another site"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > MAX_BODY:
                raise ValueError("body too large")
            body = json.loads(self.rfile.read(size))
            decision = body["decision"] if isinstance(body, dict) else None
            if not isinstance(decision, dict):
                raise ValueError("decision missing")
        except (ValueError, KeyError):
            self.send_json(400, {"error": 'send {"decision": {...}}'})
            return
        doc_id = unquote(path[len("/api/proposals/") :])

        def written(doc: dict):
            return "This item is already written. It can no longer change." if doc.get("pushed") else None

        try:
            self.send_json(200, store.update_doc(self.db, "proposals", doc_id, {"decision": decision}, refuse=written))
        except store.Refused as e:
            self.send_json(409, {"error": str(e)})
        except store.StoreError as e:
            self.send_json(404, {"error": str(e)})


def make_server(db: str, host: str = "127.0.0.1", port: int = 47821) -> ThreadingHTTPServer:
    handler = type("ReviewHandler", (Handler,), {"db": db})
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("db")
    ap.add_argument("--port", type=int, default=47821)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    server = make_server(a.db, a.host, a.port)
    print(f"Review page: http://{a.host}:{a.port}  (Ctrl-C stops it, the items stay in {a.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
