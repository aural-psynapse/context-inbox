#!/bin/sh
# Act on one item the moment a person decides on the review page.
# Usage: runner/act.sh PROJECT ITEM_ID. PROJECT is a folder name in projects/, such as acme, or a path with /.
# serve.py --on-decide "runner/act.sh PROJECT" adds the item id itself.
# An approved item is written to its destination now. A draft with a typed instruction
# is rewritten now, and the review page shows the new text within 5 seconds.
# Set CONTEXT_INBOX_TOOLS to the connector servers your guides use.
set -eu
[ $# -eq 2 ] || { sed -n 2,7p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
case "$1" in */*) dir=$1 ;; *) dir="${CONTEXT_INBOX_PROJECTS:-$here/projects}/$1" ;; esac
project=$(cd "$dir" && pwd)
item=$2
log="$project/act.log"
prompt=$(sed -e "s#<project folder>#$project#" -e "s#<item id>#$item#" "$here/runner/act-prompt.txt")
cd "$here"
echo "$(date -u +%FT%TZ) start $item" >> "$log"
# runner/permissions.py lists what the run may start and what it may not touch. Only this repo's
# Claude Code settings load. CONTEXT_INBOX_MCP_CONFIG names the MCP server's registration file.
settings=$(python3 "$here/runner/permissions.py" "$project")
if [ -n "${CONTEXT_INBOX_MCP_CONFIG:-}" ]; then set -- --mcp-config "$CONTEXT_INBOX_MCP_CONFIG"; else set --; fi
claude -p "$prompt" --add-dir "$project" --settings "$settings" --setting-sources project "$@" \
  >> "$log" 2>&1 && echo "$(date -u +%FT%TZ) done $item" >> "$log" \
  || echo "$(date -u +%FT%TZ) failed $item" >> "$log"
