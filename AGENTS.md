# context-inbox

A framework for turning messages from any source into cited changes in any destination. A person approves each change on a review page before any run writes it.

The repo gives you the run, the rules, the review page and two plug-in points: [sources](sources/README.md) and [destinations](destinations/README.md). Each project brings its own folder, in a separate private repo, with `config.json` and `RULES.md`. The config says which channels feed which destinations. `RULES.md` says who is who and what goes where.

You have two jobs here. **Set up a project** once, then do the **daily run** on a schedule.

## Set up a project

Ask the person only what you cannot look up. Done when the first run's items show on the review page and the person has seen them.

1. **Ask what to connect.** Which sources and which channels in them, and which destinations. Look up exact channel IDs, team keys and repo names yourself with the tools you have. Config takes exact, case-sensitive IDs only, never display names.
2. **Make the project folder** in the person's private projects repo: `<project>/config.json` shaped like [`config.example.json`](config.example.json), and `<project>/RULES.md`. In `RULES.md`, list people by their source user ID with name and role, and say which updates go to which destination and how they should look.
3. **Wire each source.** Use the built-in reader when `sources/<type>.py` exists. Otherwise write a reader into the project folder and set `reader`, or set `how` to read through a connector. Follow [sources/README.md](sources/README.md). Test it on one channel with an empty cursor file and check that every line has every field of the message format.
4. **Wire each destination.** Use the built-in guide when `destinations/<type>.md` exists. Otherwise write a guide into the project folder and set `guide`. Follow [destinations/README.md](destinations/README.md). Confirm you can read the destination with your tools before trusting you can write it.
5. **Store tokens outside git.** Put each source token in the env var named by `secret`. In a cloud environment, store it as a network secret for the API's host and leave the env var unset.
6. **Publish the review page.** Publish [`review.html`](review.html) as a claude.ai artifact with capabilities `{ "user": {}, "db": { "rules": [ { "path": "state", "read": "owner", "write": "owner" } ] } }`. Put its URL in `review_page`. Ask the person to share it as Editor with everyone who approves.
7. **Run once.** Do the daily run below. The first run reads the whole history.
8. **Schedule it.** Offer a daily scheduled run with the prompt: `Run the daily run in context-inbox/AGENTS.md for project folder <projects repo>/<project>.` It needs this repo, the projects repo, every destination repo, and every connector the guides name.

## Review page collections

The run reads and writes the review page through the ArtifactData tool.

| Collection | Holds | Who reads |
|---|---|---|
| `proposals` | items waiting for, or past, review | every reviewer |
| `state` | one doc per source id: `{ cursors: { channel_id: cursor } }` | page owner only |
| `runs` | one doc per run, id = UTC start time | every reviewer |

## Daily run

Read the project's `config.json` and `RULES.md` first. Run the steps in order. Each ends on its done line.

1. **Push approved items.** Read `proposals`. For each item with `decision.status == "approved"` and no `pushed`, one at a time:
   1. Find the destination's guide: its `guide` path, else `destinations/<type>.md`. No guide: log an error for the item and move on.
   2. Search the destination for `ctx: <item id>` as the guide says. A hit means an earlier run already wrote it: skip the write.
   3. Otherwise write it, using `decision.body` when present, else `body`, with the marker where the guide puts it. Read `decision.comment` first: it may change what to write.
   4. Save `pushed: { at, url }` on that item right away, in its own write, before touching the next item.
   Done when every approved item with a guide carries `pushed`.
2. **Read new messages.** For each source, load its cursors from `state/<source id>` into a local file. Then read: its `reader` path, else `sources/<type>.py`, else its `how` instructions. Keep the updated cursor file; do not save it yet.
   Done when every channel has a count.
3. **Propose.** Turn the new messages into items per [`RULES.md`](RULES.md) and the project's `RULES.md`. A message may feed only the destinations its channel lists in `feeds`. Write each item to `proposals`. An item whose `id` already exists gets updated, never duplicated, but only while it has no decision. An item that is approved, rejected or pushed is frozen: never change it. New facts for that record become a new item with id `<old id>--<first new message ts without the dot>`, so a reviewer sees and approves them.
   Done when every new message is cited by an item or plainly off topic for every destination it feeds.
4. **Save cursors.** Replace `state/<source id>` with a `set` whose data is exactly `{ "cursors": { "<channel id>": "<cursor>" } }`, nothing wrapped around it. This comes last, so a run that fails earlier re-reads the same messages next time.
5. **Log the run.** Write `runs/<UTC start time>`: `{ date, counts: { channel_id: n }, pushed: n, proposed: n, errors: [text] }`. Write it even when a step failed, with the error text.

Nothing reaches a destination without `decision.status == "approved"`. Rejected and waiting items stay as they are.

## Changing this repo

This repo stays generic. It holds no project's names, channel IDs, people or links. Those go in the project's own folder.

- **Built-in readers:** Python 3.9+, standard library only, in `sources/`. Run one with no arguments to print its usage.
- **Built-in guides:** one Markdown file per type in `destinations/`, under 20 lines.
- **Review page:** `review.html` is one file with no build step. It shows any destination type. After a change, take a screenshot in a browser and republish it to the same artifact URL.
- **Commits:** one line, `type: what changed`. No trailers.
