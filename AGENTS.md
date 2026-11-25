# context-inbox

A framework for turning messages from any source into cited changes in any destination. A person approves each change on a review page before any run writes it.

This repo holds:

| Part | Where |
|---|---|
| Instructions for you | this file, [`RULES.md`](RULES.md) |
| Connector: finds each project folder and checks its config | [`connector/check.py`](connector/check.py) |
| Integrations: readers, guides, review stores, and recipes that pair them | [`integrations/`](integrations/) |
| MCP server: the agent's only door to the items and the destinations | [`server/mcp.py`](server/mcp.py) |
| Review page with run log | [`ui/review.html`](ui/review.html) |
| Runner: prompt and local run script | [`runner/`](runner/) |
| Skills and a hook for Claude Code | [`.claude/`](.claude/) |

Each project keeps its own folder in `projects/` at the top of this repo, such as `projects/acme/`: `config.json` and `RULES.md`, plus any reader or guide it wrote itself. Git ignores `projects/`, so a project's settings never get pushed to this public repo. [`projects-example/`](projects-example/) shows the layout to copy.

You have two jobs here. **Set up a project** once, then do **a run** each time one starts. A run pushes approved items, reads new messages and proposes new items.

## Set up a project

Ask the person only what you cannot look up. Done when the first run's items show on the review page and the person has seen them.

1. **Ask what to connect.** Which sources and which channels in them, and which destinations. Look up exact channel IDs, team keys and repo names yourself. Config takes exact, case-sensitive IDs only, never display names.
2. **Make the project folder** `projects/<project>/`, copying [`projects-example/acme/`](projects-example/acme/) and the closest recipe in [`integrations/recipes.md`](integrations/recipes.md). In `RULES.md`, list people by their source user ID, say what counts, and say what goes to which destination.
3. **Wire each source** with a reader (see Sources below). Use one from `integrations/` by name when it fits. Test it on one channel with `--only <channel id>` and a cursor file holding `{}`. Check that every line has every field of the message format.
4. **Wire each destination** with a guide (see Destinations below). Use one from `integrations/` by name when it fits. Confirm you can read the destination with your tools. With the MCP server, also write its tools file (see MCP server below).
5. **Store tokens outside git.** Put each source token in the env var named by `secret`. In a cloud environment, store it as a network secret for the API's host and leave the env var unset.
6. **Check the config.** Run `python3 connector/check.py <project>` until it exits 0. Here and in the runner scripts, `<project>` is the folder name in `projects/`, such as `acme`. A value with `/` is a folder path instead.
7. **Set up the review store.** Pick one (see Review store below), set `review_store`, and follow its guide's "Set up". `sqlite` needs nothing but this repo. Put the link people open in `review_page`, and tell the person who can open it.
8. **Run once.** Do a run as "A run" below says. The first run reads the whole history.
9. **Keep it running.** With the `sqlite` store, start the page with both options below and give the person the command. Each approval gets written the moment the person clicks, and new messages become items every 5 minutes while the page is up:
   ```sh
   python3 integrations/sqlite/serve.py projects/<project>/review.db \
     --on-decide "runner/act.sh <project>" \
     --every 5 --run "runner/read-now.sh <project>"
   ```
   With the `claude-artifact` store and a Slack source, set up [`integrations/slack/worker.md`](integrations/slack/worker.md): each Slack message and each approval starts a cloud run within a minute, with no computer switched on. Otherwise a run needs a Claude Code session signed in to claude.ai, started with `runner/run.sh <project>`.

## Sources

A source has channels: streams with their own cursor, such as a Slack channel or an email label. Each source in config sets one of:

- `reader`: an integration name such as `slack` (runs `integrations/slack/reader.py`), or a path to a program in the project folder. It runs as `<reader> CONFIG SOURCE_ID CURSORS OUT_DIR [--only CHANNEL_ID]`.
- `how`: plain instructions for you to read through a connector, producing the same files a reader would.

