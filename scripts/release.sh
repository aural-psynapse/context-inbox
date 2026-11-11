#!/bin/sh
# Make a release from this machine with release-please, no GitHub Actions needed.
# Usage:
#   scripts/release.sh            open or update the release pull request
#   scripts/release.sh publish    after merging that pull request: tag it and make the GitHub release
# Needs node and a signed-in gh.
set -eu
cd "$(dirname "$0")/.."
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
token=$(gh auth token)
case "${1:-pr}" in
  pr) cmd=release-pr ;;
  publish) cmd=github-release ;;
  dry) cmd="release-pr --dry-run" ;;
  *) sed -n 2,6p "$0"; exit 2 ;;
esac
# shellcheck disable=SC2086
npx --yes release-please@17.11.2 $cmd \
  --token="$token" --repo-url="$repo" \
  --config-file=release-please-config.json --manifest-file=.release-please-manifest.json
