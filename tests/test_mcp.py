import contextlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "integrations", "sqlite"))
import store  # noqa: E402


class FakeLinear(BaseHTTPRequestHandler):
    """Answers the few GraphQL calls the Linear writer makes, and remembers every call."""

    calls: list = []
    issues: list = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        q, v = body["query"], body["variables"]
        self.calls.append({"query": q, "variables": v, "auth": self.headers.get("Authorization")})
        if "searchIssues" in q:
            data = {"searchIssues": {"nodes": [i for i in self.issues if v["t"] in i["description"]]}}
        elif "teams" in q:
            data = {"teams": {"nodes": [{"id": "team-1"}] if v["k"] == "ACM" else []}}
        elif "issueCreate" in q:
            issue = {"url": f"https://linear.test/ACM-{len(self.issues) + 1}", "description": v["i"]["description"]}
            self.issues.append(issue)
            data = {"issueCreate": {"success": True, "issue": {"url": issue["url"]}}}
        else:
            data = None
        out = json.dumps({"data": data} if data else {"errors": [{"message": "unknown query"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


class McpTest(unittest.TestCase):
    def setUp(self):
        FakeLinear.calls, FakeLinear.issues = [], []
        self.linear = ThreadingHTTPServer(("127.0.0.1", 0), FakeLinear)
        threading.Thread(target=self.linear.serve_forever, daemon=True).start()
        self.addCleanup(self.linear.server_close)
        self.addCleanup(self.linear.shutdown)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.db = os.path.join(self.dir.name, "review.db")
        config = {
            "sources": [],
            "destinations": [
                {"id": "lin", "type": "linear", "guide": "linear", "team": "ACM", "secret": "TEST_LINEAR_KEY"},
                {"id": "crm", "type": "attio", "guide": "attio"},
            ],
        }
        with open(os.path.join(self.dir.name, "config.json"), "w") as f:
            json.dump(config, f)
        env = {
            **os.environ,
            "TEST_LINEAR_KEY": "lin_test_key",
            "LINEAR_API_URL": f"http://127.0.0.1:{self.linear.server_address[1]}",
        }
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(REPO, "server", "mcp.py"), self.dir.name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env,
        )
        self.addCleanup(self.proc.stdout.close)
        self.addCleanup(self.proc.wait)
        self.addCleanup(self.proc.stdin.close)
        self.n = 0
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
        self.assertEqual(init["serverInfo"]["name"], "context-inbox")
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")

    def rpc(self, method, params=None):
        self.n += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}) + "\n")
        self.proc.stdin.flush()
        reply = json.loads(self.proc.stdout.readline())
        self.assertEqual(reply["id"], self.n)
        return reply["result"]

    def tool(self, name, **args):
        r = self.rpc("tools/call", {"name": name, "arguments": args})
        t = r["content"][0]["text"]
        with contextlib.suppress(ValueError):
            t = json.loads(t)
        return t, r.get("isError", False)

    def item(self, doc_id="lin--1", **extra):
        return {
            "id": doc_id,
            "dest": "lin",
            "target": "linear",
            "action": "create_issue",
            "title": "T",
            "body": "Body",
            "citations": [],
            **extra,
        }

    def test_tools_offer_no_way_to_decide(self):
        names = [t["name"] for t in self.rpc("tools/list")["tools"]]
        self.assertIn("lin__search_issues", names)
        self.assertIn("push_approved", names)
        self.assertFalse([n for n in names if "decide" in n or "approve" in n.replace("push_approved", "")])

    def test_nothing_reaches_linear_without_approval(self):
        _, err = self.tool("propose", item=self.item(decision={"status": "approved"}, pushed={"url": "x"}))
        self.assertFalse(err)
        saved = store.get_doc(self.db, "proposals", "lin--1")
        self.assertNotIn("pushed", saved)
        self.assertNotIn("decision", saved)
        result, _ = self.tool("push_approved")
        self.assertEqual(result["written"], [])
        self.assertFalse([c for c in FakeLinear.calls if "issueCreate" in c["query"]])

    def test_approved_item_is_written_once_with_the_server_key(self):
        self.tool("propose", item=self.item())
        store.update_doc(self.db, "proposals", "lin--1", {"decision": {"status": "approved", "body": "Edited"}})
        result, _ = self.tool("push_approved")
        self.assertEqual(result["written"], [{"id": "lin--1", "url": "https://linear.test/ACM-1"}])
        create = [c for c in FakeLinear.calls if "issueCreate" in c["query"]]
        self.assertEqual(create[0]["variables"]["i"]["description"], "Edited\n\nctx: lin--1")
        self.assertEqual(create[0]["auth"], "lin_test_key")
        self.assertEqual(store.get_doc(self.db, "proposals", "lin--1")["pushed"]["url"], "https://linear.test/ACM-1")
        again, _ = self.tool("push_approved")
        self.assertEqual(again["written"], [])
        self.assertEqual(len(FakeLinear.issues), 1)

    def test_write_that_went_through_is_not_repeated(self):
        FakeLinear.issues.append({"url": "https://linear.test/ACM-9", "description": "old\n\nctx: lin--1"})
        self.tool("propose", item=self.item())
        store.update_doc(self.db, "proposals", "lin--1", {"decision": {"status": "approved"}})
        result, _ = self.tool("push_approved")
        self.assertEqual(result["written"][0]["url"], "https://linear.test/ACM-9")
        self.assertFalse([c for c in FakeLinear.calls if "issueCreate" in c["query"]])

    def test_decided_items_are_frozen(self):
        self.tool("propose", item=self.item())
        store.update_doc(self.db, "proposals", "lin--1", {"decision": {"status": "rejected"}})
        self.assertTrue(self.tool("propose", item=self.item(title="Changed"))[1])
        self.assertTrue(self.tool("withdraw", id="lin--1")[1])
        self.assertEqual(store.get_doc(self.db, "proposals", "lin--1")["title"], "T")

    def test_reviewer_answer_survives_a_rewrite(self):
        self.tool("propose", item=self.item(unsure=True))
        store.update_doc(self.db, "proposals", "lin--1", {"decision": {"status": "pending", "comment": "yes"}})
        self.tool("propose", item=self.item(unsure=False))
        self.assertEqual(store.get_doc(self.db, "proposals", "lin--1")["decision"]["comment"], "yes")

    def test_destination_without_writer_waits(self):
        self.tool("propose", item={**self.item("crm--1"), "dest": "crm", "action": "add_note"})
        store.update_doc(self.db, "proposals", "crm--1", {"decision": {"status": "approved"}})
        result, _ = self.tool("push_approved")
        self.assertEqual(result["approved_without_writer"][0]["id"], "crm--1")
        self.assertNotIn("pushed", store.get_doc(self.db, "proposals", "crm--1"))

    def test_cursors_runs_and_bad_input(self):
        self.tool("save_cursors", source="slack", cursors={"C1": "1"})
        self.assertEqual(self.tool("inbox_get", collection="state", id="slack")[0]["cursors"], {"C1": "1"})
        self.tool("log_run", run={"date": "2026-01-31T06:00:00Z", "errors": []})
        self.assertEqual(len(self.tool("inbox_list", collection="runs")[0]), 1)
        self.assertTrue(self.tool("propose", item={**self.item(), "dest": "nowhere"})[1])
        self.assertTrue(self.tool("lin__delete_everything")[1])
        self.assertTrue(self.tool("inbox_list", collection="secrets")[1])


if __name__ == "__main__":
    unittest.main()