A reader:

- reads `CURSORS`, a JSON object `{ "<channel id>": "<cursor>" }`. A missing channel, or a file holding `{}`, means read from the start.
- returns every message newer than the cursor, late thread replies included, into `OUT_DIR/<channel id>.jsonl`, oldest first.
- moves each cursor to the newest message read, but never past the moment the run started, so a message posted during the run comes back next time.
- prints `<channel id>: <n> new` per channel. A channel that fails keeps its old cursor and gets no file. The reader finishes the other channels, rewrites `CURSORS`, and exits 1.

A message edited after it was read is not read again. Each line:

```json
{ "source": "", "channel_id": "", "private": false, "feeds": [], "ts": "", "thread_ts": null, "date": "YYYY-MM-DD HH:MM", "author_id": "", "author": "", "text": "", "files": [], "link": "" }
```

`private` and `feeds` copy the channel's config. `ts` is unique within the channel. `date` is UTC. `link` opens the message itself, inside its thread for a reply.

`files` holds one object per file shared in the message:

```json
{ "id": "", "name": "", "type": "", "link": "", "text": "", "note": "" }
```

`text` is the file's text, cut to a length the reader picks. A reader that cannot read a file leaves `text` empty and says why in `note`, such as an image or a link to a document in another tool. `note` is left out when there is nothing to say. `id` is the file's id in the source. A source whose files can be attached to a destination record has a `download.py` next to its reader: `download.py CONFIG SOURCE_ID FILE_ID OUT_DIR` saves the file and prints its path, media type and size.

## Destinations

Each destination in config sets `guide`: an integration name such as `attio` (reads `integrations/attio/guide.md`), or a path to a Markdown file in the project folder.

Every destination follows the same three rules, so a guide does not repeat them:

- **Marker.** Each written record carries `ctx: <item id>`. A change with no text of its own, such as a new state or stage, goes with a note or comment that carries it.
- **Search first.** Before writing, search the destination for the marker. A hit means an earlier run wrote it: skip the write.
- **Link.** Save the record's URL as `pushed.url`.

A guide adds only what is specific to the tool:

1. Which connector or CLI writes, and which config keys pick the workspace, team or repo.
2. How each `action` maps to a record.
3. Where the marker goes, and where to search for it.
4. Which URL counts as the record's URL.
5. **A complete record**: the fields a record should hold, how to read the live field list, the public doc pages that list fields, and a `Docs checked: YYYY-MM-DD` line.

## Review store

The review store holds the three collections below and serves [`ui/review.html`](ui/review.html). Config sets `review_store`: an integration name such as `sqlite` (reads `integrations/sqlite/guide.md`), or a path to a Markdown file in the project folder. Left out, it is `claude-artifact` when `review_page` is a claude.ai link and `sqlite` otherwise.

| Store | The items live in | Who can open the page | A run reaches it from |
|---|---|---|---|
| `sqlite` | one file in the project folder | everyone who can reach the address | the machine that holds the file |
| `claude-artifact` | storage claude.ai gives the page | claude.ai accounts the page is shared with | any signed-in Claude Code session, cloud runs included |

Login is a choice the store's guide makes. A store with no login lets everyone who can open the page decide, which fits a page that already sits behind a login.

A guide says:

1. **Set up**: what to make or publish, and which link goes in `review_page`.
2. **Read and write in a run**: how you list, read, set, update and delete a doc in each collection.
3. **Who can open it**: how people sign in, or that there is no login, and what `decision.by` holds.
4. **Where a run can reach it.**

To keep the items in a database a site already has, write a guide in the project folder. Add one table to that database, with a collection name, a doc id and the doc as JSON per row. Have the site serve `ui/review.html` unchanged, with these addresses beside it:

