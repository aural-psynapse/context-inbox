# Recipes

Each recipe pairs the Slack reader with one destination. Merge the parts you need into your project's `config.json` and `RULES.md`. [`projects-example/acme/`](../projects-example/acme/) shows a full project.

Every recipe uses this source. List each channel with the destinations it `feeds`:

```json
"sources": [ { "id": "slack-acme", "type": "slack", "reader": "slack", "secret": "SLACK_TOKEN_ACME",
  "channels": [ { "id": "C0123456789", "feeds": ["linear-acme"] } ] } ]
```

| Recipe | Destination in `config.json` | Line in `RULES.md` | Also needs |
|---|---|---|---|
| Slack to Linear | `{ "id": "linear-acme", "type": "linear", "guide": "linear", "team": "ACM" }` | Bug reports and feature requests go to linear-acme, one issue each, in project "Customer requests". | Linear connector |
| Slack to Attio | `{ "id": "attio-acme", "type": "attio", "guide": "attio", "workspace": "acme" }` | Leads, deals and follow-ups go to attio-acme, one deal per company. | Attio connector. `im:history` on the Slack token for a private DM, marked `"private": true`. |
| Slack to GitHub | `{ "id": "docs-acme", "type": "github", "guide": "github", "repo": "acme/docs", "branch": "main" }` | Client decisions go to docs-acme as a new file in `decisions/`, named by date and topic. | Push access to the repo, and the repo cloned in the run |
