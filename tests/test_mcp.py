import contextlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "integrations", "sqlite"))
import store  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "server"))
import mcp  # noqa: E402

TOOLS = """
import json, os
from pathlib import Path

READ_TOOLS = [{"name": "find", "description": "Records holding the words.",
               "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}}}]


def _log(dest):
    return Path(dest["log"])


def _records(dest):
    p = _log(dest)
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def read(tool, args, dest):
    if args.get("q") == "boom":
        raise RuntimeError("the tool is down")
    return [r for r in _records(dest) if args.get("q", "") in r["text"]]


def write(item, dest):
    if os.environ.get(dest["secret"]) != "server-only-key":
        raise RuntimeError("no key")
    marker = "ctx: " + item["id"]
    for r in _records(dest):
        if marker in r["text"]:
            return r["url"]
    body = (item.get("decision") or {}).get("body") or item["body"]
    url = "https://tracker.test/" + str(len(_records(dest)) + 1)
    with _log(dest).open("a") as f:
        f.write(json.dumps({"url": url, "text": body + "\\n\\n" + marker}) + "\\n")
    return url
"""


class McpTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.db = os.path.join(self.dir.name, "review.db")
        self.log = os.path.join(self.dir.name, "tracker.jsonl")
        os.makedirs(os.path.join(self.dir.name, "tools"))
        with open(os.path.join(self.dir.name, "tools", "tracker.py"), "w") as f:
            f.write(TOOLS)
        config = {
            "sources": [],
            "destinations": [
                {"id": "lin", "type": "tracker", "tools": "tools/tracker.py", "secret": "TRACKER_KEY", "log": self.log},
                {"id": "crm", "type": "crm", "guide": "attio"},
            ],
        }
        with open(os.path.join(self.dir.name, "config.json"), "w") as f:
            json.dump(config, f)
        pin = mcp.pin_of(TOOLS.encode(), config["destinations"][0])
        env = {**os.environ, "TRACKER_KEY": "server-only-key", "CONTEXT_INBOX_PINS": json.dumps({"lin": pin})}
        self.start(env)

    def start(self, env):
        self.env = env
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(REPO, "server", "mcp.py"), self.dir.name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env,
        )
        self.addCleanup(self.stop, self.proc)
        self.n = 0
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
        self.assertEqual(init["serverInfo"]["name"], "context-inbox")
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")

    def stop(self, proc):
        proc.stdin.close()
        proc.wait()
        proc.stdout.close()

    def restart(self, env):
        self.stop(self.proc)
        self.start(env)

    def approve(self, doc_id, **extra):
        rev = store.get_doc(self.db, "proposals", doc_id).get("rev", "")
        store.write(self.db, "proposals", doc_id, store.page_change({"status": "approved", "rev": rev, **extra}))

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
            "target": "tracker",
            "action": "create",
            "title": "T",
            "body": "Body",
            "citations": [],
            **extra,
        }

    def test_tools_offer_no_way_to_decide(self):
        names = [t["name"] for t in self.rpc("tools/list")["tools"]]
        self.assertIn("lin__find", names)
        self.assertIn("push_approved", names)
        self.assertFalse([n for n in names if "decide" in n or "approve" in n.replace("push_approved", "")])

    def test_nothing_is_written_without_approval(self):
        _, err = self.tool("propose", item=self.item(decision={"status": "approved"}, pushed={"url": "x"}))
        self.assertFalse(err)
        saved = store.get_doc(self.db, "proposals", "lin--1")
        self.assertNotIn("pushed", saved)
        self.assertNotIn("decision", saved)
        result, _ = self.tool("push_approved")
        self.assertEqual(result["written"], [])
        self.assertFalse(os.path.exists(self.log))

    def records(self):
        with open(self.log) as f:
            return [json.loads(x) for x in f]

    def test_approved_item_is_written_once_with_the_server_key(self):
        self.tool("propose", item=self.item())
        self.approve("lin--1", body="Edited")
        result, _ = self.tool("push_approved")
        self.assertEqual(result["written"], [{"id": "lin--1", "url": "https://tracker.test/1"}])
        self.assertEqual(self.records()[0]["text"], "Edited\n\nctx: lin--1")
        self.assertEqual(store.get_doc(self.db, "proposals", "lin--1")["pushed"]["url"], "https://tracker.test/1")
        self.assertEqual(self.tool("lin__find", q="Edited")[0][0]["url"], "https://tracker.test/1")
        again, _ = self.tool("push_approved")
        self.assertEqual(again["written"], [])
        self.assertEqual(len(self.records()), 1)

    def test_write_that_went_through_is_not_repeated(self):
        with open(self.log, "w") as f:
            f.write(json.dumps({"url": "https://tracker.test/9", "text": "old\n\nctx: lin--1"}) + "\n")
        self.tool("propose", item=self.item())
        self.approve("lin--1")
        result, _ = self.tool("push_approved")
        self.assertEqual(result["written"][0]["url"], "https://tracker.test/9")
        self.assertEqual(len(self.records()), 1)

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
        self.approve("crm--1")
        result, _ = self.tool("push_approved")
        self.assertEqual(result["approved_without_writer"][0]["id"], "crm--1")
        self.assertNotIn("pushed", store.get_doc(self.db, "proposals", "crm--1"))

    def test_text_changed_before_the_click_is_not_written(self):
        self.tool("propose", item=self.item())
        seen = store.get_doc(self.db, "proposals", "lin--1")["rev"]
        self.tool("propose", item=self.item(body="Swapped in just before the click"))
        with self.assertRaises(store.Refused):
            store.write(self.db, "proposals", "lin--1", store.page_change({"status": "approved", "rev": seen}))
        self.assertEqual(self.tool("push_approved")[0]["written"], [])
        self.assertFalse(os.path.exists(self.log))

    def test_withdraw_and_propose_again_does_not_reuse_an_approval(self):
        self.tool("propose", item=self.item())
        seen = store.get_doc(self.db, "proposals", "lin--1")["rev"]
        self.tool("withdraw", id="lin--1")
        self.tool("propose", item=self.item(body="Swapped after a withdraw"))
        with self.assertRaises(store.Refused):
            store.write(self.db, "proposals", "lin--1", store.page_change({"status": "approved", "rev": seen}))
        self.assertFalse(os.path.exists(self.log))

    def test_destination_settings_changed_after_pinning_are_switched_off(self):
        cfg_path = os.path.join(self.dir.name, "config.json")
        with open(cfg_path) as f:
            cfg = json.load(f)
        cfg["destinations"][0]["log"] = os.path.join(self.dir.name, "elsewhere.jsonl")
        with open(cfg_path, "w") as f:
            json.dump(cfg, f)
        self.restart(self.env)
        self.tool("propose", item=self.item())
        self.approve("lin--1")
        result, _ = self.tool("push_approved")
        self.assertIn("changed since it was pinned", result["approved_without_writer"][0]["why"])
        self.assertFalse(os.path.exists(cfg["destinations"][0]["log"]))

    def test_item_saved_before_fingerprints_can_still_be_approved_and_written(self):
        store.set_doc(self.db, "proposals", "lin--1", {k: v for k, v in self.item().items() if k != "id"})
        store.write(self.db, "proposals", "lin--1", store.page_change({"status": "approved", "rev": ""}))
        result, _ = self.tool("push_approved")
        self.assertEqual(result["written"][0]["id"], "lin--1")

    def test_tools_file_changed_after_pinning_is_switched_off(self):
        with open(os.path.join(self.dir.name, "tools", "tracker.py"), "a") as f:
            f.write("\n# edited by a run\n")
        self.restart(self.env)
        names = [t["name"] for t in self.rpc("tools/list")["tools"]]
        self.assertNotIn("lin__find", names)
        self.tool("propose", item=self.item())
        self.approve("lin--1")
        result, _ = self.tool("push_approved")
        self.assertIn("changed since it was pinned", result["approved_without_writer"][0]["why"])
        self.assertFalse(os.path.exists(self.log))

    def test_bad_calls_answer_with_an_error_and_the_server_keeps_running(self):
        self.assertTrue(self.tool("lin__find", q="boom")[1])
        r = self.rpc("tools/call", {"name": "propose", "arguments": ["not", "an", "object"]})
        self.assertTrue(r["isError"])
        self.assertTrue(self.tool("propose", item={**self.item(), "dest": ["lin"]})[1])
        self.assertEqual(self.tool("inbox_list", collection="runs")[0], [])

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
