# Slack Worker: runs within a minute of each message

[`worker.js`](worker.js) is a Cloudflare Worker for a project on the `claude-artifact` review page. Slack sends it each new message, and it starts the project's cloud run through the run's API trigger. Approving an item on the review page starts a run the same way. Nobody needs a computer switched on.

- A message in a watched channel starts a run about 15 seconds later. Messages that arrive in between join that run.
- Two runs start at least 90 seconds apart.
- The Worker reads no message itself. It only says "run now".
- Cloudflare's free plan covers it. Each run uses the Claude plan of the person who owns the run.

## Set up

1. **The cloud run.** Make a Claude Code scheduled task with no schedule and the prompt in [`runner/prompt.txt`](../../runner/prompt.txt). Its project folder cannot come from `projects/`, since git ignores that folder. Store the project's `config.json` and `RULES.md` on the review page instead, in `project/config` (`{ "json": "<config.json text>" }`) and `project/rules` (`{ "text": "<RULES.md text>" }`), and have the prompt write both to a temporary folder before the run. On the task's page, add an **API** trigger and press **Generate token**.
2. **The Worker.** In the project folder, write a `wrangler.toml`:
   ```toml
   name = "slack-context-inbox-<project>"
   main = "<path to context-inbox>/integrations/slack/worker.js"
   compatibility_date = "2026-11-01"

   [vars]
   FIRE_URL = "<the API trigger's Fire URL>"
   CHANNELS = "<the channel ids in config.json, comma-separated>"
   MCP_PATH = "<a long random string>"

   [[durable_objects.bindings]]
   name = "RUNS"
   class_name = "Runs"

   [[migrations]]
   tag = "v1"
   new_sqlite_classes = ["Runs"]
   ```
   Run `npx wrangler deploy`, then store the two secrets, each copied first: `pbpaste | npx wrangler secret put FIRE_TOKEN` and `pbpaste | npx wrangler secret put SLACK_SIGNING_SECRET`. The signing secret is on the Slack app's **Basic Information** page.
3. **Slack.** On the Slack app that holds the reader's token, open **Event Subscriptions**, turn events on, and set the Request URL to the Worker's address. Under **Subscribe to events on behalf of users**, add `message.channels`, `message.groups` and `message.im`, then save.
4. **Approving starts a run.** In claude.ai, open Settings, Connectors, and add a custom connector named `Context Inbox runs` with the address `https://<worker address>/mcp/<MCP_PATH>`. Set `"run_connector": "Context Inbox runs"` in `config.json` and in `project/config`. Publish the review page with the `mcp` capability for that connector and its `run_now` tool.

## Check it

- Post a message in a watched channel. A run shows on the task's page within a minute, and the page's run log gets a new entry when it ends.
- `npx wrangler tail` shows each request the Worker gets.
