# Changelog

## [2.0.0](https://github.com/aural-psynapse/context-inbox/compare/v1.5.2...v2.0.0) (2026-11-25)


### ⚠ BREAKING CHANGES

* keep each project in an ignored projects/ folder instead of a separate repo

### Features

* keep each project in an ignored projects/ folder instead of a separate repo ([d741e66](https://github.com/aural-psynapse/context-inbox/commit/d741e663f17f95aaa82613d64e786962fa94a1b7))


### Bug Fixes

* lock the projects folder even before it exists ([34fcc81](https://github.com/aural-psynapse/context-inbox/commit/34fcc81abda3feaa5a977356930b2ee07cc4dcd0))

## [1.5.2](https://github.com/aural-psynapse/context-inbox/compare/v1.5.1...v1.5.2) (2026-11-23)


### Bug Fixes

* lint the MCP server's error check the way CI does ([bc2e466](https://github.com/aural-psynapse/context-inbox/commit/bc2e466233efebe6f90448961c9957b06b8480d2))

## [1.5.1](https://github.com/aural-psynapse/context-inbox/compare/v1.5.0...v1.5.1) (2026-11-23)


### Bug Fixes

* a run writes only in the project folder and temporary folders, and the server starts in Python's isolated mode ([b194c54](https://github.com/aural-psynapse/context-inbox/commit/b194c542544c73d2cd0f9c00db93b4348fc8a15c))
* the review page opens run-written links only as http or https addresses ([5244998](https://github.com/aural-psynapse/context-inbox/commit/524499813c7e2980f6850583c36d7ac4ce43aa2c))

## [1.5.0](https://github.com/aural-psynapse/context-inbox/compare/v1.4.1...v1.5.0) (2026-11-23)


### Features

* a project's name in config shows in the review page's tab and top left ([f995888](https://github.com/aural-psynapse/context-inbox/commit/f995888765493e6c34b3b9184fa538229d77bc90))

## [1.4.1](https://github.com/aural-psynapse/context-inbox/compare/v1.4.0...v1.4.1) (2026-11-23)


### Bug Fixes

* lint errors in the new tests and the Gmail sender ([79ba04d](https://github.com/aural-psynapse/context-inbox/commit/79ba04d1a08923c143bdf046f6e373f860371cf9))

## [1.4.0](https://github.com/aural-psynapse/context-inbox/compare/v1.3.0...v1.4.0) (2026-11-23)


### Features

* a company note can carry its contact ([1664e18](https://github.com/aural-psynapse/context-inbox/commit/1664e189c9f5e1e61be5ad32a9a3bce1c432a4eb))
* act on each review decision at once from the local review page ([889f04b](https://github.com/aural-psynapse/context-inbox/commit/889f04be4a2aed93c75b75f2eb58701ea9f5db61))
* Attio guide writes company notes, new deals and contacts ([5373dab](https://github.com/aural-psynapse/context-inbox/commit/5373dab90ef0d888cea0972ee2238b7eb6eb240d))
* Cal.com bookings reader ([ba5843b](https://github.com/aural-psynapse/context-inbox/commit/ba5843bcccc2ba01b397a5b0c85b27459d5bc29f))
* Gmail destination stops at a daily limit ([20548b4](https://github.com/aural-psynapse/context-inbox/commit/20548b43f2548d4fe569e914e962fd2e5f568105))
* Gmail destination that sends each approved email once from a send-as address ([b7fa506](https://github.com/aural-psynapse/context-inbox/commit/b7fa5063a4ae0a33b912b385b5180020f4b07fe2))
* Gmail reader with attachment text ([f37bb68](https://github.com/aural-psynapse/context-inbox/commit/f37bb682a7c100915665e2a6c0721121d3368fe8))
* old badge for late items and regular runs while the local review page is up ([30ded4c](https://github.com/aural-psynapse/context-inbox/commit/30ded4c752d3070cbc0a4bc79335d09b43fa1380))
* timed reminder drafts after a write, set per destination ([c58ff9e](https://github.com/aural-psynapse/context-inbox/commit/c58ff9ef8259f555e696a32ecb2d0b86921dc6a8))

## [1.3.0](https://github.com/aural-psynapse/context-inbox/compare/v1.2.2...v1.3.0) (2026-11-23)


### Features

* keep review items in a SQLite file by default, with claude.ai as a second review store ([53cb569](https://github.com/aural-psynapse/context-inbox/commit/53cb5694d0e2a6539c2425b1e32149065ff438a7))

## [1.2.2](https://github.com/aural-psynapse/context-inbox/compare/v1.2.1...v1.2.2) (2026-11-19)


### Bug Fixes

* log only failures as run errors ([#5](https://github.com/aural-psynapse/context-inbox/issues/5)) ([f252ee0](https://github.com/aural-psynapse/context-inbox/commit/f252ee016a9bbe8aa9ec4ebd811b730eaa40e43d))

## [1.2.1](https://github.com/aural-psynapse/context-inbox/compare/v1.2.0...v1.2.1) (2026-11-19)


### Bug Fixes

* apply the reviewer's answer when pushing an approved question item ([#3](https://github.com/aural-psynapse/context-inbox/issues/3)) ([8d4cbdc](https://github.com/aural-psynapse/context-inbox/commit/8d4cbdcd8d253adb56a110e094ef4ca47105a7d4))

## [1.2.0](https://github.com/aural-psynapse/context-inbox/compare/v1.1.0...v1.2.0) (2026-11-18)


### Features

* attach documents shared in Slack to Linear issues and Attio deals ([2b552c7](https://github.com/aural-psynapse/context-inbox/commit/2b552c78f848e143b5ac70c2143064be22122164))
* fill every record field, not only notes ([c196466](https://github.com/aural-psynapse/context-inbox/commit/c196466f27ceb0453132a8439b1b512bd0bf5c87))
* read the text of files shared in Slack messages ([8ab3c6d](https://github.com/aural-psynapse/context-inbox/commit/8ab3c6da6a73272a1cd8709ad2209560a27bd11e))


### Bug Fixes

* retry rate-limited Slack file downloads and name the missing scope on 403 ([5ec3ded](https://github.com/aural-psynapse/context-inbox/commit/5ec3ded924740247c0c7d8a1401bda57c74ab27d))

## [1.1.0](https://github.com/aural-psynapse/context-inbox/compare/v1.0.0...v1.1.0) (2026-11-13)


### Features

* accept a single project folder in check.py, run.sh and fire.sh ([01e3a27](https://github.com/aural-psynapse/context-inbox/commit/01e3a27d3106fd4d7739ff43875b7b06ae06144f))


### Bug Fixes

* name the project when check.py gets a relative folder ([ee86a41](https://github.com/aural-psynapse/context-inbox/commit/ee86a41268e672b17e4e72566156e3eb3c26f2a4))

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
