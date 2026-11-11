# Contributing

Thanks for helping. Issues and pull requests are welcome.

## Before you open a pull request

- Run the tests: `python3 -m unittest discover -s tests`.
- Keep the repo generic. Real company names, channel IDs, people and links belong in a projects repo, not here.
- Readers stay Python 3.10+ with the standard library only.
- After changing `ui/review.html`, take a screenshot in a browser and attach it to the pull request.

## Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org). The type sets the next version:

| Type | Example | Version change |
|---|---|---|
| `fix:` | `fix: keep the cursor when a channel fails` | 0.5.0 to 0.5.1 |
| `feat:` | `feat: add a Notion guide` | 0.5.0 to 0.6.0 |
| `feat!:` | `feat!: rename feeds to targets` | 0.5.0 to 1.0.0 |
| `docs:`, `chore:`, `ci:`, `refactor:`, `test:` | `docs: fix a typo` | none |

One line, no trailers.

## Adding an integration

A source needs a reader and a destination needs a guide. [AGENTS.md](AGENTS.md) gives both formats. Put them in `integrations/<name>/`, add a recipe to `integrations/recipes/`, and list them in the README.
