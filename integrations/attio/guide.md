# Attio

Write through the Attio connector, in the workspace named by the destination's `workspace`.

- The deal record holds notes, tasks and fields. Status lives in the deal stage.
- `add_note`: one short dated note per event, in the language `RULES.md` names. Summarise; never paste chat quotes.
- `create_task`: a follow-up linked to the deal, with an assignee and a due date.
- `update_deal`: change the stage or fields, and add a note saying what changed. Closing a task works the same way: close it, then add the note.
- End every note body and task text with `ctx: <item id>`. Field changes carry no text, so the note beside them carries the marker.
- Before writing, search notes and tasks for `ctx: <item id>`. A hit means it is already written.
- `pushed.url` is the deal record URL.
