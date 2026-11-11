#!/bin/sh
# Start a project's scheduled cloud run now, with no person in the loop.
# Usage: runner/fire.sh PROJECTS_DIR PROJECT [--check]
# Reads the scheduled task id from "routine" in the project's config.json and
# starts it through Claude Code, which must be signed in with a claude.ai account.
# With CONTEXT_INBOX_FIRE_URL and CONTEXT_INBOX_FIRE_TOKEN set, it calls the
# task's API trigger instead and needs no Claude Code.
# --check only confirms the task exists and prints its schedule.
set -eu
[ $# -ge 2 ] || { sed -n 2,8p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
cfg="$1/$2/config.json"
id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("routine", ""))' "$cfg")
check=${3:-}

if [ -n "${CONTEXT_INBOX_FIRE_URL:-}" ] && [ -n "${CONTEXT_INBOX_FIRE_TOKEN:-}" ] && [ "$check" != "--check" ]; then
  out=$(curl -sS --fail-with-body -X POST "$CONTEXT_INBOX_FIRE_URL" \
    -H "Authorization: Bearer $CONTEXT_INBOX_FIRE_TOKEN" \
    -H "anthropic-beta: experimental-cc-routine-2026-04-01" \
    -H "anthropic-version: 2023-06-01" \
    -H "Content-Type: application/json" \
    -d '{}') || { echo "$out" >&2; exit 1; }
  printf '%s\n' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["claude_code_session_url"])'
  exit 0
fi

[ -n "$id" ] || { echo "Set \"routine\" in $cfg to the scheduled task id, such as trig_01ABC." >&2; exit 1; }
case "$id" in trig_*) ;; *) echo "\"routine\" must look like trig_01ABC." >&2; exit 1 ;; esac
if [ "$check" = "--check" ]; then
  ask="Call RemoteTrigger with action get and trigger_id $id. Reply with one line: OK, then its name and cron, or FAILED and the error."
else
  ask="Call RemoteTrigger with action run and trigger_id $id. Then call it with action list_runs and the same trigger_id. Reply with one line: the claude.ai link of the newest run, or FAILED and the error."
fi
cd "$here"
exec claude -p "$ask" --allowedTools ToolSearch RemoteTrigger < /dev/null
