#!/bin/sh
# Run one project's daily run now, on this machine.
# Usage: runner/run.sh PROJECTS_DIR PROJECT
# Set CONTEXT_INBOX_TOOLS to the connector servers your guides use, such as
# "mcp__claude_ai_Linear mcp__claude_ai_Attio". Claude Code must be signed in
# with a claude.ai account, so the review page tools load.
set -eu
[ $# -eq 2 ] || { sed -n 2,6p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
projects=$(cd "$1" && pwd)
if ! python3 "$here/connector/check.py" "$projects" "$2" > /dev/null; then
  echo "Config check failed. Fix the errors above, then run again." >&2
  exit 1
fi
prompt=$(sed "s#<projects repo>/<project>#$projects/$2#" "$here/runner/prompt.txt")
cd "$here"
exec claude -p "$prompt" \
  --add-dir "$projects" \
  --permission-mode acceptEdits \
  --allowedTools "Bash Read Write Edit Glob Grep ToolSearch ArtifactData ${CONTEXT_INBOX_TOOLS:-}"
