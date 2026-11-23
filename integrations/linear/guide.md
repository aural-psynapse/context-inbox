# Linear

With the MCP server, [`tools.py`](tools.py) writes `create_issue`, `comment_issue` and `update_issue` itself after approval, with a Linear API key in the env var named by `secret`. It does not set `fields.set` or attach `fields.files` yet. Everything below is for writing with the Linear connector instead.

Write with the Linear connector, in the team named by the destination's `team`.

- `create_issue` makes an issue. It starts in the team's first triage or backlog state unless `RULES.md` names one. Project, labels and assignee come from `RULES.md`.
- `update_issue` changes the issue named in `existing`. `comment_issue` adds a comment to it.
- The marker goes on the last line of the description or comment. Search issues and comments for it.
- Files in `fields.files` attach to the issue. For each file: call `prepare_attachment_upload` with the issue, file name, media type and size from `download.py`, then run `python3 integrations/linear/put.py <uploadRequest.url> <path> '<uploadRequest.headers as JSON>'` within 60 seconds, then call `create_attachment_from_upload` with the `assetUrl` and the file name as title. One file at a time. Search the issue's attachments by file name first and skip a file already there.
- `pushed.url` is the issue URL.

## A complete record

An issue holds these fields. `fields.set` writes them with `save_issue` on the issue's id.

| Field | Fill from |
|---|---|
| Status | the latest state a message gives, else the first state `RULES.md` names |
| Assignee | the person `RULES.md` routes the work to |
| Project | the project `RULES.md` names |
| Labels | the labels `RULES.md` names |
| Priority | urgency a message states |
| Due date | a deadline a message states |
| Estimate | a size a message states, when the team uses estimates |

Read the team's statuses and labels with the connector before setting them. They differ by team.

Docs: https://linear.app/docs/creating-issues

Docs checked: 2026-11-16