| Address | Answers |
|---|---|
| `GET api/proposals` | a JSON array of every item, each with its `id` |
| `GET api/runs` | the 30 newest run docs, newest first, each with its `id` |
| `PATCH api/proposals/<id>` with `{ "decision": {} }` | replaces `decision` on that item. Refuses an item that carries `pushed`. |
| `GET api/me` | `{ "id": "", "name": "", "can_write": true }` for the signed-in person. Answer `{}` when there is no login. |

[`integrations/sqlite/serve.py`](integrations/sqlite/serve.py) is a working copy of those addresses.

## MCP server

[`server/mcp.py`](server/mcp.py) is the agent's one door to the items and the destinations. It works with the `sqlite` review store.

- **Reads** go straight through: `inbox_list`, `inbox_get`, and each destination's read tools, named `<destination id>__<tool>`.
- **Changes** wait for a person: `propose` saves an item, `withdraw` deletes an undecided one. No tool approves or rejects.
- **Writes** happen only in `push_approved`. The server writes each approved, unwritten item itself and saves `pushed`. It skips an item whose text changed after the approval.
- **Keys** live in the server's environment. The agent session holds no destination key and no write connector for that destination.

### Register the server

The person keeps one registration file per project, outside the project folder and this repo, such as `~/.config/context-inbox/<project>.json`. Only the server process gets its `env`:

```json
{ "mcpServers": { "context-inbox": {
  "command": "python3",
  "args": ["-I", "<this repo>/server/mcp.py", "<project folder>"],
  "env": { "CRM_KEY": "<the destination's key>", "CONTEXT_INBOX_PINS": "<output of --print-pins>" }
} } }
```

Put one `env` entry per destination `secret`. Set `CONTEXT_INBOX_MCP_CONFIG` to the file's path before `runner/run.sh`. The run gets the server's tools as `mcp__context-inbox__<tool>`.

`runner/run.sh` takes the run's permissions from [`runner/permissions.py`](runner/permissions.py) and loads only this repo's Claude Code settings, so the person's own allow rules cannot widen them. The run may start only the programs the config check names. It may write only in the project folder and the temporary folders, and not in those programs, the tools files or the review store's file. `-I` in the registration keeps Python from loading files from the person's own Python folders into the server. It may neither read nor edit the registration file or Claude Code's own settings. The run can still read any file the person can. Nothing it reads leaves this machine through a destination on the server, except inside an item a person approves; a destination without a tools file, written by the agent itself, has no such guard. A run started another way needs the same settings: `claude --settings "$(python3 runner/permissions.py <project folder>)" --setting-sources project --mcp-config <registration file>`.

### Wire a destination to the server

1. Write a tools file for the destination in the project folder, such as `tools/crm.py`, and set `"tools": "tools/crm.py"` on the destination in config. `connector/check.py` checks that the file exists.
2. Ask the person to read the file, then run `python3 server/mcp.py <project folder> --print-pins` and register the server with that output. The server runs a destination only while its tools file and its settings in `config.json` match the pin, so a run that edits either one switches that destination off.
3. Test it through the server: call each read tool, then propose one test item on a test record the person names. The person approves it, you call `push_approved`, and both of you check the record.

The file defines, with the Python standard library only:

| Name | What it does |
|---|---|
| `READ_TOOLS` | a list of `{ name, description, inputSchema }`, one per read the agent needs to draft good items, such as a search or a get by id. Reads only: no tool here may create, change or delete anything. |
| `read(tool, args, destination)` | runs one read tool and returns JSON-ready data. It raises on any failure; the server returns the error to the agent. |
| `write(item, destination)` | writes one approved item. It handles each `action` the destination's guide defines and raises on any other. It uses `decision.body` when present, else `body`, and puts `ctx: <item id>` where the guide puts the marker: for a change with no text of its own, such as a new stage, it adds a note or comment that carries the marker. It searches for the marker first, so a write never happens twice. It returns the record's URL, or the record's id when the tool has no URL. It raises on any failure. |

