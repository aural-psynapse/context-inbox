#!/bin/sh
# Start the scheduled cloud run now, with no person in the loop.
# Usage: runner/fire.sh
# Needs CONTEXT_INBOX_FIRE_URL and CONTEXT_INBOX_FIRE_TOKEN: the Fire URL and
# token of the scheduled task's API trigger. Prints the run's session URL.
set -eu
: "${CONTEXT_INBOX_FIRE_URL:?set CONTEXT_INBOX_FIRE_URL to the Fire URL of the scheduled task}"
: "${CONTEXT_INBOX_FIRE_TOKEN:?set CONTEXT_INBOX_FIRE_TOKEN to the API token of the scheduled task}"
out=$(curl -sS --fail-with-body -X POST "$CONTEXT_INBOX_FIRE_URL" \
  -H "Authorization: Bearer $CONTEXT_INBOX_FIRE_TOKEN" \
  -H "anthropic-beta: experimental-cc-routine-2026-04-01" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{}') || { echo "$out" >&2; exit 1; }
printf '%s\n' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["claude_code_session_url"])'
