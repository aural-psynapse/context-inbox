# Recipes

Each recipe pairs the Slack reader with one destination. Merge the parts you need into your project's `config.json` and `RULES.md`. [`projects-example/acme/`](../projects-example/acme/) shows a full project.

Every recipe uses this source. List each channel with the destinations it `feeds`:

```json
"sources": [ { "id": "slack-acme", "type": "slack", "reader": "slack", "secret": "SLACK_TOKEN_ACME",
  "channels": [ { "id": "C0123456789", "feeds": ["linear-acme"] } ] } ]
```

The Slack token needs `files:read` so the reader can read files shared in messages. In cloud runs, store it as a network secret for `files.slack.com` as well as `slack.com`.

| Recipe | Destination in `config.json` | Line in `RULES.md` | Also needs |
|---|---|---|---|
| Slack to Linear | `{ "id": "linear-acme", "type": "linear", "guide": "linear", "team": "ACM" }` | Bug reports and feature requests go to linear-acme, one issue each, in project "Customer requests". | Linear connector |
| Slack to Attio | `{ "id": "attio-acme", "type": "attio", "guide": "attio", "workspace": "acme" }` | Leads, deals and follow-ups go to attio-acme, one deal per company. | Attio connector. An Attio API token in `secret` to attach files. `im:history` on the Slack token for a private DM, marked `"private": true`. |
| Slack to GitHub | `{ "id": "docs-acme", "type": "github", "guide": "github", "repo": "acme/docs", "branch": "main" }` | Client decisions go to docs-acme as a new file in `decisions/`, named by date and topic. | Push access to the repo, and the repo cloned in the run |

## Cal.com bookings as a source

A source of type `calcom` reads new bookings, and each cancellation, move or confirmation of one, as messages. A channel id is an event type slug, or `all` for every booking.

```json
"sources": [ { "id": "cal-acme", "type": "calcom", "reader": "calcom", "secret": "CAL_API_KEY_ACME",
  "channels": [ { "id": "intro-call", "feeds": ["attio-acme"] } ] } ]
```

The secret holds a Cal.com API key, which starts with `cal_`, made under Settings, Developer, API keys. In cloud runs, store it as a network secret for `api.cal.com`.

## Gmail as a source

A source of type `gmail` reads emails that match a Gmail search. Each channel has a short `id` and a `query`.

```json
"sources": [ { "id": "mail-acme", "type": "gmail", "reader": "gmail", "secret": "GMAIL_ACME",
  "channels": [ { "id": "sales", "query": "to:sales@acme.com", "feeds": ["attio-acme"] } ] } ]
```

The secret holds JSON `{"client_id", "client_secret", "refresh_token"}` from a Google OAuth client with the `gmail.readonly` scope, or a short-lived access token. In cloud runs, store it as a network secret for `gmail.googleapis.com` and `oauth2.googleapis.com`.
