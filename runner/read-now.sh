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
# shellcheck disable=SC2086
claude -p "$prompt" \
  --add-dir "$projects" \
  --allowedTools \
  "Bash(python3 $here/connector/check.py:*)" \
  "Bash(python3 $here/integrations/:*)" \
  "Bash(python3 $projects/:*)" \
  "Bash($projects/:*)" \
  "Bash(git log:*)" "Bash(git add:*)" "Bash(git commit:*)" "Bash(git pull:*)" "Bash(git push:*)" "Bash(git status:*)" \
  Read Write Edit Glob Grep ToolSearch ArtifactData ${CONTEXT_INBOX_TOOLS:-} \
  >> "$projects/read.log" 2>&1
