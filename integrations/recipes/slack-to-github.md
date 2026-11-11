# Slack to GitHub

Client decisions in Slack become files in a docs repo, one commit per approved item.

`config.json`:

```json
"sources": [ { "id": "slack-acme", "type": "slack", "reader": "slack", "secret": "SLACK_TOKEN_ACME",
  "channels": [ { "id": "C0345678901", "feeds": ["docs-acme"] } ] } ],
"destinations": [ { "id": "docs-acme", "type": "github", "guide": "github", "repo": "acme/docs", "branch": "main" } ]
```

`RULES.md`:

```markdown
- Client decisions go to docs-acme as a new file in decisions/, named by date and topic.
```

Needs: a Slack user token, push access to the repo, and the repo cloned in the run.
