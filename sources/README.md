# Sources

A source is anything people write in: Slack, email, Discord, meeting notes, a support inbox. It has one or more **channels**: streams with their own cursor, such as a Slack channel, an email label or a folder.

The run needs one thing from a source: new messages per channel, in the format below, plus an updated cursor per channel. You can provide them in three ways. The run tries them in this order.

| Config on the source | Who reads |
|---|---|
| `"reader": "<path>"` | A program you wrote, path relative to the project folder. |
| nothing, and `sources/<type>.py` exists here | A built-in reader. |
| `"how": "<plain instructions>"` | The agent itself, through a connector or CLI it has. |

## Reader program

```
<reader> CONFIG SOURCE_ID CURSORS OUT_DIR
```

- `CONFIG`: path to the project's `config.json`.
- `SOURCE_ID`: the source's `id` in that config.
- `CURSORS`: a JSON file `{ "<channel id>": "<cursor>" }`. Read it at start and rewrite it at the end. A cursor is any string the reader can compare, such as a timestamp. A missing channel means read from the beginning.
- `OUT_DIR`: write one `<channel id>.jsonl` per channel, one message per line, oldest first.
- Print `<channel id>: <n> new` per channel. Exit non-zero on failure, before rewriting `CURSORS`.
- Read the token from the env var named by the source's `secret`.

A reader returns every message newer than the cursor, including replies that arrive late in old threads. The run proposes from what the reader returns and nothing else, so a skipped message stays skipped.

## Message format

```json
{
  "source": "slack-example",
  "channel_id": "C0123456789",
  "private": false,
  "feeds": ["linear-example"],
  "ts": "1762851600.000100",
  "thread_ts": null,
  "date": "2026-11-11 09:00",
  "author_id": "U0123456789",
  "author": "Display name",
  "text": "Message text",
  "files": ["file names"],
  "link": "https://link-to-this-message"
}
```

- `private` and `feeds` copy the channel's config.
- `ts` is unique within the channel and is what citations point at.
- `date` is UTC.
- `link` opens the message itself. Citations without a working link are not allowed.

## Reading through a connector

With `how` set, the agent runs no program. It reads each channel with the tools named in `how`, writes the same `.jsonl` files and cursor file, and continues as if a reader had run. Write `how` as instructions to the agent: which tool, which filter, and what the cursor is.

```json
{ "id": "mail-example", "type": "gmail", "how": "Gmail connector. One channel per label id. Cursor is the newest message date read.", "channels": [ { "id": "Label_123", "feeds": ["crm-example"] } ] }
```

A program gives the same result every run. Prefer one for sources you read every day.
