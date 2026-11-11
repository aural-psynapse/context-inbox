"""Claude Code PreToolUse hook: refuse a destination write that carries no ctx marker.

Every record a run writes ends with `ctx: <item id>`, the id of an item approved
on the review page. A write without one did not come from an approved item, so
this hook stops it. Commits outside this repo need the marker too, and no trailers.
"""

import json
import os
import re
import sys

WRITE_TOOLS = re.compile(
    r"(save_issue|save_comment|create-note|update-note|create-task|update-task|"
    r"create-record|update-record|upsert-record|create-comment)$"
)


def main() -> None:
    call = json.load(sys.stdin)
    name = call.get("tool_name", "")
    args = call.get("tool_input", {})
    text = json.dumps(args, ensure_ascii=False)
    if name.startswith("mcp__") and WRITE_TOOLS.search(name) and "ctx: " not in text:
        sys.stderr.write(f"{name}: a run writes only approved items, and each ends with `ctx: <item id>`. Add the marker or skip the write.\n")
        sys.exit(2)
    if name == "Bash":
        cmd = args.get("command", "")
        here = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR", ""))
        in_this_repo = os.path.realpath(call.get("cwd", "")) == here and not re.search(r"\bcd\s|\bgit\s+-C\s", cmd)
        if re.search(r"\bgit\s+commit\b", cmd) and not in_this_repo:
            if re.search(r"Co-Authored-By|Claude-Session|Generated with", cmd, re.I):
                sys.stderr.write("git commit: destination commits carry no trailers.\n")
                sys.exit(2)
            if "ctx: " not in cmd:
                sys.stderr.write("git commit: message must be `docs: <title> (ctx: <item id>)`.\n")
                sys.exit(2)


if __name__ == "__main__":
    main()
