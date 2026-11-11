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

The agent looks up channel IDs, writes any reader or guide that is missing, publishes the review page and runs once. [AGENTS.md](AGENTS.md) has its steps.

## Plug in anything

| | Built in | Add your own |
|---|---|---|
| **Sources** | Slack | A reader program, or plain instructions for reading through a connector. See [sources/README.md](sources/README.md). |
| **Destinations** | Linear, Attio, GitHub | A guide of under 20 lines. See [destinations/README.md](destinations/README.md). |

Your own readers and guides live in your project folder, so this repo stays untouched. Routing lives in config: each channel lists the destinations it `feeds`.

## Set it up by hand

You need [Claude Code](https://docs.claude.com/en/docs/claude-code) with a connector or CLI for each destination, a claude.ai account for the review page, and Python 3.9+ for the built-in reader.

1. **Make a project folder** in a private repo of its own: `config.json` shaped like [`config.example.json`](config.example.json), and a `RULES.md` with who is who and what goes where.
2. **Publish [`review.html`](review.html)** as a claude.ai artifact with capabilities `{ "user": {}, "db": { "rules": [ { "path": "state", "read": "owner", "write": "owner" } ] } }`. Put its URL in `review_page` and share it as Editor with your approvers.
3. **Set each source token** in the env var named by its `secret`. The Slack reader needs a user token with `channels:history`, `groups:history`, `im:history`, `mpim:history` and `users:read`.
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
| `sources[].type` | Picks the built-in reader `sources/<type>.py` when one exists. |
| `sources[].reader` | Path to your own reader, relative to the project folder. |
| `sources[].how` | Instructions for the agent to read through a connector instead. |
| `sources[].secret` | Env var that holds the token. |
| `sources[].channels[].id` | Exact channel ID, case-sensitive. Names like `#general` are not accepted. |
| `sources[].channels[].feeds` | Destination ids this channel may write to. |
| `sources[].channels[].private` | `true` for chats that mix work and personal talk. |
| `destinations[].type` | Picks the built-in guide `destinations/<type>.md` when one exists. |
| `destinations[].guide` | Path to your own guide, relative to the project folder. |

Other keys on a destination, such as `team` or `repo`, are read by its guide.

## Repo layout

```
AGENTS.md              setup and the daily run, step by step
RULES.md               what a proposal is and its JSON shape
config.example.json    config shape
sources/               how to add a source, and built-in readers
destinations/          how to add a destination, and built-in guides
review.html            the review page
```

## License

[MIT](LICENSE)
