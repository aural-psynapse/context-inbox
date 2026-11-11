# Destinations

A destination is anywhere an approved item gets written: a tracker, a CRM, a docs repo, a wiki. The agent writes to it with a connector or CLI it has, following a short guide.

The run finds the guide in this order:

1. `"guide": "<path>"` on the destination, relative to the project folder.
2. `destinations/<type>.md` in this repo.

No guide means the run skips that destination's items and logs an error.

## What a guide says

A guide answers four questions. Keep it under 20 lines.

1. **Tool.** Which connector or CLI writes, and which config keys pick the workspace, team or repo.
2. **Shape.** How each `action` maps to a record: which object, which fields, which state new records start in.
3. **Marker.** Where `ctx: <item id>` goes in the written record, and how to search for it. A search hit means an earlier run already wrote the item, so the agent skips the write. This is what makes a rerun safe.
4. **Link.** What URL to save as `pushed.url`.

Project-specific choices, such as which labels or which assignee, go in the project's `RULES.md`, not in the guide.

## Example

```markdown
# Notion

Write with the Notion connector, in the database named by the destination's `database`.

- `create_issue` adds a page. `update_issue` and `comment_issue` add a comment to the page named in `existing`.
- Title comes from the item's `title`, body from `body`.
- End the page body or comment with `ctx: <item id>`. Search the database for that text before writing.
- `pushed.url` is the page URL.
```

Built-in guides: [linear](linear.md), [attio](attio.md), [github](github.md).
