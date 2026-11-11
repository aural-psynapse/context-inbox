---
name: context-inbox-run
description: Run context-inbox once for one project: push approved items, read new messages, propose changes. Use when someone asks to run, sync or refresh the inbox now.
---

1. Run `python3 connector/check.py <projects repo> <project>`. Exit 1: report its errors and stop.
2. Follow "Daily run" in AGENTS.md, using the paths the check printed.
3. Report the counts from the runs doc you wrote.
