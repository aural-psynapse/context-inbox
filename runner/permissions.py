"""Print the Claude Code settings a run gets, as JSON for `claude --settings`.

Usage: python3 runner/permissions.py PROJECT

PROJECT is a folder name in projects/, such as acme, or a path with "/".

The run may start only the programs the config check names: each reader, the
download script beside a built-in reader, and the store's command line. It may
not edit this repo outside its own project folder, those programs, the destinations' tools files or the review
store's file, so it cannot plant a script and start it. It may neither read nor
edit Claude Code's own settings, or the MCP server's registration file named by
CONTEXT_INBOX_MCP_CONFIG, where the destination keys and pins sit.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "connector"))
import check  # noqa: E402


def rule_paths(path) -> list:
    """Both spellings of an absolute path, as typed and with links resolved, such as /tmp and /private/tmp.

    A rule matches the path as the session writes it, so it needs each spelling. "//" starts an absolute path.
    """
    typed, real = os.path.abspath(path), os.path.realpath(path)
    return sorted({"/" + typed, "/" + real})


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    project = check.project_dir(sys.argv[1])
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
        # Python runs files beside the script first, such as a planted json.py, so lock the reader's folder.
        programs.append(reader.parent / "**" if Path(os.path.realpath(project)) in reader.parents else reader)
        download = reader.parent / "download.py"
        if download.is_file() and HERE in download.parents:
            allow.append(f"Bash(python3 {download}:*)")
            programs.append(download)
    configs = sorted({str(project / "config.json"), os.path.realpath(project / "config.json")})
    for dest in checked["destinations"]:
        guide = Path(dest.get("guide_path") or "")
        if guide.parent.parent != HERE / "integrations":
            continue
        for script in sorted(guide.parent.glob("*.py")):
            if script.name in ("reader.py", "download.py", "tools.py"):
                continue
            # A script whose first argument is CONFIG may run only with this project's config.
            pinned = re.search(r"Usage:\s*\n\s*python3 \S+ CONFIG\b", script.read_text())
            allow += [f"Bash(python3 {script} {c}:*)" for c in configs] if pinned else [f"Bash(python3 {script}:*)"]
    # No git: `git log --output=<file>` and similar would let the run overwrite any program above.
    # Writes go only to the project folder and the temporary folders. A file written anywhere else, such as
    # usercustomize.py in Python's user folder, could run inside a program that holds keys.
    writable = [project, Path(tempfile.gettempdir()), Path("/tmp")]
    allow += [f"Edit({r}/**)" for p in writable for r in rule_paths(p)]
    allow += ["Read", "Glob", "Grep", "ToolSearch", "ArtifactData", "mcp__context-inbox"]
    allow += os.environ.get("CONTEXT_INBOX_TOOLS", "").split()
    # The project folder sits inside this repo, in projects/. Lock the rest of the repo, sibling projects included.
    real = Path(os.path.realpath(project))
    projects = HERE / "projects"
    locked = [c / "**" if c.is_dir() else c for c in sorted(HERE.iterdir()) if c != projects]
    if projects == real.parent:
        locked += [c / "**" if c.is_dir() else c for c in sorted(projects.iterdir()) if c != real]
    elif projects not in real.parents:
        locked.append(projects / "**")
    locked += [project / "review.db", project / "review.db-*", *programs]
    locked += [d["tools_path"] for d in checked["destinations"] if d.get("tools_path")]
    deny = ["Read(~/.claude.json)", "Edit(~/.claude.json)", "Read(~/.claude/**)", "Edit(~/.claude/**)"]
    server_file = os.environ.get("CONTEXT_INBOX_MCP_CONFIG")
    if server_file:
        # The MCP server's registration holds the destination keys and pins.
        deny += [f"{tool}({r})" for tool in ("Read", "Edit") for r in rule_paths(server_file)]
    deny += [f"Edit({r})" for p in locked for r in rule_paths(p)]
    # "default" asks the person before anything not allowed here, whatever their own settings say.
    print(json.dumps({"permissions": {"defaultMode": "default", "allow": allow, "deny": deny}}))


if __name__ == "__main__":
    main()
