# Changelog

## [1.0.0](https://github.com/aural-psynapse/context-inbox/compare/v0.5.0...v1.0.0) (2026-11-11)

First public release. The config format, the item shape and the reader and guide formats are now stable. A change that breaks them will raise the first number.

### Bug Fixes

* `runner/fire.sh` exits with an error when the run fails to start.

### Documentation

* README with banner, screenshots of the review page, quickstart and integrations.
* CONTRIBUTING.md and SECURITY.md.

### Miscellaneous

* Tests for the connector and the write check, run by CI on every push with ruff and shellcheck.
* release-please runs on GitHub Actions.

## [0.5.0](https://github.com/aural-psynapse/context-inbox/compare/v0.4.0...v0.5.0) (2026-11-11)

### Features

* `runner/fire.sh` starts a project's scheduled cloud run from any agent or script, with no person and no API key. It reads the task id from `routine` in `config.json`.
* `fire.sh` can also call a scheduled task's API trigger directly, for callers with no Claude Code.

## [0.4.0](https://github.com/aural-psynapse/context-inbox/compare/v0.3.0...v0.4.0) (2026-11-11)

### Features

* Connector: `connector/check.py` finds a projects repo, checks every config, and prints each reader command and guide path. A config error stops the run before it reads a message.
* Integrations folder with the Slack reader, Linear, Attio and GitHub guides, and recipes for Slack to Linear, Slack to Attio and Slack to GitHub.
* Run log on the review page: the "Synced" box opens a list of runs with counts and errors.
* Runner: the scheduled-run prompt and `run.sh` for a run on your own machine.
* Claude Code skills for setup and run-now, and a hook that refuses destination writes without a `ctx:` marker.
* Example projects repo with one project.
* Review page shows written items with their link and locks them, and adds a "Written" filter.

### Bug Fixes

* Slack reader no longer skips a message posted while a run is reading, keeps reading other channels when one fails, times out stalled requests, and keeps attachment and forwarded text.
* Review page saves edited text and comments only onto the item on screen, and shows an error when a save fails.
* Review page keeps the sidebar on mid-size screens and keeps focus while you type a comment.
* Connector rejects names in place of channel IDs, misspelt keys, placeholder links, and paths outside the project folder.
* Write check covers commits made with `git -C` or `git -c`, `gh` writes and chat posts, and blocks the write when the check itself fails.
* A run applies reviewer answers on "Needs your answer" items.

## [0.3.0](https://github.com/aural-psynapse/context-inbox/compare/v0.2.0...v0.3.0) (2026-11-11)

### Features

* Any source or destination: a project names a reader per source and a guide per destination, kept in its own folder.
* One example project folder replaces the built-in readers and guides.

## [0.2.0](https://github.com/aural-psynapse/context-inbox/compare/v0.1.0...v0.2.0) (2026-11-11)

### Features

* Review page shows the last run in the sidebar: when it ran, how many items it wrote, and how many it proposed.
* README, llms.txt and AGENTS.md written for outside users. MIT license.

## [0.1.0](https://github.com/aural-psynapse/context-inbox/releases/tag/v0.1.0) (2026-11-11)

### Features

* Daily run that reads new Slack messages, proposes cited changes on a review page, and writes only the ones a person approved to Linear, Attio or GitHub.

### Bug Fixes

* Slack reader formats its start time so Slack returns messages.
* Slack reader picks up replies in threads of any age.
