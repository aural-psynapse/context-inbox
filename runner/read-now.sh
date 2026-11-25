#!/bin/sh
# Run one project's run now, without a person in the loop: push approved items,
# read new messages, propose items. For serve.py --every ... --run.
# Usage: runner/read-now.sh PROJECT, a folder name in projects/ such as acme, or a path with /
# Set CONTEXT_INBOX_TOOLS to the connector servers your guides use.
set -eu
[ $# -eq 1 ] || { sed -n 2,6p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
case "$1" in */*) dir=$1 ;; *) dir="${CONTEXT_INBOX_PROJECTS:-$here/projects}/$1" ;; esac
project=$(cd "$dir" && pwd)
python3 "$here/connector/check.py" "$project" > /dev/null || exit 1
prompt=$(sed "s#<project folder>#$project#" "$here/runner/prompt.txt")
cd "$here"
# runner/permissions.py lists what the run may start and what it may not touch. Only this repo's
# Claude Code settings load. CONTEXT_INBOX_MCP_CONFIG names the MCP server's registration file.
settings=$(python3 "$here/runner/permissions.py" "$project")
if [ -n "${CONTEXT_INBOX_MCP_CONFIG:-}" ]; then set -- --mcp-config "$CONTEXT_INBOX_MCP_CONFIG"; else set --; fi
claude -p "$prompt" --add-dir "$project" --settings "$settings" --setting-sources project "$@" \
  >> "$project/read.log" 2>&1
