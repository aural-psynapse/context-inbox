---
name: context-inbox-setup
description: "Set up context-inbox for a new project, or add a source or destination to one. Use when someone asks to connect Slack, email or another source to Linear, Attio, GitHub or another tool through a review page."
---

Follow "Set up a project" in AGENTS.md at the repo root.

- Start from `projects-example/acme/` and the closest recipe in `integrations/recipes.md`.
- Reuse an integration in `integrations/` by name. Write a new reader or guide into the project folder only when none fits, in the formats AGENTS.md gives.
- Done when `python3 connector/check.py <projects repo> <project>` exits 0 and the first run's items show on the review page.