`destination` is the destination's object from config. Read its key with `os.environ[destination["secret"]]`.

A destination without `tools` keeps the old way: the agent writes approved items by the guide, and `push_approved` lists them as waiting.

With the server, a run calls `push_approved` for step 1, `propose` and `withdraw` for step 3, `save_cursors` for step 4 and `log_run` for step 5. `runner/run.sh` allows the server's tools.

## Review page collections

You read and write the collections the way the review store's guide says.

| Collection | Holds | Who reads |
|---|---|---|
| `proposals` | items waiting for, or past, review | every reviewer |
| `state` | one doc per source id: `{ cursors: { channel_id: cursor } }` | the run, and no reviewer |
| `runs` | one doc per run, id = UTC start time | every reviewer |

An item may carry `look`: an address the review page shows in a frame, so the reviewer sees the change instead of reading it. Use a path on the review page's own site, or an `https://` address.

An approved item may carry `publishing: { version, since }` while its destination puts the change live and `pushed` is not there yet. The destination's own code sets it in its own store; the `sqlite` store and the MCP server never set it. The review page shows a loader on that item, keeps it in view and blocks its buttons until `pushed` arrives.

An item is **decided** when `decision.status` is `approved` or `rejected`, or when it carries `pushed`. A reviewer can also save a comment without deciding: `decision.status` stays `pending` and `decision.comment` holds the text. On an item marked `unsure`, that comment is the reviewer's answer. The review page shows pushed items as written, with their link, and locks them.

## A run

Run the steps in order. Each ends on its done line.

0. **Check.** Run `python3 connector/check.py <project folder>`. Exit 1: write a `runs` doc with its errors, write nothing else, and stop. Otherwise keep its output: it gives each reader command, each guide path and the review store's guide at `review_store.guide_path`. Then read that guide and the project's `RULES.md`.
   For each guide whose `Docs checked` date is more than 7 days old, read the doc pages it links. When a page lists a field the guide's "A complete record" list lacks, add `Guide out of date: <guide>, <field>, <page>` to the run's `errors`, so a person updates the guide and its date.

1. **Push approved items.** Read `proposals`. For each item with `decision.status == "approved"` and no `pushed`, one at a time:
   1. Read the destination's guide at its `guide_path`.
   2. Search the destination for `ctx: <item id>` as the guide says. A hit means an earlier run already wrote it: skip the write.
   3. Otherwise write it, using `decision.body` when present, else `body`, with the marker where the guide puts it. Read `decision.comment` first: it may change what to write.
   When the item carries `unsure: true` and a `decision.comment`, the comment answers its `question`. Apply the answer first: when the question proposed field values and the answer accepts them, write those values as `fields.set`.
   When the item lists `fields.set`, write each field on the record the way the guide says, in the same push.
   When the item lists `fields.files`, download each one with its source's `download.py` into a temporary folder and attach it to the record the way the guide says. Delete the downloads after the item is saved.
   4. Save `pushed: { at, url }` on that item right away, in its own write, before touching the next item.
   Done when every approved item carries `pushed`.
2. **Read new messages.** For each source, read `state/<source id>` and write only its `cursors` object to a local file (`{}` when the doc is missing), then run its `read.run` command with `CONFIG SOURCE_ID CURSORS OUT_DIR`, or follow its `read.how`. Keep the updated cursor file; do not save it yet.
   A reader that exits 1 still gives counts for the channels that worked. Log the failed channels as errors.
   Done when every channel has a count or an error.
