# context-inbox

Turn team chat into updates for your tracker, CRM and docs, with a person approving every change first.

An agent reads new chat messages once a day and drafts the changes they imply: a new Linear issue, an Attio note, a line in a docs repo. Each draft lands on a review page with the exact text it will write and the messages it came from. You approve, reject or edit it there. The next run writes only what you approved.

## How it works

```
Slack ──► reader script ──► agent drafts items ──► review page ──► you approve
                                                                      │
             Linear / Attio / GitHub ◄── next run writes approved ◄───┘
```

- **Cited.** Each item quotes the messages behind it, with author, date and link. A fact with no quote stays out.
- **Approved first.** The agent writes to a destination only for items marked approved on the review page.
- **Written once.** Each written record carries `ctx: <item id>`. The agent searches for that marker before writing, so a rerun never writes twice.
- **Incremental.** The reader keeps one cursor per channel and returns only messages newer than it, including late replies in old threads.
- **Private chats stay private.** For channels flagged `private`, the agent takes only work messages. It skips personal talk without quoting or mentioning it.

## Supported

| Sources | Destinations |
|---|---|
| Slack | Linear, Attio, GitHub |

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code), with the Linear and Attio connectors for those destinations and `git` for GitHub.
- A claude.ai account to host the review page as an artifact with a database.
- A Slack user token with `channels:history`, `groups:history`, `im:history`, `mpim:history` and `users:read`.
- Python 3.9 or newer. The reader uses the standard library only.

## Setup

1. **Make a project folder.** Keep it in a private repo of its own, one folder per project. Put two files in it:
   - `config.json`, shaped like [`config.example.json`](config.example.json).
   - `RULES.md`, with who is who and which updates go where. The agent reads it next to the shared [`RULES.md`](RULES.md). The project file wins on conflict.
2. **Publish the review page.** Ask Claude Code to publish [`review.html`](review.html) as an artifact with these capabilities, then put its URL in `review_page`:
   ```json
   { "user": {}, "db": { "rules": [ { "path": "state", "read": "owner", "write": "owner" } ] } }
   ```
   Share it as Editor with everyone who approves.
3. **Give the reader a token.** Set the env var named by the source's `secret`. In a cloud environment you can leave it unset and let the network proxy add the token for `slack.com`.
4. **Run it.** From a session that has both repos checked out, send:
   ```
   Run the daily run in context-inbox/AGENTS.md for project folder <projects repo>/<project>.
   ```
   To run it every day, save that prompt as a Claude Code routine with a cron schedule.

The first run reads the whole channel history and proposes the current state of each lead or task.

## Config

| Key | Meaning |
|---|---|
| `review_page` | URL of the published review page. |
| `sources[].id` | Name for the source. Cursors are stored under it. |
| `sources[].type` | Reader to use: `scripts/sources/<type>.py`. |
| `sources[].secret` | Env var that holds the token. |
| `sources[].channels[].id` | Exact channel ID, case-sensitive. Names like `#general` are not accepted. |
| `sources[].channels[].feeds` | Destination ids this channel may write to. |
| `sources[].channels[].private` | `true` for one-to-one chats that mix work and personal talk. |
| `destinations[].type` | `linear`, `attio` or `github`. Guide: `destinations/<type>.md`. |

## Adding a source or destination

- **Source:** add `scripts/sources/<type>.py`. It takes the same four arguments as [`slack.py`](scripts/sources/slack.py) and writes one JSON line per message with the same fields.
- **Destination:** add `destinations/<type>.md`. It says how to write, where the `ctx:` marker goes, how to search for it, and what `pushed.url` points to. Add the type's colour to `TYPE_COLOR` in `review.html`.

## Repo layout

```
AGENTS.md              the daily run, step by step
RULES.md               what a proposal is and its JSON shape
config.example.json    config shape
destinations/          one guide per destination type
scripts/sources/       one reader per source type
review.html            the review page
```

## License

[MIT](LICENSE)
