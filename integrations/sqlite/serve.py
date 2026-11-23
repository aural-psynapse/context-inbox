"""Serve the review page and its items from one SQLite file.

Usage:
  python3 integrations/sqlite/serve.py DB [--port 47821] [--host 127.0.0.1]
      [--on-decide COMMAND] [--every MINUTES --run COMMAND]

Open http://127.0.0.1:47821 to review. Stop it with Ctrl-C. The items stay in
DB, and a run reads and writes DB with store.py whether this is up or not.

There is no login here. Everyone who can reach the address can approve, so
keep the default host, or put the address behind a login you already have.

The page can change one thing: the `decision` on an item that is not written
yet. It never sees the saved cursors.

--on-decide: after each saved decision, start COMMAND with the item id added as
its last argument, without waiting for it. runner/act.sh is the command that
pushes an approved item at once, or rewrites a draft from a typed instruction.

--every with --run: while the page is up, start COMMAND every MINUTES minutes, so
new messages become items without waiting for the daily run. A run still going
when the next one is due is left to finish; the next starts after it.
runner/read-now.sh is that command.
"""

import argparse
import json
import shlex
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402

PAGE = Path(__file__).resolve().parent.parent.parent / "ui" / "review.html"
MAX_BODY = 1_000_000


class Handler(BaseHTTPRequestHandler):
    db = ""
    on_decide: list = []

    def act(self, doc_id: str) -> None:
        """Start the on-decide command for one item and return at once."""
        if not self.on_decide:
            return
        try:
            subprocess.Popen([*self.on_decide, doc_id], stdin=subprocess.DEVNULL, start_new_session=True)
        except OSError as e:
            print(f"on-decide failed for {doc_id}: {e}", file=sys.stderr)

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

        try:
            saved = store.write(self.db, "proposals", doc_id, store.page_change(decision))
        except store.Refused as e:
            self.send_json(409, {"error": str(e)})
        except store.StoreError as e:
            self.send_json(404, {"error": str(e)})
        else:
            self.send_json(200, saved)
            if decision.get("status") in ("approved", "rejected") or decision.get("comment"):
                self.act(doc_id)


def run_every(minutes: float, command: str, stop: threading.Event) -> threading.Thread:
    """Start `command` now and then every `minutes`, one run at a time, until `stop` is set."""

    def loop() -> None:
        while not stop.is_set():
            started = time.monotonic()
            try:
                subprocess.run(shlex.split(command), stdin=subprocess.DEVNULL, check=False)
            except OSError as e:
                print(f"--run failed: {e}", file=sys.stderr)
            stop.wait(max(0.0, minutes * 60 - (time.monotonic() - started)))

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread


def make_server(db: str, host: str = "127.0.0.1", port: int = 47821, on_decide: str = "") -> ThreadingHTTPServer:
    handler = type("ReviewHandler", (Handler,), {"db": db, "on_decide": shlex.split(on_decide)})
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("db")
    ap.add_argument("--port", type=int, default=47821)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--on-decide", default="", help="command started with the item id after each decision")
    ap.add_argument("--every", type=float, help="minutes between runs of --run")
    ap.add_argument("--run", default="", help="command that reads new messages, such as runner/read-now.sh")
    a = ap.parse_args()
    if bool(a.every) != bool(a.run):
        ap.error("--every and --run go together")
    server = make_server(a.db, a.host, a.port, a.on_decide)
    stop = threading.Event()
    if a.run:
        run_every(a.every, a.run, stop)
    print(f"Review page: http://{a.host}:{a.port}  (Ctrl-C stops it, the items stay in {a.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
