#!/bin/sh
# Run one project's run now, without a person in the loop: push approved items,
# read new messages, propose items. For serve.py --every ... --run.
# Usage: runner/read-now.sh PROJECTS_DIR PROJECT, or runner/read-now.sh PROJECT_DIR
# Set CONTEXT_INBOX_TOOLS to the connector servers your guides use.
set -eu
[ $# -eq 1 ] || [ $# -eq 2 ] || { sed -n 2,6p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
projects=$(cd "$1${2:+/$2}" && pwd)
python3 "$here/connector/check.py" "$projects" > /dev/null || exit 1
prompt=$(sed "s#<projects repo>/<project>#$projects#" "$here/runner/prompt.txt")
cd "$here"
# runner/permissions.py lists what the run may start and what it may not touch. Only this repo's
# Claude Code settings load. CONTEXT_INBOX_MCP_CONFIG names the MCP server's registration file.
settings=$(python3 "$here/runner/permissions.py" "$projects")
if [ -n "${CONTEXT_INBOX_MCP_CONFIG:-}" ]; then set -- --mcp-config "$CONTEXT_INBOX_MCP_CONFIG"; else set --; fi
claude -p "$prompt" --add-dir "$projects" --settings "$settings" --setting-sources project "$@" \
  >> "$projects/read.log" 2>&1
