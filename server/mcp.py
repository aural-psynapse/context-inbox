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

A destination gets read tools and a writer when config sets its `tools`: an
integration name (integrations/<name>/tools.py) or a path to a Python file in
the project folder. AGENTS.md says what that file holds. Approved items for a
destination without `tools` stay unwritten here, and push_approved lists them.

The server runs a destination only when the SHA-256 of its tools file and its
settings in config.json matches the pin a person set in CONTEXT_INBOX_PINS, a
JSON object { destination id: sha256 } in the server's environment. A run that
edits either one therefore switches that destination off until a person reads
them and pins them again.
  python3 server/mcp.py PROJECT_DIR --print-pins   prints the current hashes
"""

import argparse
import hashlib
import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "integrations" / "sqlite"))
sys.path.insert(0, str(REPO / "connector"))
import check  # noqa: E402
import store  # noqa: E402

PROTOCOL = "2025-06-18"
COLLECTIONS = {"type": "string", "enum": ["proposals", "state", "runs"]}
DOC_ID = {"type": "string", "pattern": r"^[A-Za-z0-9_.~:@+-]{1,200}$"}


def text(value, error: bool = False) -> dict:
    body = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
    return {"content": [{"type": "text", "text": body}], **({"isError": True} if error else {})}


def tools_path(project: Path, value) -> Path:
    """The same rule connector/check.py uses: a value with "/" or a file extension is a path in the project folder."""
    if not isinstance(value, str) or not value:
        raise ToolError("tools must be an integration name or a path in the project folder")
    if check.is_path(value):
        path = (project / value).resolve()
        if project.resolve() not in path.parents:
            raise ToolError(f"tools {value!r} points outside the project folder")
    else:
        path = REPO / "integrations" / value / "tools.py"
    if not path.is_file():
        raise ToolError(f"tools not found at {path}")
    return path


def pin_of(code: bytes, dest: dict) -> str:
    settings = json.dumps(dest, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(code + b"\0" + settings).hexdigest()


def load_tools(path: Path, dest: dict, pin) -> types.ModuleType:
    """Run the file only when its bytes and the destination's settings match the pin, and run exactly those bytes."""
    code = path.read_bytes()
    digest = pin_of(code, dest)
    if pin != digest:
        why = "has no pin" if not pin else "changed since it was pinned"
        raise ToolError(
            f"{path} or its destination settings {why}. A person reads both, then pins {digest} in CONTEXT_INBOX_PINS."
        )
    module = types.ModuleType(f"ci_tools_{digest[:12]}")
    module.__file__ = str(path)
    exec(compile(code, str(path), "exec"), module.__dict__)
    return module


class Server:
    def __init__(self, project: Path, db: str):
        self.project = project
        self.db = db
        self.config = json.loads((project / "config.json").read_text())
        pins = json.loads(os.environ.get("CONTEXT_INBOX_PINS") or "{}")
        self.dests: dict = {}
        for d in self.config.get("destinations", []):
            entry = {"config": d, "tools": None, "problem": "no tools file in config"}
            if d.get("tools"):
                try:
                    entry["tools"] = load_tools(tools_path(project, d["tools"]), d, pins.get(d["id"]))
                    entry["problem"] = None
                except Exception as e:  # one broken tools file switches off its destination, not the server
                    entry["problem"] = str(e)
            self.dests[d["id"]] = entry

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

    def call(self, name: str, args) -> dict:
        if not isinstance(args, dict):
            return text("arguments must be an object.", error=True)
        try:
            return self._call(name, args)
        except Exception as e:  # a bad call or a failing read tool answers with an error, never stops the server
            return text(
                f"{type(e).__name__}: {e}" if not isinstance(e, (ToolError, store.StoreError)) else str(e), True
            )

    def _call(self, name: str, a: dict) -> dict:
        if name == "inbox_list":
            return text(store.list_docs(self.db, a.get("collection", "")))
        if name == "inbox_get":
            return text(store.get_doc(self.db, a.get("collection", ""), str(a.get("id", ""))))
        if name == "propose":
            return self.propose(a.get("item"))
        if name == "withdraw":
            doc_id = str(a.get("id", ""))
            store.write(self.db, "proposals", doc_id, store.agent_change("delete"))
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
        if not isinstance(item.get("dest"), str) or item["dest"] not in self.dests:
            raise ToolError(f"dest must be one of: {', '.join(self.dests)}")
        doc = {k: v for k, v in item.items() if k not in ("id", "decision", "pushed", "rev")}

        def change(old):
            if old and not store.decided(old) and (old.get("decision") or {}).get("comment"):
                # Keep a reviewer's saved comment or answer when the run rewrites the item.
                doc["decision"] = {"status": "pending", "comment": old["decision"]["comment"]}
            return store.agent_change("set", doc)(old)

        store.write(self.db, "proposals", item["id"], change)
        return text(f"Saved {item['id']} for review.")

    def push_approved(self) -> dict:
        written, failed, waiting = [], [], []
        for item in store.list_docs(self.db, "proposals"):
            decision = item.get("decision") or {}
            if item.get("pushed") or decision.get("status") != "approved":
                continue
            if str(decision.get("rev", "")) != str(item.get("rev", "")) or item.get("rev") != store.text_rev(item):
                failed.append({"id": item["id"], "error": "the text changed after the approval. Nothing written."})
                continue
            d = self.dests.get(item.get("dest"))
            if not d or not d["tools"]:
                why = d["problem"] if d else f"destination {item.get('dest')!r} is not in config"
                waiting.append({"id": item["id"], "why": why})
                continue
            try:
                url = d["tools"].write(item, d["config"])
            except Exception as e:  # one failed write must not stop the others
                failed.append({"id": item["id"], "error": str(e)})
                continue
            pushed = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "url": url}
            store.write(self.db, "proposals", item["id"], store.agent_change("update", {"pushed": pushed}))
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
    ap.add_argument("--print-pins", action="store_true", help="print each tools file's sha256 for CONTEXT_INBOX_PINS")
    a = ap.parse_args()
    project = Path(a.project).resolve()
    if a.print_pins:
        dests = json.loads((project / "config.json").read_text()).get("destinations", [])
        pins = {d["id"]: pin_of(tools_path(project, d["tools"]).read_bytes(), d) for d in dests if d.get("tools")}
        print(json.dumps(pins))
        return
    serve(Server(project, a.db or str(project / "review.db")))


if __name__ == "__main__":
    main()
