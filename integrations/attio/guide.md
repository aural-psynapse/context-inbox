# Attio

Write with the Attio connector, in the workspace named by the destination's `workspace`.

- The deal record holds notes, tasks and fields. Status lives in the deal stage.
- `add_note`: one short dated note per event. Summarise; never paste chat quotes.
- `create_task`: a follow-up linked to the deal, with an assignee and a due date.
- `update_deal`: change the stage or fields. Closing a task works the same way.
- The marker goes at the end of note bodies and task text. Search notes and tasks for it.
- Files in `fields.files` attach to the deal through Attio's file API, since the connector cannot upload: `python3 integrations/attio/upload.py CONFIG <destination id> deals <record id> <path>`. The destination's `secret` names the env var holding an Attio API token with the `file:read-write`, `object_configuration:read` and `record_permission:read` scopes. A note that goes with a file names it.
- `pushed.url` is the deal record URL.

## A complete record

A deal holds these fields. `fields.set` writes them with the connector's record update, by `api_slug`.

| Field | `api_slug` | Fill from |
|---|---|---|
| Deal stage | `stage` | the latest status a message gives |
| Deal owner | `owner` | the person `RULES.md` routes the deal to |
| Deal value | `value` | a quoted price, proposal total or agreed figure, in the field's currency |
| Associated company | `associated_company` | the client company |
| Associated people | `associated_people` | every client contact named in the messages |

A deal also has an open task for its next step, made with `create_task`, while the deal is not won or lost.

The workspace can add its own fields. Read them with the connector's attribute list for `deals` once per run, and fill any writable field a message gives a fact for.

Docs: https://docs.attio.com/docs/standard-objects/standard-objects-deals

Docs checked: 2026-11-16
