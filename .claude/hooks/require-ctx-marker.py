"""Claude Code PreToolUse hook: refuse a destination write that carries no ctx marker.

Every record a run writes carries `ctx: <item id>`. This hook checks that the
marker is present. It cannot check that the item was approved: the agent does
that in step 1 of the daily run, against the review page.

Checked:
- connector writes that create or change text: issues, comments, documents,
  notes, tasks, records, list entries
- `git commit` outside this repo: one line, marker, no trailers
- `gh issue|pr create|comment|edit` and `gh api` writes outside this repo

Refused outright: posting to chat, since a run never sends messages.

Not checked: field-only updates by record id, where every value is short and
on one line, such as a Linear state change, an Attio stage change or closing a
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
    r"create-comment|add-record-to-list|create-activity-record|upsert-activity-record|"
    r"save_status_update|save_release_note|create_draft)$"
)
TEXT_KEYS = {"description", "body", "content", "text", "title", "note", "message", "comment", "markdown"}


def has_text(v) -> bool:
    """True when any string inside looks like prose rather than an id or a state name."""
    if isinstance(v, str):
        return len(v) > 40 or "\n" in v
    if isinstance(v, dict):
        return any(has_text(x) for x in v.values())
    if isinstance(v, list):
        return any(has_text(x) for x in v)
    return False
GIT_COMMIT = re.compile(r"\bgit(\s+(-c\s+\S+|-C\s+\S+|--[\w-]+(=\S+)?))*\s+commit\b")
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
        field_only = isinstance(args, dict) and args.get("id") and not (TEXT_KEYS & set(args)) and not has_text(args)
        if WRITE_TOOLS.search(name) and not field_only and "ctx: " not in json.dumps(args, ensure_ascii=False):
            block(f"{name}: a run writes only approved items, and each carries `ctx: <item id>`. Add the marker or skip the write.")
        return
    if name != "Bash":
        return
    cmd = args.get("command", "")
    here = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR", ""))
    outside = os.path.realpath(call.get("cwd", "")) != here or re.search(r"\bcd\s|\bgit\s+(\S+\s+)*-C\s", cmd)
    gh_write = re.search(r"\bgh\s+(issue|pr)\s+(create|comment|edit)\b|\bgh\s+api\b[^|;&\n]*(-X\s*(POST|PATCH|PUT)|--method\s+(POST|PATCH|PUT)|\s-f\s)", cmd)
    if gh_write and (outside or re.search(r"\s(-R|--repo)[\s=]|\bgh\s+api\b", cmd)) and "ctx: " not in cmd:
        block("gh: a write needs `ctx: <item id>` in its body.")
    if not outside:
        return
    if GIT_COMMIT.search(cmd):
        if len(re.findall(r"(^|\s)(-m|--message)(\s|=)", cmd)) > 1 or re.search(r"-m\s+(\"[^\"]*\n|'[^']*\n)", cmd):
            block("git commit: one-line message only.")
        if re.search(r"\b(Co-Authored-By|Signed-off-by|Generated with)\b", cmd, re.I):
            block("git commit: destination commits carry no trailers.")
        if "ctx: " not in cmd:
            block("git commit: message must be `docs: <title> (ctx: <item id>)`.")


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
