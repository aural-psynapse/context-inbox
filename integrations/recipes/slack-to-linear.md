# Slack to Linear

Bug reports and requests in a Slack channel become Linear issues.

`config.json`:

```json
"sources": [ { "id": "slack-acme", "type": "slack", "reader": "slack", "secret": "SLACK_TOKEN_ACME",
  "channels": [ { "id": "C0123456789", "feeds": ["linear-acme"] } ] } ],
"destinations": [ { "id": "linear-acme", "type": "linear", "guide": "linear", "team": "ACM" } ]
```

`RULES.md`:

```markdown
- Bug reports and feature requests from customers go to linear-acme.
- One issue per bug or request, in project "Customer requests", assignee U0987654321.
```

Needs: a Slack user token, the Linear connector.
