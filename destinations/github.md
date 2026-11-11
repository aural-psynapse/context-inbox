# GitHub

Commit to the destination's `repo` on its `branch`, one commit per item.

- Follow that repo's own README and AGENTS.md for where files go.
- Commit message: one line, `docs: <item title> (ctx: <item id>)`. No trailers: no Co-Authored-By, no session links.
- Before writing, run `git log --grep "ctx: <item id>"`. A hit means it is already written.
- `pushed.url` is the commit URL.
