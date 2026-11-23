"""Context Inbox MCP server: the agent's only door to the review store and the destinations.

Usage (as an MCP server over stdio, standard library only):
  python3 server/mcp.py PROJECT_DIR [--db PATH]

PROJECT_DIR holds config.json. The items live in PROJECT_DIR/review.db unless
--db names another file. It is the same file integrations/sqlite/serve.py shows.

What the agent can do here:
- read the items, the run log and the saved cursors
- propose an item, change or withdraw one nobody has decided yet
- save cursors and log a run
- call each destination's read tools, named `<destination id>__<tool>`
- call push_approved, which writes every approved item that is not written yet

What the agent cannot do here: decide an item, or write to a destination
without an approval. A person decides on the review page. The keys for each
destination stay in this server's environment, in the env var the
destination's `secret` names, so the agent session never needs them.

A destination gets a writer when its integration folder holds `tools.py`.
Items for any other destination stay approved and unwritten here, and
push_approved lists them.
"""

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "integrations" / "sqlite"))
import store  # noqa: E402

PROTOCOL = "2025-06-18"
COLLECTIONS = {"type": "string", "enum": ["proposals", "state", "runs"]}
DOC_ID = {"type": "string", "pattern": r"^[A-Za-z0-9_.~:@+-]{1,200}$"}


def text(value, error: bool = False) -> dict:
    body = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
    return {"content": [{"type": "text", "text": body}], **({"isError": True} if error else {})}


def decided(doc: dict) -> bool:
    status = (doc.get("decision") or {}).get("status")
    return bool(doc.get("pushed")) or status in ("approved", "rejected")


