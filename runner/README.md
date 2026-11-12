# Runner

- `run.sh PROJECTS_DIR PROJECT` (or `run.sh PROJECT_DIR`) checks the project's config, then opens an interactive Claude Code session that runs the daily run once. A session started with `claude -p` gets no review page tools, so the script does not use it. A config error prints the errors and stops before Claude starts, so no run log entry gets written.
- `prompt.txt` is the prompt for a scheduled run.

## Run on this machine

- Sign Claude Code in with a claude.ai account. The review page tools need it.
- The session may run, without asking, only the config check, the readers, and `git log`, `add`, `commit`, `pull`, `push` and `status`. Any other shell command asks you first. Messages come from outside people, so read what a command does before you allow it.
- Set `CONTEXT_INBOX_TOOLS` to the connector servers your guides use, such as `mcp__claude_ai_Linear mcp__claude_ai_Attio`, so the run may call them without asking.
- Set each source token in the env var named by its `secret`.

## Run on a schedule

Copy `prompt.txt`, replace `<projects repo>/<project>` with your project folder, and save it as a Claude Code scheduled task with a daily cron. Give it:

- context-inbox.
- Your projects repo, and every repo a guide writes to.
- Every connector your guides name.
- Each source token as a network secret for its API host.

A scheduled run starts one folder above the repos it clones, so the write check in `.claude/` does not load there. The run still writes only approved items, because step 1 of the daily run checks each one against the review page.

A scheduled run with a config error writes a run log entry with the errors and writes nothing else.

## Start a run from an agent or a script

`fire.sh PROJECTS_DIR PROJECT` (or `fire.sh PROJECT_DIR`) starts the project's scheduled task now and prints the link to the run. No person needs to watch.

- Put the task's id in `routine` in the project's `config.json`, such as `"routine": "trig_01ABC"`. `RemoteTrigger` with action `list` shows the ids, and so does the task's page on claude.ai.
- The script asks a background Claude Code session to start the task. That session needs a claude.ai sign-in and nothing else.
- `fire.sh PROJECTS_DIR PROJECT --check` only confirms the task exists and prints its schedule.
- For a caller with no Claude Code, such as an alert, add an API trigger to the task on the web, as [the scheduled tasks docs](https://code.claude.com/docs/en/routines#add-an-api-trigger) describe. Set `CONTEXT_INBOX_FIRE_URL` and `CONTEXT_INBOX_FIRE_TOKEN` to its Fire URL and token, outside git. `fire.sh` then calls that URL directly.

`run.sh` is for a person at the keyboard. A session started with `claude -p` cannot load the review page tools, so a script cannot use `run.sh`.
