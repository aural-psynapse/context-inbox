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
cd "$here"
# Shell access covers only the checker, the readers and the git steps a guide uses.
# Anything else asks first, since the session reads messages written by outside people.
# shellcheck disable=SC2086
exec claude "$prompt" \
  --add-dir "$projects" \
  --allowedTools \
  "Bash(python3 $here/connector/check.py:*)" \
  "Bash(python3 $here/integrations/:*)" \
  "Bash(python3 $projects/:*)" \
  "Bash($projects/:*)" \
  "Bash(git log:*)" "Bash(git add:*)" "Bash(git commit:*)" "Bash(git pull:*)" "Bash(git push:*)" "Bash(git status:*)" \
  Read Write Edit Glob Grep ToolSearch ArtifactData ${CONTEXT_INBOX_TOOLS:-}
