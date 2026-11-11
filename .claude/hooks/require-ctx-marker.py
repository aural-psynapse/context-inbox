"""Claude Code PreToolUse hook: refuse a destination write that carries no ctx marker.

Every record a run writes carries `ctx: <item id>`. This hook checks that the
marker is present. It cannot check that the item was approved: the agent does
that in step 1 of the daily run, against the review page.

Checked:
- connector writes that create or change text: issues, comments, documents,
  notes, tasks, records, list entries
- `git commit` outside this repo: one line, marker, no trailers
- `gh issue|pr create|comment|edit` and `gh api` writes

Refused outright: posting to chat, since a run never sends messages.

Not checked: field-only updates such as an Attio stage change or closing a
task. They carry no text for a marker. Guides pair each one with a note that
carries it. `git push` is not checked; the commit before it is.
"""

import json
import os
import re
import sys

WRITE_TOOLS = re.compile(
    r"(save_issue|save_comment|save_document|save_project|create_attachment|"
    r"create-note|update-note|create-task|create-record|upsert-record|"
    r"create-comment|add-record-to-list|create-activity-record|upsert-activity-record)$"
)
CHAT_SEND = re.compile(r"(send_message|schedule_message|send_message_draft|chat_postMessage)$")


def block(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.exit(2)


def check(call: dict) -> None:
    name = call.get("tool_name", "")
    args = call.get("tool_input", {}) or {}
    if name.startswith("mcp__"):
        if CHAT_SEND.search(name):
            block(f"{name}: a run never posts to chat.")
        if WRITE_TOOLS.search(name) and "ctx: " not in json.dumps(args, ensure_ascii=False):
            block(f"{name}: a run writes only approved items, and each carries `ctx: <item id>`. Add the marker or skip the write.")
        return
    if name != "Bash":
        return
    cmd = args.get("command", "")
    here = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR", ""))
    outside = os.path.realpath(call.get("cwd", "")) != here or re.search(r"\bcd\s|\bgit\s+(\S+\s+)*-C\s", cmd)
    if re.search(r"\bgit\b[^|;&\n]*\bcommit\b", cmd) and outside:
        if len(re.findall(r"(^|\s)(-m|--message)(\s|=)", cmd)) > 1 or re.search(r"-m\s+(\"[^\"]*\n|'[^']*\n)", cmd):
            block("git commit: one-line message only.")
        if re.search(r"\b(Co-Authored-By|Signed-off-by|Generated with)\b", cmd, re.I):
            block("git commit: destination commits carry no trailers.")
        if "ctx: " not in cmd:
            block("git commit: message must be `docs: <title> (ctx: <item id>)`.")
    if re.search(r"\bgh\s+(issue|pr)\s+(create|comment|edit)\b|\bgh\s+api\b[^|;&\n]*(-X\s*(POST|PATCH|PUT)|--method\s+(POST|PATCH|PUT)|\s-f\s)", cmd) and "ctx: " not in cmd:
        block("gh: a write needs `ctx: <item id>` in its body.")


def main() -> None:
    try:
        call = json.load(sys.stdin)
    except ValueError as e:
        block(f"require-ctx-marker: could not read the tool call ({e}).")
    try:
        check(call)
    except SystemExit:
        raise
    except Exception as e:  # fail closed: a broken check must not let writes through
        block(f"require-ctx-marker: check failed ({e}).")


if __name__ == "__main__":
    main()
