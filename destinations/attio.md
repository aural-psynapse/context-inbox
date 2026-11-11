# Attio

Write through the Attio connector, in the workspace named by the destination's `workspace`.

- The deal record holds notes, tasks and fields. Status lives in the deal stage.
- One short dated note per event. Summarise in short English lines; never paste chat quotes.
- Follow-ups are tasks linked to the deal, with an assignee and a due date. Close a task its replacement makes obsolete.
- End every note body and task text with `ctx: <item id>`. Search notes and tasks for it before writing; a hit means it is already written.
- `pushed.url` is the record URL.
