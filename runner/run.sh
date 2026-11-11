#!/bin/sh
# Run one project's daily run now, on this machine.
# Usage: runner/run.sh PROJECTS_DIR PROJECT
set -eu
[ $# -eq 2 ] || { sed -n 2,3p "$0"; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
python3 "$here/connector/check.py" "$1" "$2" > /dev/null
prompt=$(sed "s#<projects repo>/<project>#$1/$2#" "$here/runner/prompt.txt")
cd "$here" && exec claude -p "$prompt"
