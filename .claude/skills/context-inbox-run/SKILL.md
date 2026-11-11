---
name: context-inbox-run
description: "Run context-inbox once for one project. It pushes approved items, reads new messages and proposes changes. Use when someone asks to run, sync or refresh the inbox now."
---

1. Run `python3 connector/check.py <projects repo> <project>`. Exit 1: write the run log entry with its errors, report them and stop.
2. Follow "Daily run" in AGENTS.md, using the paths the check printed.
3. Report the counts from the runs doc you wrote.

In a session with no review page tools, such as `claude -p` or another agent, run `runner/fire.sh <projects repo> <project>` instead. It starts the scheduled cloud run and prints its link.
