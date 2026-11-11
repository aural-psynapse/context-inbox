# context-inbox

A framework for turning messages from any source into cited changes in any destination. A person approves each change on a review page before any run writes it.

This repo holds the run, the rules and the review page. Each project keeps its own folder in a separate private repo: `config.json`, `RULES.md`, and the readers and guides it needs. [`example/`](example/) is a complete project folder to copy.

You have two jobs here. **Set up a project** once, then do the **daily run** on a schedule.

## Set up a project

Ask the person only what you cannot look up. Done when the first run's items show on the review page and the person has seen them.

1. **Ask what to connect.** Which sources and which channels in them, and which destinations. Look up exact channel IDs, team keys and repo names yourself. Config takes exact, case-sensitive IDs only, never display names.
2. **Make the project folder** in the person's private projects repo, copying [`example/`](example/). In `RULES.md`, list people by their source user ID, say what counts, and say what goes to which destination.
3. **Wire each source** with a reader (see Sources below). Test it on one channel with an empty cursor file. Check that every line has every field of the message format.
4. **Wire each destination** with a guide (see Destinations below). Confirm you can read the destination with your tools.
5. **Store tokens outside git.** Put each source token in the env var named by `secret`. In a cloud environment, store it as a network secret for the API's host and leave the env var unset.
6. **Publish the review page.** Publish [`review.html`](review.html) as a claude.ai artifact with capabilities `{ "user": {}, "db": { "rules": [ { "path": "state", "read": "owner", "write": "owner" } ] } }`. Put its URL in `review_page`. Ask the person to share it as Editor with everyone who approves.
7. **Run once.** Do the daily run below. The first run reads the whole history.
8. **Schedule it.** Offer a daily scheduled run with the prompt `Run the daily run in context-inbox/AGENTS.md for project folder <projects repo>/<project>.` It needs this repo, the projects repo, every repo a guide writes to, and every connector a guide names.

## Sources

A source has channels: streams with their own cursor, such as a Slack channel or an email label. Each source in config sets one of:

- `reader`: a program in the project folder, run as `<reader> CONFIG SOURCE_ID CURSORS OUT_DIR`. [`example/readers/slack.py`](example/readers/slack.py) is one.
- `how`: plain instructions for you to read through a connector, producing the same files a reader would.

A reader reads `CURSORS` (`{ "<channel id>": "<cursor>" }`, missing means from the start), writes `OUT_DIR/<channel id>.jsonl` oldest first, prints `<channel id>: <n> new`, and rewrites `CURSORS` only on success. It returns every message newer than the cursor, late thread replies included. Each line:

```json
{ "source": "", "channel_id": "", "private": false, "feeds": [], "ts": "", "thread_ts": null, "date": "YYYY-MM-DD HH:MM", "author_id": "", "author": "", "text": "", "files": [], "link": "" }
```

`private` and `feeds` copy the channel's config. `ts` is unique within the channel. `date` is UTC. `link` opens the message itself.

## Destinations

Each destination in config sets `guide`: a short Markdown file in the project folder. [`example/guides/linear.md`](example/guides/linear.md) is one. A guide says:

1. Which connector or CLI writes, and which config keys pick the workspace, team or repo.
2. How each `action` maps to a record.
3. Where `ctx: <item id>` goes in the written record, and how to search for it.
4. What URL to save as `pushed.url`.

## Review page collections

You read and write the review page through the ArtifactData tool.

| Collection | Holds | Who reads |
|---|---|---|
| `proposals` | items waiting for, or past, review | every reviewer |
| `state` | one doc per source id: `{ cursors: { channel_id: cursor } }` | page owner only |
| `runs` | one doc per run, id = UTC start time | every reviewer |

## Daily run

Read the project's `config.json` and `RULES.md` first. Run the steps in order. Each ends on its done line.

1. **Push approved items.** Read `proposals`. For each item with `decision.status == "approved"` and no `pushed`, one at a time:
   1. Read the destination's `guide`. Missing: log an error for the item and move on.
   2. Search the destination for `ctx: <item id>` as the guide says. A hit means an earlier run already wrote it: skip the write.
   3. Otherwise write it, using `decision.body` when present, else `body`, with the marker where the guide puts it. Read `decision.comment` first: it may change what to write.
   4. Save `pushed: { at, url }` on that item right away, in its own write, before touching the next item.
   Done when every approved item with a guide carries `pushed`.
2. **Read new messages.** For each source, load its cursors from `state/<source id>` into a local file, then run its `reader` or follow its `how`. Keep the updated cursor file; do not save it yet.
   Done when every channel has a count.
3. **Propose.** Turn the new messages into items per [`RULES.md`](RULES.md) and the project's `RULES.md`. A message may feed only the destinations its channel lists in `feeds`. Write each item to `proposals`. An item whose `id` already exists gets updated, never duplicated, but only while it has no decision. An item that is approved, rejected or pushed is frozen: never change it. New facts for that record become a new item with id `<old id>--<first new message ts without the dot>`, so a reviewer sees and approves them.
   Done when every new message is cited by an item or plainly off topic for every destination it feeds.
4. **Save cursors.** Replace `state/<source id>` with a `set` whose data is exactly `{ "cursors": { "<channel id>": "<cursor>" } }`, nothing wrapped around it. This comes last, so a run that fails earlier re-reads the same messages next time.
5. **Log the run.** Write `runs/<UTC start time>`: `{ date, counts: { channel_id: n }, pushed: n, proposed: n, errors: [text] }`. Write it even when a step failed, with the error text.

Nothing reaches a destination without `decision.status == "approved"`. Rejected and waiting items stay as they are.

## Changing this repo

This repo stays generic. It holds no real project's names, IDs, people or links.

- `example/` stays a working project folder. Its reader is Python 3.9+, standard library only.
- `review.html` is one file with no build step and shows any destination type. After a change, take a screenshot in a browser and republish it to the same artifact URL.
- Commits: one line, `type: what changed`. No trailers.
