# Example projects repo

Keep a repo shaped like this one private. Each folder is one project.

```
acme/
  config.json    sources, channels, destinations, and which channel feeds which
  RULES.md       who is who, what counts, what goes where
```

`reader` and `guide` in `config.json` take an integration name from `integrations/` in context-inbox, or a path inside the project folder for one you wrote yourself, such as `readers/discourse.py` or `guides/notion.md`.

Check a projects repo with:

```
python3 connector/check.py <projects repo> [project]
```
