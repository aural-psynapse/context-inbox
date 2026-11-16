# Linear

Write with the Linear connector, in the team named by the destination's `team`.

- `create_issue` makes an issue. It starts in the team's first triage or backlog state unless `RULES.md` names one. Project, labels and assignee come from `RULES.md`.
- `update_issue` changes the issue named in `existing`. `comment_issue` adds a comment to it.
- The marker goes on the last line of the description or comment. Search issues and comments for it.
- Files in `fields.files` attach to the issue. For each file: call `prepare_attachment_upload` with the issue, file name, media type and size from `download.py`, then run `python3 integrations/linear/put.py <uploadRequest.url> <path> '<uploadRequest.headers as JSON>'` within 60 seconds, then call `create_attachment_from_upload` with the `assetUrl` and the file name as title. One file at a time. Search the issue's attachments by file name first and skip a file already there.
- `pushed.url` is the issue URL.
