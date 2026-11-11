# Linear

Write through the Linear connector, in the team named by the destination's `team`.

- `create_issue` makes an issue. New issues start in the team's first triage or backlog state unless the project's `RULES.md` names one. Project, labels and assignee come from `RULES.md`.
- `update_issue` changes the issue named in `existing`. `comment_issue` adds a comment to it.
- End every description or comment you write with a last line `ctx: <item id>`. A field change with no text, such as a new state, goes with a comment that carries the marker.
- Before writing, search issues and comments for `ctx: <item id>`. A hit means it is already written.
- `pushed.url` is the issue URL.
