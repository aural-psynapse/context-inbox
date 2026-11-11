# context-inbox

Turns chat messages into cited changes for work tools. A person approves each change on a review page before any run writes it. Setup for people is in [README.md](README.md).

A run serves one project. Its folder (in a separate private repo) holds `config.json` and `RULES.md`. Read both first. `config.json` follows [`config.example.json`](config.example.json). `review_page` in it is the page every step below reads and writes, through the ArtifactData tool.

## Review page collections

| Collection | Holds | Who reads |
|---|---|---|
| `proposals` | items waiting for, or past, review | every reviewer |
| `state` | one doc per source id: `{ cursors: { channel_id: ts } }` | page owner only |
| `runs` | one doc per run, id = UTC start time | every reviewer |

## Daily run

Run the steps in order. Each ends on its done line.

1. **Push approved items.** Read `proposals`. For each item with `decision.status == "approved"` and no `pushed`, one at a time:
   1. Follow the guide for the destination's type in `destinations/<type>.md`.
   2. Search the destination for the item's `id` first. Found means an earlier run already wrote it: skip the write.
   3. Otherwise write it, using `decision.body` when present, else `body`, and carry the item's `id` in the written record as the guide says. Read `decision.comment` first: it may change what to write.
   4. Save `pushed: { at, url }` on that item right away, in its own write, before touching the next item.
   Done when every approved item carries `pushed`.
2. **Read new messages.** For each source, load its cursors from `state/<source id>` into a local file, then run the reader for its type in `scripts/sources/<type>.py` (usage at the top of each script). Keep the updated cursor file; do not save it yet.
   Done when the reader printed a count for every channel.
3. **Propose.** Turn the new messages into items per [`RULES.md`](RULES.md) and the project's `RULES.md`. A message may feed only the destinations its channel lists in `feeds`. Write each item to `proposals`. An item whose `id` already exists gets updated, never duplicated, but only while it has no decision. An item that is approved, rejected or pushed is frozen: never change it. New facts for that record become a new item with id `<old id>--<first new message ts without the dot>`, so a reviewer sees and approves them.
   Done when every new message is cited by an item or plainly not about a client or lead.
4. **Save cursors.** Replace `state/<source id>` with a `set` whose data is exactly `{ "cursors": { "<channel id>": "<ts>" } }`, nothing wrapped around it. This comes last, so a run that fails earlier re-reads the same messages next time.
5. **Log the run.** Write `runs/<UTC start time>`: `{ date, counts: { channel_id: n }, pushed: n, proposed: n, errors: [text] }`. Write it even when a step failed, with the error text.

Nothing reaches a destination without `decision.status == "approved"`. Rejected and waiting items stay as they are.

## Changing this repo

This repo stays generic. It holds no project's names, channel IDs, people or links. Those go in the project's own folder.

- **Reader scripts:** Python 3.9+, standard library only. Check one with `python3 scripts/sources/<type>.py` and no arguments; it prints its usage.
- **New source:** copy the arguments and the output fields of `scripts/sources/slack.py`, so steps 2 and 3 work unchanged.
- **New destination:** add `destinations/<type>.md` covering how to write, where `ctx: <item id>` goes, how to search for it, and what `pushed.url` holds. Add the type to `TYPE_COLOR` in `review.html` and to `target` in `RULES.md`.
- **Review page:** `review.html` is one file with no build step. After a change, take a screenshot in a browser and republish it to the same artifact URL.
- **Commits:** one line, `type: what changed`. No trailers.