3. **Propose.** Turn the new messages into items per [`RULES.md`](RULES.md) and the project's `RULES.md`. A message may feed only the destinations its channel lists in `feeds`. Write each item to `proposals`. An item whose `id` already exists gets updated, never duplicated, but only while it is undecided. A decided item is frozen: never change it. New facts for that record become a new item with id `<old id>--<first new message ts without the dot>`, so a reviewer sees and approves them. Set `old` on each item whose newest cited message is older than `old_after_hours` from the check output, as [`RULES.md`](RULES.md) says.
   Then read the reviewer's answers: for each undecided item with `unsure: true` and a `decision.comment`, apply the answer. Rewrite the item to match, or delete it when the answer says it is off topic. Set `unsure: false` and keep the comment.
   Skip a message that an existing item already cites, by channel and `ts`. A reader can return a message twice when it was posted during the previous run.
   Done when every new message is cited by an item or plainly off topic for every destination it feeds, and every answer is applied.
3b. **Draft reminders.** For each destination in config with `reminder_days`, read every item written to it, meaning it carries `pushed`, that is not itself a reminder. For each day N in `reminder_days` with `pushed.at` plus N days in the past, propose a reminder item unless one exists with id `<item id>--r<N>`, or the project's `RULES.md` says reminders for that record stop, for example after a reply in the same thread. A reminder item has id `<item id>--r<N>`, `reminder_of: "<item id>"`, the same `dest` and `target`, `existing` set to the written record from `pushed`, and its text written per the project's `RULES.md`. It waits for approval like any other item. A computer that was off on the day makes the reminder on its first run after.
   Done when every reminder due today exists or is stopped.
4. **Save cursors.** Replace `state/<source id>` with a `set` whose data is exactly `{ "cursors": { "<channel id>": "<cursor>" } }`, nothing wrapped around it. This comes last, so a run that fails earlier re-reads the same messages next time.
5. **Log the run.** Write `runs/<UTC start time>`: `{ date, counts: { channel_id: n }, pushed: n, proposed: n, errors: [text] }`. `date` is the run's start as an ISO 8601 UTC timestamp, such as `2026-01-31T06:00:00Z`. Write it even when a step failed, with the error text. `errors` holds only failures: a step, reader, write or check that did not work. A step with nothing to do, such as a destination with no approved items, is not an error.

Nothing reaches a destination without `decision.status == "approved"`. Rejected and waiting items stay as they are.

## Changing this repo

This repo stays generic. It holds no real project's names, IDs, people or links.

- `projects-example/acme/` passes `connector/check.py`. Nothing under `projects/` is ever committed. Readers and review stores are Python 3.10+, standard library only.
- An integration is a folder in `integrations/` holding `reader.py`, `guide.md`, or both, plus any small script its guide or reader calls, such as `download.py`, `upload.py` or `store.py`. A recipe shows one source and one destination wired together.
- `.claude/hooks/require-ctx-marker.py` refuses destination writes that lack a `ctx: ` marker, and any chat post. It checks that a marker is present, not that the item was approved. Add new write tools to its list. It loads only in sessions started inside this repo, such as `runner/run.sh`. A scheduled cloud run starts one folder above, so it does not load there.
- `ui/review.html` is one file with no build step and shows any destination type. It names no review store except in `claudeStore` and `httpStore`. After a change, open it through `integrations/sqlite/serve.py`, take a screenshot, and republish it to each claude.ai artifact that serves it, made with `ui/named.py` so it keeps that project's name. The page says "Context Inbox" twice, in `<title>` and in the `brand` line; `ui/named.py` replaces exactly those two.
- Docs follow the code in the same commit. A change to what a person can do, or how they start it, updates `README.md`, `AGENTS.md`, `llms.txt` and the touched guide or `runner/README.md` before it is pushed. `tests/test_docs.py` fails when a runner script, an integration or a review page option goes unnamed in them.
- Commits: one line, `type: what changed`, no trailers. The type sets the next version: `fix:` raises the last number, `feat:` the middle one, and `feat!:` or a `BREAKING CHANGE:` line the first one. `docs:`, `chore:`, `ci:` and `refactor:` raise nothing. `scripts/release.sh` opens a pull request with the new version and changelog. After it merges, `scripts/release.sh publish` makes the release.
