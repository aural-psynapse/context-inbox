# context-inbox

A framework for turning messages from any source into cited changes in any destination. A person approves each change on a review page before any run writes it.

This repo holds:

| Part | Where |
|---|---|
| Instructions for you | this file, [`RULES.md`](RULES.md) |
| Connector: finds a projects repo and checks each config | [`connector/check.py`](connector/check.py) |
| Integrations: readers, guides, and recipes that pair them | [`integrations/`](integrations/) |
| Review page with run log | [`ui/review.html`](ui/review.html) |
| Runner: prompt and local run script | [`runner/`](runner/) |
| Skills and a hook for Claude Code | [`.claude/`](.claude/) |

Each project keeps its own folder in a separate private repo: `config.json` and `RULES.md`, plus any reader or guide it wrote itself. [`projects-example/`](projects-example/) is a projects repo to copy.

You have two jobs here. **Set up a project** once, then do the **daily run** on a schedule.

## Set up a project

Ask the person only what you cannot look up. Done when the first run's items show on the review page and the person has seen them.

1. **Ask what to connect.** Which sources and which channels in them, and which destinations. Look up exact channel IDs, team keys and repo names yourself. Config takes exact, case-sensitive IDs only, never display names.
2. **Make the project folder** in the person's private projects repo, copying [`projects-example/acme/`](projects-example/acme/) and the closest recipe in [`integrations/recipes/`](integrations/recipes/). In `RULES.md`, list people by their source user ID, say what counts, and say what goes to which destination.
3. **Wire each source** with a reader (see Sources below). Use one from `integrations/` by name when it fits. Test it on one channel with an empty cursor file. Check that every line has every field of the message format.
4. **Wire each destination** with a guide (see Destinations below). Use one from `integrations/` by name when it fits. Confirm you can read the destination with your tools.
5. **Store tokens outside git.** Put each source token in the env var named by `secret`. In a cloud environment, store it as a network secret for the API's host and leave the env var unset.
6. **Check the config.** Run `python3 connector/check.py <projects repo> <project>` until it exits 0.
7. **Publish the review page.** Publish [`ui/review.html`](ui/review.html) as a claude.ai artifact with capabilities `{ "user": {}, "db": { "rules": [ { "path": "state", "read": "owner", "write": "owner" } ] } }`. Put its URL in `review_page`. Ask the person to share it as Editor with everyone who approves.
8. **Run once.** Do the daily run below. The first run reads the whole history.
9. **Schedule it.** Offer a daily scheduled run with the prompt in [`runner/prompt.txt`](runner/prompt.txt). It needs this repo, the projects repo, every repo a guide writes to, and every connector a guide names.

## Sources

A source has channels: streams with their own cursor, such as a Slack channel or an email label. Each source in config sets one of:

- `reader`: an integration name such as `slack` (runs `integrations/slack/reader.py`), or a path to a program in the project folder. It runs as `<reader> CONFIG SOURCE_ID CURSORS OUT_DIR`.
- `how`: plain instructions for you to read through a connector, producing the same files a reader would.

A reader reads `CURSORS` (`{ "<channel id>": "<cursor>" }`, missing means from the start), writes `OUT_DIR/<channel id>.jsonl` oldest first, prints `<channel id>: <n> new`, and rewrites `CURSORS` only on success. It returns every message newer than the cursor, late thread replies included. Each line:

```json
{ "source": "", "channel_id": "", "private": false, "feeds": [], "ts": "", "thread_ts": null, "date": "YYYY-MM-DD HH:MM", "author_id": "", "author": "", "text": "", "files": [], "link": "" }
```

`private` and `feeds` copy the channel's config. `ts` is unique within the channel. `date` is UTC. `link` opens the message itself.

## Destinations

Each destination in config sets `guide`: an integration name such as `attio` (reads `integrations/attio/guide.md`), or a path to a Markdown file in the project folder. A guide says:

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

Run the steps in order. Each ends on its done line.

0. **Check.** Run `python3 connector/check.py <projects repo> <project>`. Exit 1: write a `runs` doc with its errors and stop. Otherwise keep its output: it gives each reader command and each guide path. Then read the project's `RULES.md`.

1. **Push approved items.** Read `proposals`. For each item with `decision.status == "approved"` and no `pushed`, one at a time:
   1. Read the destination's guide at its `guide_path`.
   2. Search the destination for `ctx: <item id>` as the guide says. A hit means an earlier run already wrote it: skip the write.
   3. Otherwise write it, using `decision.body` when present, else `body`, with the marker where the guide puts it. Read `decision.comment` first: it may change what to write.
   4. Save `pushed: { at, url }` on that item right away, in its own write, before touching the next item.
   Done when every approved item carries `pushed`.
2. **Read new messages.** For each source, load its cursors from `state/<source id>` into a local file, then run its `read.run` command with `CONFIG SOURCE_ID CURSORS OUT_DIR`, or follow its `read.how`. Keep the updated cursor file; do not save it yet.
   Done when every channel has a count.
3. **Propose.** Turn the new messages into items per [`RULES.md`](RULES.md) and the project's `RULES.md`. A message may feed only the destinations its channel lists in `feeds`. Write each item to `proposals`. An item whose `id` already exists gets updated, never duplicated, but only while it has no decision. An item that is approved, rejected or pushed is frozen: never change it. New facts for that record become a new item with id `<old id>--<first new message ts without the dot>`, so a reviewer sees and approves them.
   Done when every new message is cited by an item or plainly off topic for every destination it feeds.
4. **Save cursors.** Replace `state/<source id>` with a `set` whose data is exactly `{ "cursors": { "<channel id>": "<cursor>" } }`, nothing wrapped around it. This comes last, so a run that fails earlier re-reads the same messages next time.
5. **Log the run.** Write `runs/<UTC start time>`: `{ date, counts: { channel_id: n }, pushed: n, proposed: n, errors: [text] }`. Write it even when a step failed, with the error text.

Nothing reaches a destination without `decision.status == "approved"`. Rejected and waiting items stay as they are.

## Changing this repo

This repo stays generic. It holds no real project's names, IDs, people or links.

- `projects-example/` passes `connector/check.py`. Readers are Python 3.9+, standard library only.
- An integration is a folder in `integrations/` holding `reader.py`, `guide.md`, or both. A recipe shows one source and one destination wired together.
- `.claude/hooks/require-ctx-marker.py` refuses destination writes without `ctx: <item id>`. Add new write tools to its list.
- `ui/review.html` is one file with no build step and shows any destination type. After a change, take a screenshot in a browser and republish it to the same artifact URL.
- Commits: one line, `type: what changed`. No trailers.
