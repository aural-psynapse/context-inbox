# Runner

- `run.sh PROJECTS_DIR PROJECT` checks the project's config, then runs the daily run once with Claude Code on this machine. A config error prints the errors and stops before Claude starts, so no run log entry gets written.
- `prompt.txt` is the prompt for a scheduled run.

## Run on this machine

- Sign Claude Code in with a claude.ai account. The review page tools need it.
- The run may use the shell only for `python3` and `git`. Messages come from outside people, so a message that tries to give the agent orders cannot run other commands without asking.
- Set `CONTEXT_INBOX_TOOLS` to the connector servers your guides use, such as `mcp__claude_ai_Linear mcp__claude_ai_Attio`, so the run may call them without asking.
- Set each source token in the env var named by its `secret`.

## Run on a schedule

Save `prompt.txt` as a Claude Code routine with a daily cron. Give it:

- context-inbox as the first repo, so the session starts inside it and loads the write check in `.claude/`.
- Your projects repo, and every repo a guide writes to.
- Every connector your guides name.
- Each source token as a network secret for its API host.

A scheduled run with a config error writes a run log entry with the errors and writes nothing else.
