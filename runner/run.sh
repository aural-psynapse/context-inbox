#!/bin/sh
# Run one project's daily run now, on this machine, in an interactive Claude Code session.
# Usage: runner/run.sh PROJECTS_DIR PROJECT, or runner/run.sh PROJECT_DIR
# Set CONTEXT_INBOX_TOOLS to the connector servers your guides use, such as
# "mcp__claude_ai_Linear mcp__claude_ai_Attio". Claude Code must be signed in
# with a claude.ai account, so the review page tools load.
set -eu
[ $# -eq 1 ] || [ $# -eq 2 ] || { sed -n 2,6p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
projects=$(cd "$1${2:+/$2}" && pwd)
if ! python3 "$here/connector/check.py" "$projects" > /dev/null; then
  echo "Config check failed. Fix the errors above, then run again." >&2
  exit 1
fi
prompt=$(sed "s#<projects repo>/<project>#$projects#" "$here/runner/prompt.txt")
settings=$(python3 "$here/runner/permissions.py" "$projects")
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
exec claude "$prompt" --add-dir "$projects" --settings "$settings" --setting-sources project "$@"
