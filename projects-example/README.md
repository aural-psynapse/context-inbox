# Example projects repo

Keep a repo shaped like this one private. Each folder is one project.

```
acme/
  config.json    sources, channels, destinations, and which channel feeds which
  RULES.md       who is who, what counts, what goes where
```

`acme/config.json` uses fake IDs. Replace every one with real values before a run. It keeps its items in a SQLite file, the default `review_store`.

`reader`, `guide` and `review_store` in `config.json` take an integration name from `integrations/` in context-inbox, such as `slack`. For one you wrote yourself, give a path inside the project folder, such as `readers/forum.py` or `./notion.md`. A value is a path when it contains `/` or ends in a file extension.

Check a projects repo with:

```
python3 connector/check.py <projects repo> [project]
```
