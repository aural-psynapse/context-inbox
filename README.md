# context-inbox

Reads updates from chat tools, proposes changes to work tools, and writes each change only after a person approves it on a review page.

- Sources today: Slack. Destinations today: Linear, Attio, GitHub.
- Each project keeps its own `config.json` and `RULES.md` in a separate private repo. See [`config.example.json`](config.example.json).
- Instructions for the agent that runs it: [AGENTS.md](AGENTS.md).
