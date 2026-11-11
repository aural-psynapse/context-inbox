# context-inbox

A framework for turning team messages into updates in your tools, with a person approving every change first.

An agent reads new messages from your sources, drafts the changes they imply for your destinations, and puts each draft on a review page with the exact text and the messages it came from. You approve, reject or edit it there. The next run writes only what you approved.

You bring the sources, the destinations and the rules for what goes where. The framework brings the run, the review page, and the guarantees below.

## How it works

```
sources ──► readers ──► agent drafts items ──► review page ──► you approve
                                                                  │
          destinations ◄── next run writes approved items ◄───────┘
```

- **Cited.** Each item quotes the messages behind it, with author, date and link. A fact with no quote stays out.
- **Approved first.** The agent writes to a destination only for items marked approved on the review page.
- **Written once.** Each written record carries `ctx: <item id>`. The agent searches for that marker before writing, so a rerun never writes twice.
- **Incremental.** Readers keep one cursor per channel and return only newer messages, including late replies in old threads.
- **Private chats stay private.** For channels flagged `private`, the agent takes only messages that matter to the destinations. It skips the rest without quoting or mentioning it.

## Set it up with an agent

Point a coding agent with tool access at this repo and tell it what to connect:

```
Set up context-inbox for project "acme" following AGENTS.md.
Read #sales and #support in our Slack. Write deals to HubSpot and bugs to Linear.
```

The agent looks up channel IDs, picks or writes a reader for each source and a guide for each destination, publishes the review page and runs once. [AGENTS.md](AGENTS.md) has its steps.

## What is in the box

| Part | What it does |
|---|---|
| [Connector](connector/check.py) | Finds your projects repo, checks every config, and tells the run which reader and guide to use. A config error stops the run before it reads any message. The run logs the errors and writes nothing else. |
| [Integrations](integrations/) | Slack reader. Linear, Attio and GitHub guides. Recipes such as [Slack to Attio](integrations/recipes/slack-to-attio.md). |
| [Review page](ui/review.html) | Items to approve, reject or edit, filtered by status and destination. Last sync, and a run log with counts and errors per run. Keys: J, K, A, R, E, U. |
| [Runner](runner/) | The scheduled-run prompt. `fire.sh` starts the cloud run from any agent or script. `run.sh` runs once on your machine, with you watching. |
| [Agent instructions](AGENTS.md) | Setup and the daily run, step by step, plus the [proposal rules](RULES.md). |
| [Skills and hook](.claude/) | `context-inbox-setup` and `context-inbox-run` skills. A hook that refuses the connector writes it lists, commits and GitHub writes when they lack a `ctx:` marker, and any chat post. It checks the marker is there; the run checks approval. |
| [Example projects repo](projects-example/) | One project, Acme: Slack to Linear and Slack to Attio. |

A source needs a reader and a destination needs a guide. Use one from `integrations/` by name, or let the agent write one into your project folder. Routing lives in config: each channel lists the destinations it `feeds`.

## Set it up by hand

You need [Claude Code](https://docs.claude.com/en/docs/claude-code) with a connector or CLI for each destination, a claude.ai account for the review page, and Python 3.9+ for the connector and Slack reader.

1. **Make a project folder** in a private repo of its own: copy of [`projects-example/`](projects-example/). Edit `config.json` and `RULES.md`, then run `python3 connector/check.py <projects repo> <project>`.
2. **Publish [`ui/review.html`](ui/review.html)** as a claude.ai artifact with capabilities `{ "user": { "scopes": ["profile"] }, "db": { "rules": [ { "path": "state", "read": "owner", "write": "owner" } ] } }`. Put its URL in `review_page`. Share it with your approvers as Contributor when the Share menu offers it, else as Editor. An Editor can also republish the page and read the saved cursors.
3. **Set each source token** in the env var named by its `secret`. The Slack reader needs a user token with `channels:history`, `groups:history`, `im:history`, `mpim:history` and `users:read`.
4. **Run it** every day: save [`runner/prompt.txt`](runner/prompt.txt) as a Claude Code scheduled task with a cron schedule. Start it at any other time with `runner/fire.sh <projects repo> <project>`, or with `runner/run.sh <projects repo> <project>` to watch it run. [`runner/README.md`](runner/README.md) has the details.

## Config

| Key | Meaning |
|---|---|
| `review_page` | URL of the published review page. |
| `routine` | Optional. Id of the scheduled task, such as `trig_01ABC`, so `runner/fire.sh` can start it. |
| `sources[].id` | Name for the source. Cursors are stored under it. |
| `sources[].type` | Name of the tool, such as `slack`. |
| `sources[].reader` | Integration name, such as `slack`, or a path inside the project folder. |
| `sources[].how` | Instructions for the agent to read through a connector instead. |
| `sources[].secret` | Env var that holds the token. |
| `sources[].channels[].id` | Exact channel ID, case-sensitive. Names like `#general` are not accepted. |
| `sources[].channels[].feeds` | Destination ids this channel may write to. |
| `sources[].channels[].private` | `true` for chats that mix work and personal talk. |
| `destinations[].type` | Name of the tool. The review page colours items by it. |
| `destinations[].guide` | Integration name, such as `attio`, or a path inside the project folder. |

Other keys on a destination, such as `team` or `repo`, are read by its guide. Other keys on a source or a channel, such as a forum address, are read by its reader. Keys are case-sensitive.

## Repo layout

```
AGENTS.md                instructions for the agent: setup and daily run
RULES.md                 what a proposal is and its JSON shape
connector/check.py       finds and checks project configs
integrations/            readers, guides, recipes
ui/review.html           review page and run log
runner/                  scheduled-run prompt and local run script
.claude/                 skills and the write-blocking hook
projects-example/        a projects repo to copy
```

## Versioning

The repo follows [semantic versioning](https://semver.org). Commit messages start with a type, as [Conventional Commits](https://www.conventionalcommits.org) describes: `fix:` for a bug fix, `feat:` for a new feature, `feat!:` for a change that breaks existing setups. [release-please](https://github.com/googleapis/release-please) reads them and opens a pull request with the next version and the [changelog](CHANGELOG.md). Run `scripts/release.sh` to open or update that pull request. After you merge it, run `scripts/release.sh publish` to tag the version and make the GitHub release.

## License

[MIT](LICENSE)
