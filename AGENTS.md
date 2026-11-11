# context-inbox

Turns updates from chat tools into changes in work tools, written only after a person approves each one on a review page.

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
3. **Propose.** Turn the new messages into items per [`RULES.md`](RULES.md) and the project's `RULES.md`. A message may feed only the destinations its channel lists in `feeds`. Write each item to `proposals`. An item whose `id` already exists gets updated, never duplicated.
   Done when every new message is cited by an item or plainly not about a client or lead.
4. **Save cursors.** Write the updated cursors to `state/<source id>`. This comes last, so a run that fails earlier re-reads the same messages next time.
5. **Log the run.** Write `runs/<UTC start time>`: `{ date, counts: { channel_id: n }, pushed: n, proposed: n, errors: [text] }`. Write it even when a step failed, with the error text.

Nothing reaches a destination without `decision.status == "approved"`. Rejected and waiting items stay as they are.
