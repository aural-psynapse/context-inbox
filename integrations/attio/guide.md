# Attio

Write with the Attio connector, in the workspace named by the destination's `workspace`.

- The deal record holds notes, tasks and fields. Status lives in the deal stage.
- `add_note`: one short dated note per event. Summarise; never paste chat quotes.
- `create_task`: a follow-up linked to the deal, with an assignee and a due date.
- `update_deal`: change the stage or fields. Closing a task works the same way.
- The marker goes at the end of note bodies and task text. Search notes and tasks for it.
- `pushed.url` is the deal record URL.
