#!/bin/sh
# Act on one item the moment a person decides on the review page.
# Usage: runner/act.sh PROJECTS_DIR PROJECT ITEM_ID, or runner/act.sh PROJECT_DIR ITEM_ID
# serve.py --on-decide "runner/act.sh PROJECTS_DIR PROJECT" adds the item id itself.
# An approved item is written to its destination now. A draft with a typed instruction
# is rewritten now, and the review page shows the new text within 5 seconds.
# Set CONTEXT_INBOX_TOOLS to the connector servers your guides use.
set -eu
[ $# -eq 2 ] || [ $# -eq 3 ] || { sed -n 2,7p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
if [ $# -eq 3 ]; then projects=$(cd "$1/$2" && pwd); item=$3; else projects=$(cd "$1" && pwd); item=$2; fi
log="$projects/act.log"
prompt=$(sed -e "s#<projects repo>/<project>#$projects#" -e "s#<item id>#$item#" "$here/runner/act-prompt.txt")
cd "$here"
echo "$(date -u +%FT%TZ) start $item" >> "$log"
# runner/permissions.py lists what the run may start and what it may not touch. Only this repo's
# Claude Code settings load. CONTEXT_INBOX_MCP_CONFIG names the MCP server's registration file.
settings=$(python3 "$here/runner/permissions.py" "$projects")
if [ -n "${CONTEXT_INBOX_MCP_CONFIG:-}" ]; then set -- --mcp-config "$CONTEXT_INBOX_MCP_CONFIG"; else set --; fi
claude -p "$prompt" --add-dir "$projects" --settings "$settings" --setting-sources project "$@" \
  >> "$log" 2>&1 && echo "$(date -u +%FT%TZ) done $item" >> "$log" \
  || echo "$(date -u +%FT%TZ) failed $item" >> "$log"
