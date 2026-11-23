# claude.ai review store

The review page is published as a page on claude.ai, which Claude calls an artifact. claude.ai stores the items, the saved cursors and the run log for that page, and signs people in.

## Set up

1. Make the page with the project's name: `python3 ui/named.py <project folder>/config.json /tmp/review.html`. Publish that file as a claude.ai artifact with these capabilities:
   ```json
   { "user": { "scopes": ["profile"] }, "db": { "rules": [ { "path": "state", "read": "owner", "write": "owner" } ] } }
   ```
2. In `config.json`, set `"review_store": "claude-artifact"` and put the artifact's URL in `review_page`.
3. After a change to `ui/review.html` or to `name` in config, make the page again the same way and republish it to the same artifact URL.

## Read and write in a run

Use the ArtifactData tool on the artifact at `review_page`. The collections are `proposals`, `state` and `runs`, with the doc ids AGENTS.md gives.

## Who can open it

- A new artifact is visible only to its owner. People sign in with their claude.ai account.
- The owner opens the artifact, clicks "Share", and invites each approver with "Can edit" access. Claude's help pages list three access levels: "Can view", "Commenter" and "Can edit". They do not say which levels may save a decision, so pick "Can edit". A person who cannot save sees "You can view this page but not change it" on the review page.
- A person with "Can edit" can also republish the page.
- `decision.by` holds the reviewer's claude.ai user id. The page shows their name.
- The capabilities above let only the page's owner read `state`.

Sharing steps come from [Share artifacts](https://support.claude.com/en/articles/9547008-publishing-and-sharing-artifacts) and [Artifacts in Claude Code](https://code.claude.com/docs/en/artifacts). Docs checked: 2026-11-23.

## Where a run can reach it

Any Claude Code session signed in with a claude.ai account that can edit the page, a scheduled cloud run included. A session started with `claude -p` gets no ArtifactData tool.
