import json
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, ".claude", "hooks", "require-ctx-marker.py")
GH = "g" + "h"


def run(call):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=REPO)
    data = call if isinstance(call, str) else json.dumps(call)
    return subprocess.run([sys.executable, HOOK], input=data, text=True, capture_output=True, env=env).returncode


def bash(cmd, cwd="/tmp"):
    return {"tool_name": "Bash", "cwd": cwd, "tool_input": {"command": cmd}}


class HookTest(unittest.TestCase):
    def test_cases(self):
        cases = [
            ("write without marker", 2, {"tool_name": "mcp__L__save_issue", "tool_input": {"description": "x"}}),
            (
                "write with marker",
                0,
                {"tool_name": "mcp__L__save_issue", "tool_input": {"description": "x\nctx: a--1"}},
            ),
            (
                "field-only update",
                0,
                {"tool_name": "mcp__L__save_issue", "tool_input": {"id": "ABC-1", "state": "Done"}},
            ),
            (
                "text under another key",
                2,
                {
                    "tool_name": "mcp__A__upsert-record",
                    "tool_input": {
                        "id": "r1",
                        "values": {"notes": "Customer says the renewal slips to March because legal is slow"},
                    },
                },
            ),
            ("list entry", 2, {"tool_name": "mcp__A__add-record-to-list", "tool_input": {}}),
            ("chat post", 2, {"tool_name": "mcp__S__slack_send_message", "tool_input": {"text": "ctx: a"}}),
            ("git -C commit", 2, bash("git -C ../docs commit -m 'docs: x'", REPO)),
            ("git -c commit", 2, bash("git -c user.name=x commit -m 'docs: x'")),
            ("two messages", 2, bash("git commit -m 'docs: x (ctx: a)' -m 'body'")),
            ("trailer", 2, bash("git commit -m 'docs: x (ctx: a) Co-Authored-By: z'")),
            ("good commit", 0, bash("git commit -m 'docs: x (ctx: a)'")),
            ("commit in this repo", 0, bash("git commit -m 'fix: y'", REPO)),
            ("log grep", 0, bash("git log --grep commit")),
            ("issue create", 2, bash(GH + " issue create -t x -b y")),
            ("issue create from repo with -R", 2, bash(GH + " issue create -R acme/docs -t x -b y", REPO)),
            ("api write from repo", 2, bash(GH + " api -X POST repos/acme/docs/issues -f title=x", REPO)),
            ("api read", 0, bash(GH + " api repos/a/b")),
            ("pr in this repo", 0, bash(GH + " pr create -t x -b y", REPO)),
            ("plain command", 0, bash("ls")),
            ("bad input", 2, "nope"),
        ]
        for label, want, call in cases:
            with self.subTest(label):
                self.assertEqual(run(call), want)


if __name__ == "__main__":
    unittest.main()
