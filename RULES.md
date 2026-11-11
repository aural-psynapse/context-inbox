# Proposal rules

These apply to every project. The project's own `RULES.md` adds routing, people and tone, and wins where the two differ.

## Hard rules

- Propose only. Destinations are written in step 1 of the daily run, never while proposing.
- Every item cites at least one message: author, date, link, and a verbatim quote of at most 2 sentences.
- A fact without a citation does not exist. Deal sizes, dates, names and statuses come from a cited message or stay out.
- A message feeds only the destinations its channel lists in `feeds`.
- Unsure whether a message matters to a destination it feeds: write the item with `"unsure": true` and one plain `question` for the reviewer. Every such message gets an item.
- Channels marked `private` are one-to-one chats that also hold personal talk. Take only messages that matter to the destinations the channel feeds. Skip everything else entirely: no quote, no paraphrase, no hint it exists. When a message mixes both, quote only the work sentence. When unsure, leave it out.
- Check the destination first. An existing record gets an update item that names it in `existing`. A fact already recorded gets no item.
- One item per destination record. Several messages about the same record merge into one item with several citations.
- History runs propose the current state. A record that changed several times is proposed at its latest state, citing the latest messages.

## Writing

- Plain words, short sentences, active voice, in the language the project's `RULES.md` names (English when it names none). Commas and full stops in place of dashes.
- `body` is the exact text that gets written. At most 80 words, except verbatim file content. Write it as the team would, first person or neutral.

## Item shape

```json
{
  "id": "<destination id>--<record id, file slug, or first cited message ts without the dot>",
  "dest": "<destination id from config>",
  "target": "<destination type from config>",
  "action": "<verb the destination guide defines, such as create_issue or add_note>",
  "where": "Plain words: which project, record or file",
  "existing": { "id": "...", "url": "..." },
  "title": "Short title of the record or change",
  "body": "Exact text to write",
  "fields": { "paths": ["every file the commit will touch"], "stage": "...", "assignee": "...", "due": "YYYY-MM-DD" },
  "citations": [
    { "date": "YYYY-MM-DD HH:MM", "author": "Name", "channel": "<channel id>", "ts": "<message ts>", "quote": "verbatim", "link": "https://..." }
  ],
  "unsure": false,
  "question": "",
  "run": "YYYY-MM-DD",
  "order": 0
}
```

- `id` stays the same when the same record comes up again, so a re-read updates the item instead of adding a second one. Once an item has a decision or `pushed`, it never changes: news about that record goes into a new item, as AGENTS.md step 3 says.
- `existing` is `null` for new records. `fields` holds only what the action needs.
- `order` continues after the highest `order` already on the page.
