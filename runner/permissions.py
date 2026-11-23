"""Print the Claude Code settings a daily run gets, as JSON for `claude --settings`.

Usage: python3 runner/permissions.py PROJECT_DIR

The run may start only the programs the config check names: each reader, the
download script beside a built-in reader, and the store's command line. It may
not edit this repo, those programs, the destinations' tools files or the review
store's file, so it cannot plant a script and start it. It may neither read nor
edit Claude Code's own settings, or the MCP server's registration file named by
CONTEXT_INBOX_MCP_CONFIG, where the destination keys and pins sit.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def rule_path(path) -> str:
    # In permission rules, "//" starts an absolute path.
    return "/" + str(Path(path).resolve())


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    project = Path(sys.argv[1]).resolve()
    out = subprocess.run(
        [sys.executable, str(HERE / "connector" / "check.py"), str(project)], capture_output=True, text=True
    )
    if out.returncode:
        sys.exit(out.stderr)
    checked = json.loads(out.stdout)
    programs = [HERE / "integrations" / "sqlite" / "store.py"]
    allow = [f"Bash(python3 {HERE / 'connector' / 'check.py'}:*)", f"Bash(python3 {programs[0]}:*)"]
    for source in checked["sources"]:
        run = (source.get("read") or {}).get("run")
        if not run:
            continue
        allow.append(f"Bash({' '.join(run)}:*)")
        reader = Path(run[-1])
        programs.append(reader)
        download = reader.parent / "download.py"
        if download.is_file() and HERE in download.parents:
            allow.append(f"Bash(python3 {download}:*)")
            programs.append(download)
    allow += [f"Bash(git {verb}:*)" for verb in ("log", "add", "commit", "pull", "push", "status")]
    allow += ["Read", "Write", "Edit", "Glob", "Grep", "ToolSearch", "ArtifactData", "mcp__context-inbox"]
    allow += os.environ.get("CONTEXT_INBOX_TOOLS", "").split()
    locked = [HERE / "**", project / "review.db", project / "review.db-*", *programs]
    locked += [d["tools_path"] for d in checked["destinations"] if d.get("tools_path")]
    deny = ["Read(~/.claude.json)", "Edit(~/.claude.json)", "Read(~/.claude/**)", "Edit(~/.claude/**)"]
    server_file = os.environ.get("CONTEXT_INBOX_MCP_CONFIG")
    if server_file:
        # The MCP server's registration holds the destination keys and pins.
        deny += [f"Read({rule_path(server_file)})", f"Edit({rule_path(server_file)})"]
    deny += [f"Edit({rule_path(p)})" for p in locked]
    # "default" asks the person before anything not allowed here, whatever their own settings say.
    print(json.dumps({"permissions": {"defaultMode": "default", "allow": allow, "deny": deny}}))


if __name__ == "__main__":
    main()