def load_tools(path: Path):
    spec = importlib.util.spec_from_file_location(f"ci_tools_{path.parent.name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Server:
    def __init__(self, project: Path, db: str):
        self.project = project
        self.db = db
        self.config = json.loads((project / "config.json").read_text())
        self.dests: dict = {}
        for d in self.config.get("destinations", []):
            name = d.get("guide", d.get("type"))
            path = REPO / "integrations" / str(name) / "tools.py"
            self.dests[d["id"]] = {"config": d, "tools": load_tools(path) if path.is_file() else None}

    # -- tool list -----------------------------------------------------------

    def tool_list(self) -> list:
        tools = [
            {
                "name": "inbox_list",
                "description": "Every doc in one collection, each with its id: proposals, state (cursors) or runs.",
                "inputSchema": {
                    "type": "object",
                    "required": ["collection"],
                    "properties": {"collection": COLLECTIONS},
                },
            },
            {
                "name": "inbox_get",
                "description": "One doc from a collection, or null.",
                "inputSchema": {
                    "type": "object",
                    "required": ["collection", "id"],
                    "properties": {"collection": COLLECTIONS, "id": DOC_ID},
                },
            },
            {
                "name": "propose",
                "description": "Save an item for a person to review, in the shape RULES.md gives. Replaces an "
                "undecided item with the same id. Refuses a decided or written item. Drops any decision or pushed.",
                "inputSchema": {"type": "object", "required": ["item"], "properties": {"item": {"type": "object"}}},
            },
            {
                "name": "withdraw",
                "description": "Delete an item nobody has decided yet, such as one a reviewer's answer says is "
                "off topic. Refuses a decided or written item.",
                "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": DOC_ID}},
            },
            {
                "name": "save_cursors",
                "description": "Save where reading stopped for one source: { channel id: cursor }. Call it last "
                "in a run.",
                "inputSchema": {
                    "type": "object",
                    "required": ["source", "cursors"],
                    "properties": {"source": DOC_ID, "cursors": {"type": "object"}},
                },
            },
            {
                "name": "log_run",
                "description": "Write the run log entry: { date, counts, pushed, proposed, errors }. The id is date.",
                "inputSchema": {"type": "object", "required": ["run"], "properties": {"run": {"type": "object"}}},
            },
            {
                "name": "push_approved",
                "description": "Write every approved item that is not written yet to its destination, with the "
                "keys this server holds, and save where each went. Writes nothing that a person has not approved.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
        for dest_id, d in self.dests.items():
            for t in getattr(d["tools"], "READ_TOOLS", []) if d["tools"] else []:
                tools.append(
                    {
                        "name": f"{dest_id}__{t['name']}",
                        "description": f"{dest_id} ({d['config'].get('type')}), read only: {t['description']}",
                        "inputSchema": t["inputSchema"],
                    }
                )
        return tools

    # -- tool calls ----------------------------------------------------------

    def call(self, name: str, args: dict) -> dict:
        try:
            return self._call(name, args or {})
        except store.StoreError as e:
            return text(str(e), error=True)
        except ToolError as e:
            return text(str(e), error=True)

    def _call(self, name: str, a: dict) -> dict:
        if name == "inbox_list":
            return text(store.list_docs(self.db, a.get("collection", "")))
        if name == "inbox_get":
            return text(store.get_doc(self.db, a.get("collection", ""), str(a.get("id", ""))))
        if name == "propose":
            return self.propose(a.get("item"))
        if name == "withdraw":
            doc_id = str(a.get("id", ""))
            doc = store.get_doc(self.db, "proposals", doc_id)
            if not doc:
                raise ToolError(f"There is no item {doc_id!r}.")
            if decided(doc):
                raise ToolError(f"Item {doc_id!r} is decided or written. It can no longer change.")
            store.delete_doc(self.db, "proposals", doc_id)
            return text(f"Withdrew {doc_id}.")
        if name == "save_cursors":
            if not isinstance(a.get("cursors"), dict):
                raise ToolError("cursors must be an object of { channel id: cursor }.")
            store.set_doc(self.db, "state", str(a.get("source", "")), {"cursors": a["cursors"]})
            return text("Saved.")
        if name == "log_run":
            run = a.get("run")
            if not isinstance(run, dict) or not run.get("date"):
                raise ToolError("run must be an object with a date, such as 2026-01-31T06:00:00Z.")
            store.set_doc(self.db, "runs", str(run["date"]), run)
            return text("Logged.")
        if name == "push_approved":
            return text(self.push_approved())
        dest_id, _, tool = name.partition("__")
        d = self.dests.get(dest_id)
        if d and d["tools"] and any(t["name"] == tool for t in getattr(d["tools"], "READ_TOOLS", [])):
            return text(d["tools"].read(tool, a, d["config"]))
        raise ToolError(f"There is no tool {name!r}.")

    def propose(self, item) -> dict:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ToolError("item must be an object with an id, in the shape RULES.md gives.")
        if item.get("dest") not in self.dests:
            raise ToolError(f"dest must be one of: {', '.join(self.dests)}")
        old = store.get_doc(self.db, "proposals", item["id"])
        if old and decided(old):
            raise ToolError(
                f"Item {item['id']!r} is decided or written. Put the news in a new item, as AGENTS.md step 3 says."
            )
        doc = {k: v for k, v in item.items() if k not in ("id", "decision", "pushed")}
        if old and (old.get("decision") or {}).get("comment"):
            # Keep a reviewer's saved comment or answer when the run rewrites the item.
            doc["decision"] = {"status": "pending", "comment": old["decision"]["comment"]}
        store.set_doc(self.db, "proposals", item["id"], doc)
        return text(f"Saved {item['id']} for review.")

    def push_approved(self) -> dict:
        written, failed, waiting = [], [], []
        for item in store.list_docs(self.db, "proposals"):
            if item.get("pushed") or (item.get("decision") or {}).get("status") != "approved":
                continue
            d = self.dests.get(item.get("dest"))
            if not d or not d["tools"]:
                waiting.append({"id": item["id"], "why": f"destination {item.get('dest')!r} has no writer here"})
                continue
            try:
                url = d["tools"].write(item, d["config"])
            except Exception as e:  # one failed write must not stop the others
                failed.append({"id": item["id"], "error": str(e)})
                continue
            pushed = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "url": url}
            store.update_doc(self.db, "proposals", item["id"], {"pushed": pushed})
            written.append({"id": item["id"], "url": url})
        return {"written": written, "failed": failed, "approved_without_writer": waiting}


class ToolError(Exception):
    pass


def serve(server: Server, stdin=sys.stdin, stdout=sys.stdout) -> None:
    for line in stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "not JSON"}}
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()
            continue
        if "id" not in msg:
            continue  # a notification, such as notifications/initialized
        method, params = msg.get("method"), msg.get("params") or {}
        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion", PROTOCOL),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "context-inbox", "version": (REPO / "version.txt").read_text().strip()},
                "instructions": "Read freely. Propose changes with propose. Only push_approved writes to a "
                "destination, and only what a person approved on the review page.",
            }
        elif method == "tools/list":
            result = {"tools": server.tool_list()}
        elif method == "tools/call":
            result = server.call(params.get("name", ""), params.get("arguments") or {})
        elif method == "ping":
            result = {}
        else:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": f"no method {method}"}}
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()
            continue
        stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}, ensure_ascii=False) + "\n")
        stdout.flush()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--db")
    a = ap.parse_args()
    project = Path(a.project).resolve()
    serve(Server(project, a.db or str(project / "review.db")))


if __name__ == "__main__":
    main()
