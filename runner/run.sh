#!/bin/sh
# Do one project's run now, on this machine, in an interactive Claude Code session.
# Usage: runner/run.sh PROJECT, a folder name in projects/ such as acme, or a path with /
# Set CONTEXT_INBOX_TOOLS to the connector servers your guides use, such as
# "mcp__claude_ai_Linear mcp__claude_ai_Attio". Claude Code must be signed in
# with a claude.ai account, so the review page tools load.
set -eu
[ $# -eq 1 ] || { sed -n 2,6p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
case "$1" in */*) dir=$1 ;; *) dir="${CONTEXT_INBOX_PROJECTS:-$here/projects}/$1" ;; esac
project=$(cd "$dir" && pwd)
if ! python3 "$here/connector/check.py" "$project" > /dev/null; then
  echo "Config check failed. Fix the errors above, then run again." >&2
  exit 1
fi
prompt=$(sed "s#<project folder>#$project#" "$here/runner/prompt.txt")
settings=$(python3 "$here/runner/permissions.py" "$project")
cd "$here"
# runner/permissions.py lists what the run may start and what it may not touch.
# Anything else asks first, since the session reads messages written by outside people.
# Only this repo's settings load, so the person's own allow rules cannot widen the run's.
# CONTEXT_INBOX_MCP_CONFIG names the MCP server's registration file, which holds its keys and pins.
if [ -n "${CONTEXT_INBOX_MCP_CONFIG:-}" ]; then
  set -- --mcp-config "$CONTEXT_INBOX_MCP_CONFIG"
else
  set --
fi
exec claude "$prompt" --add-dir "$project" --settings "$settings" --setting-sources project "$@"
