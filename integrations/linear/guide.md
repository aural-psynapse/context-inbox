# Linear

Write with the Linear connector, in the team named by the destination's `team`.

- `create_issue` makes an issue. It starts in the team's first triage or backlog state unless `RULES.md` names one. Project, labels and assignee come from `RULES.md`.
- `update_issue` changes the issue named in `existing`. `comment_issue` adds a comment to it.
- The marker goes on the last line of the description or comment. Search issues and comments for it.
- `pushed.url` is the issue URL.
