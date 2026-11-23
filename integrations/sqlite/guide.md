# SQLite review store

One file holds the items, the saved cursors and the run log. [`store.py`](store.py) reads and writes it for a run. [`serve.py`](serve.py) shows the review page from it. Both use the Python standard library only.

## Set up

1. The file is `review.db` in the project folder. `store.py` makes it on first use.
2. Add `review.db*` to the `.gitignore` of the projects repo. The file holds quotes from messages.
3. In `config.json`, set `"review_store": "sqlite"` and `"review_page": "http://127.0.0.1:47821"`.
4. Start the page and give the person the link and this command. The page shows the `name` from the `config.json` beside the file, or `--config` names another:
   ```sh
   python3 integrations/sqlite/serve.py <project folder>/review.db
   ```

## Read and write in a run

With the MCP server ([`server/mcp.py`](../../server/mcp.py)), use its tools instead of the commands below. The commands never approve or reject, and refuse to change a decided item, except to save `pushed` on an approved one.

Every command starts with `python3 integrations/sqlite/store.py <project folder>/review.db`.

| To | Command | Input |
|---|---|---|
| read every doc in a collection | `list <collection>` | |
| read one doc | `get <collection> <id>` | |
| write a new item, or rewrite an undecided one | `set proposals <item id>` | the item as JSON on stdin |
| save `pushed` on an item | `update proposals <item id>` | `{ "pushed": { "at": "", "url": "" } }` on stdin |
| save cursors | `set state <source id>` | `{ "cursors": { "<channel id>": "<cursor>" } }` on stdin |
| log the run | `set runs <UTC start time>` | the run doc on stdin |
| delete an item | `delete proposals <item id>` | |

`set` replaces the whole doc. `update` replaces only the top-level keys it is given and exits 1 when the doc does not exist.

## Act the moment a person decides

Start the page with `--on-decide` and each decision takes effect at once, with no wait for the daily run:

```sh
python3 integrations/sqlite/serve.py <project folder>/review.db --on-decide "runner/act.sh <projects repo> <project>"
```

- Approve: `runner/act.sh` writes that item to its destination now and saves `pushed`.
- A comment typed on an undecided item: it rewrites the draft to follow the comment. The page shows the new text within 5 seconds.
- Reject: nothing to do.

Each action is logged in `act.log` in the project folder. The daily run still pushes anything approved while the page was down.

## New messages without waiting for the daily run

Start the page with `--every` and `--run`, and a run reads new messages every few minutes while the page is up:

```sh
python3 integrations/sqlite/serve.py <project folder>/review.db --every 5 --run "runner/read-now.sh <projects repo> <project>"
```

While the computer is off, messages wait. The first run after it comes back marks items whose messages waited longer than `old_after_hours` with "Old, waited ..." in place of the date.

## The page

- The page is up only while `serve.py` runs. A run does not need it: it uses `store.py` on the file.
- Stopping `serve.py` loses nothing. The items stay in the file.
- The page re-reads the items every 5 seconds.
- The page can change one thing: `decision` on an item with no `pushed`. It never receives the `state` collection.

## Who can open it

- There is no login. Everyone who can reach the address can approve.
- The default address answers on this machine only.
- To let other people in, serve it behind a login the team already has, with `--host` and `--port` set to what that login forwards to.
- `decision.by` stays empty, so the page shows "Approved" with no name.

## Where a run can reach it

A run must happen on the machine that holds the file, such as `runner/run.sh`. A scheduled cloud run cannot reach a file on a laptop: use a store the cloud run can reach, such as [`claude-artifact`](../claude-artifact/guide.md).
