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

The agent looks up channel IDs, writes a reader for each source and a guide for each destination, publishes the review page and runs once. [AGENTS.md](AGENTS.md) has its steps.

## Plug in anything

A source needs a reader: a small program, or plain instructions for the agent to read through a connector. A destination needs a guide: a few lines on how to write to it. Both live in your project folder, and the agent writes them during setup. Routing lives in config: each channel lists the destinations it `feeds`.

[`example/`](example/) is a full project folder: Slack in, Linear out.

## Set it up by hand

You need [Claude Code](https://docs.claude.com/en/docs/claude-code) with a connector or CLI for each destination, a claude.ai account for the review page, and Python 3.9+ for the example reader.

1. **Make a project folder** in a private repo of its own: copy of [`example/`](example/). Edit `config.json`, `RULES.md`, the reader and the guide.
2. **Publish [`review.html`](review.html)** as a claude.ai artifact with capabilities `{ "user": {}, "db": { "rules": [ { "path": "state", "read": "owner", "write": "owner" } ] } }`. Put its URL in `review_page` and share it as Editor with your approvers.
3. **Set each source token** in the env var named by its `secret`. The example Slack reader needs a user token with `channels:history`, `groups:history`, `im:history`, `mpim:history` and `users:read`.
4. **Run it** from a session with both repos checked out:
   ```
   Run the daily run in context-inbox/AGENTS.md for project folder <projects repo>/<project>.
   ```
   Save that prompt as a Claude Code routine with a cron schedule to run it every day.

## Config

| Key | Meaning |
|---|---|
| `review_page` | URL of the published review page. |
| `sources[].id` | Name for the source. Cursors are stored under it. |
| `sources[].type` | Name of the tool, such as `slack`. |
| `sources[].reader` | Path to the reader, relative to the project folder. |
| `sources[].how` | Instructions for the agent to read through a connector instead. |
| `sources[].secret` | Env var that holds the token. |
| `sources[].channels[].id` | Exact channel ID, case-sensitive. Names like `#general` are not accepted. |
| `sources[].channels[].feeds` | Destination ids this channel may write to. |
| `sources[].channels[].private` | `true` for chats that mix work and personal talk. |
| `destinations[].type` | Name of the tool. The review page colours items by it. |
| `destinations[].guide` | Path to the guide, relative to the project folder. |

Other keys on a destination, such as `team` or `repo`, are read by its guide.

## Repo layout

```
AGENTS.md              setup and the daily run, step by step
RULES.md               what a proposal is and its JSON shape
example/               a project folder to copy: config, rules, reader, guide
review.html            the review page
```

## License

[MIT](LICENSE)
