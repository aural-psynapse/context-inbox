# Runner

Every script takes `PROJECT`: a folder name in `projects/`, such as `acme`, or a path with `/`.

- `act.sh PROJECT ITEM_ID` writes one approved item now, or rewrites a draft from a typed comment. The local review page starts it after each decision: see "Act the moment a person decides" in [`integrations/sqlite/guide.md`](../integrations/sqlite/guide.md). It logs to `act.log` in the project folder.
- `read-now.sh PROJECT` does one run with no person watching. The local review page starts it every few minutes: see "New messages without waiting" in the same guide. It logs to `read.log` in the project folder.
- `run.sh PROJECT` checks the project's config, then opens an interactive Claude Code session that does one run. Use it with the `claude-artifact` review store, where a session started with `claude -p` gets no review page tools. A config error prints the errors and stops before Claude starts, so no run log entry gets written.
- `fire.sh PROJECT` starts the project's scheduled cloud run now. See "Run on a schedule" below.
- `prompt.txt` is the prompt each run starts with. `act-prompt.txt` is the one `act.sh` uses.

## Run on this machine

- With the `claude-artifact` review store, sign Claude Code in with a claude.ai account. The review page tools need it.
- The session may run, without asking, only the config check, the readers, the review store's command line and the scripts the guides name. [`permissions.py`](permissions.py) lists them. It may not run `git`. Any other shell command asks you first. Messages come from outside people, so read what a command does before you allow it.
- Set `CONTEXT_INBOX_TOOLS` to the connector servers your guides use, such as `mcp__claude_ai_Linear mcp__claude_ai_Attio`, so the run may call them without asking.
- Set each source token in the env var named by its `secret`.

## Run on a schedule

Only the `claude-artifact` review store needs this. A scheduled run happens in the cloud, so it needs a review store it can reach from there. The `sqlite` store lives in a file on one machine and runs from its review page instead.

Copy `prompt.txt`, replace `<project folder>` with your project folder, and save it as a Claude Code scheduled task with a daily cron. Give it:

- context-inbox.
- Your project folder as a private repo of its own. The cloud run clones context-inbox from GitHub, and `projects/` never goes there.
- Every repo a guide writes to.
- Every connector your guides name.
- Each source token as a network secret for its API host.

A scheduled run starts one folder above the repos it clones, so the write check in `.claude/` does not load there. The run still writes only approved items, because step 1 of a run checks each one against the review page.

A scheduled run with a config error writes a run log entry with the errors and writes nothing else.

## Start a run from an agent or a script

`fire.sh PROJECT` starts the project's scheduled task now and prints the link to the run. No person needs to watch.

- Put the task's id in `routine` in the project's `config.json`, such as `"routine": "trig_01ABC"`. `RemoteTrigger` with action `list` shows the ids, and so does the task's page on claude.ai.
- The script asks a background Claude Code session to start the task. That session needs a claude.ai sign-in and nothing else.
- `fire.sh PROJECT --check` only confirms the task exists and prints its schedule.
- For a caller with no Claude Code, such as an alert, add an API trigger to the task on the web, as [the scheduled tasks docs](https://code.claude.com/docs/en/routines#add-an-api-trigger) describe. Set `CONTEXT_INBOX_FIRE_URL` and `CONTEXT_INBOX_FIRE_TOKEN` to its Fire URL and token, outside git. `fire.sh` then calls that URL directly.

`run.sh` is for a person at the keyboard. A session started with `claude -p` cannot load the review page tools, so a script cannot use `run.sh`.
