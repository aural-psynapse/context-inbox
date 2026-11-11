# Slack to Attio

Lead and deal talk in Slack, including a private DM, becomes Attio deal notes and follow-up tasks.

`config.json`:

```json
"sources": [ { "id": "slack-acme", "type": "slack", "reader": "slack", "secret": "SLACK_TOKEN_ACME",
  "channels": [
    { "id": "C0234567890", "feeds": ["attio-acme"] },
    { "id": "D0123456789", "feeds": ["attio-acme"], "private": true } ] } ],
"destinations": [ { "id": "attio-acme", "type": "attio", "guide": "attio", "workspace": "acme" } ]
```

`RULES.md`:

```markdown
- Leads, deals and customer follow-ups go to attio-acme. One deal per company.
- In D0123456789, take only messages about customers and deals. Skip the rest entirely.
```

Needs: a Slack user token with `im:history`, the Attio connector.
