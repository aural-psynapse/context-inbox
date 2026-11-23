import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE = os.path.join(REPO, "integrations", "sqlite")
STORE = os.path.join(SQLITE, "store.py")
sys.path.insert(0, SQLITE)
import serve  # noqa: E402


def cli(db, *args, stdin=None):
    r = subprocess.run(
        [sys.executable, STORE, db, *args],
        input=json.dumps(stdin) if stdin is not None else None,
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout, r.stderr


class StoreCliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.db = os.path.join(self.dir.name, "review.db")

    def test_set_get_list_delete(self):
        self.assertEqual(cli(self.db, "set", "proposals", "d--1", stdin={"title": "A", "body": "x"})[0], 0)
        self.assertEqual(
            json.loads(cli(self.db, "get", "proposals", "d--1")[1]),
            {"title": "A", "body": "x", "rev": serve.store.text_rev({"title": "A", "body": "x"}), "id": "d--1"},
        )
        self.assertEqual([d["id"] for d in json.loads(cli(self.db, "list", "proposals")[1])], ["d--1"])
        self.assertEqual(cli(self.db, "delete", "proposals", "d--1")[0], 0)
        self.assertEqual(json.loads(cli(self.db, "get", "proposals", "d--1")[1]), None)

    def test_update_keeps_other_keys(self):
        serve.store.set_doc(self.db, "proposals", "d--1", {"title": "A", "decision": {"status": "approved"}})
        self.assertEqual(cli(self.db, "update", "proposals", "d--1", stdin={"pushed": {"url": "u"}})[0], 0)
        doc = json.loads(cli(self.db, "get", "proposals", "d--1")[1])
        self.assertEqual(doc["decision"], {"status": "approved"})
        self.assertEqual(doc["pushed"], {"url": "u"})

    def test_set_replaces_whole_doc(self):
        cli(self.db, "set", "state", "slack", stdin={"cursors": {"C1": "1"}, "extra": 1})
        cli(self.db, "set", "state", "slack", stdin={"cursors": {"C1": "2"}})
        self.assertEqual(json.loads(cli(self.db, "get", "state", "slack")[1]), {"cursors": {"C1": "2"}, "id": "slack"})

    def test_pushed_only_on_an_approved_item(self):
        self.assertNotEqual(
            cli(self.db, "set", "proposals", "d--1", stdin={"title": "A", "pushed": {"url": "u"}})[0], 0
        )
        cli(self.db, "set", "proposals", "d--1", stdin={"title": "A"})
        self.assertNotEqual(cli(self.db, "update", "proposals", "d--1", stdin={"pushed": {"url": "u"}})[0], 0)
        self.assertNotIn("pushed", serve.store.get_doc(self.db, "proposals", "d--1"))

    def test_command_line_never_sets_publishing(self):
        self.assertNotEqual(
            cli(self.db, "set", "proposals", "d--1", stdin={"title": "A", "publishing": {"version": "1"}})[0], 0
        )

    def test_command_line_never_decides(self):
        self.assertNotEqual(cli(self.db, "set", "proposals", "d--1", stdin={"decision": {"status": "approved"}})[0], 0)
        cli(self.db, "set", "proposals", "d--1", stdin={"title": "A"})
        self.assertNotEqual(
            cli(self.db, "update", "proposals", "d--1", stdin={"decision": {"status": "rejected"}})[0], 0
        )
        ok = {"title": "A", "decision": {"status": "pending", "comment": "answer"}}
        self.assertEqual(cli(self.db, "set", "proposals", "d--1", stdin=ok)[0], 0)
        rev = serve.store.get_doc(self.db, "proposals", "d--1")["rev"]
        serve.store.update_doc(self.db, "proposals", "d--1", {"decision": {"status": "approved", "rev": rev}})
        self.assertNotEqual(cli(self.db, "set", "proposals", "d--1", stdin={"title": "B"})[0], 0)
        self.assertNotEqual(cli(self.db, "delete", "proposals", "d--1")[0], 0)
        self.assertEqual(cli(self.db, "update", "proposals", "d--1", stdin={"pushed": {"url": "u"}})[0], 0)
        self.assertNotEqual(cli(self.db, "update", "proposals", "d--1", stdin={"pushed": {"url": "v"}})[0], 0)

    def test_errors(self):
        bad = {
            "update missing doc": (("update", "proposals", "nope"), {"a": 1}),
            "unknown collection": (("set", "proposal", "x"), {"a": 1}),
            "doc not an object": (("set", "proposals", "x"), [1]),
            "list with an id": (("list", "proposals", "x"), None),
            "get with no id": (("get", "proposals"), None),
        }
        for label, (args, stdin) in bad.items():
            with self.subTest(label):
                code, _, err = cli(self.db, *args, stdin=stdin)
                self.assertNotEqual(code, 0)
                self.assertNotIn("Traceback", err)


class ServeTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.db = os.path.join(self.dir.name, "review.db")
        self.server = serve.make_server(self.db, port=0)
        self.server.RequestHandlerClass.log_message = lambda *a: None
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def call(self, path, method="GET", body=None, headers=None):
        req = urllib.request.Request(
            self.base + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_page_is_the_review_page(self):
        status, body = self.call("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<title>Context Inbox</title>", body)

    def test_page_never_gets_cursors_and_has_no_login(self):
        serve.store.set_doc(self.db, "state", "slack", {"cursors": {"C1": "1"}})
        self.assertEqual(self.call("/api/state")[0], 404)
        self.assertEqual(self.call("/api/me"), (200, b"{}"))

    def test_decide(self):
        serve.store.set_doc(self.db, "proposals", "d--1", {"title": "A", "body": "x"})
        status, _ = self.call("/api/proposals/d--1", "PATCH", {"decision": {"status": "approved"}, "body": "hacked"})
        self.assertEqual(status, 200)
        items = json.loads(self.call("/api/proposals")[1])
        rev = serve.store.text_rev({"title": "A", "body": "x"})
        expected = {"title": "A", "body": "x", "rev": rev, "decision": {"status": "approved", "rev": rev}, "id": "d--1"}
        self.assertEqual(items, [expected])

    def test_written_item_is_locked(self):
        serve.store.set_doc(self.db, "proposals", "d--1", {"title": "A", "pushed": {"url": "u"}})
        self.assertEqual(self.call("/api/proposals/d--1", "PATCH", {"decision": {"status": "rejected"}})[0], 409)
        self.assertNotIn("decision", serve.store.get_doc(self.db, "proposals", "d--1"))

    def test_refused_requests(self):
        serve.store.set_doc(self.db, "proposals", "d--1", {"title": "A"})
        ok = {"decision": {"status": "approved"}}
        self.assertEqual(self.call("/api/proposals/nope", "PATCH", ok)[0], 404)
        self.assertEqual(self.call("/api/proposals/d--1", "PATCH", {"status": "approved"})[0], 400)
        self.assertEqual(self.call("/api/proposals/d--1", "PATCH", ok, {"Origin": "https://elsewhere.test"})[0], 403)
        self.assertEqual(self.call("/api/runs/x", "PATCH", ok)[0], 404)
        self.assertNotIn("decision", serve.store.get_doc(self.db, "proposals", "d--1"))

    def test_runs_newest_first_and_capped(self):
        for day in range(1, 32):
            serve.store.set_doc(self.db, "runs", f"2026-01-{day:02d}", {"date": f"2026-01-{day:02d}T06:00:00Z"})
        runs = json.loads(self.call("/api/runs")[1])
        self.assertEqual(len(runs), 30)
        self.assertEqual(runs[0]["id"], "2026-01-31")


if __name__ == "__main__":
    unittest.main()


class OnDecideTest(unittest.TestCase):
    def test_each_decision_starts_the_command_with_the_item_id(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        db = os.path.join(d.name, "review.db")
        log = os.path.join(d.name, "acted.txt")
        script = os.path.join(d.name, "act.sh")
        with open(script, "w") as f:
            f.write(f'#!/bin/sh\necho "$1" >> {log}\n')
        os.chmod(script, 0o755)
        server = serve.make_server(db, port=0, on_decide=script)
        server.RequestHandlerClass.log_message = lambda *a: None
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}/api/proposals/"
        for item in ("a", "b", "c"):
            serve.store.set_doc(db, "proposals", item, {"title": item})

        def patch(item, decision):
            req = urllib.request.Request(base + item, method="PATCH", data=json.dumps({"decision": decision}).encode())
            urllib.request.urlopen(req).read()

        patch("a", {"status": "approved"})
        patch("b", {"status": "pending", "comment": "make it shorter"})
        patch("c", {"status": "pending"})
        for _ in range(50):
            if os.path.exists(log) and len(Path(log).read_text().split()) == 2:
                break
            time.sleep(0.05)
        self.assertEqual(sorted(Path(log).read_text().split()), ["a", "b"])


class RunEveryTest(unittest.TestCase):
    def test_runs_now_and_again_until_stopped(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        log = os.path.join(d.name, "runs.txt")
        script = os.path.join(d.name, "read.sh")
        with open(script, "w") as f:
            f.write(f"#!/bin/sh\necho run >> {log}\n")
        os.chmod(script, 0o755)
        stop = threading.Event()

        thread = serve.run_every(0.002, script, stop)
        time.sleep(0.5)
        stop.set()
        thread.join(2)

        self.assertGreaterEqual(len(Path(log).read_text().split()), 2)
        self.assertFalse(thread.is_alive())
