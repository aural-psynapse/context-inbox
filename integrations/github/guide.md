# GitHub

Commit to the destination's `repo` on its `branch`, one commit per item, then push.

- Follow that repo's own README and AGENTS.md for where files go.
- A commit touches only the paths in the item's `fields.paths`. When the repo's rules require more files, the proposal lists them in `fields.paths` so the reviewer sees them before approving. A path missing from the list is not written.
- Commit message: one line, `docs: <item title> (ctx: <item id>)`. No trailers and no message body.
- Before writing, run `git log --grep "ctx: <item id>"`. A hit means it is already written.
- `pushed.url` is the commit URL.
