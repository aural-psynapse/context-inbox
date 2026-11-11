# Runner

- `run.sh PROJECTS_DIR PROJECT` checks the project with the connector, then runs the daily run once with Claude Code on this machine.
- `prompt.txt` is the prompt for a scheduled run. Save it as a Claude Code routine with a daily cron, the three repos it needs (context-inbox, your projects repo, any repo a guide writes to), and the connectors your guides name.

A run with a config error stops at the connector check and writes nothing.
