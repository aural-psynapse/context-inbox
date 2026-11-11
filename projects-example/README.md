# Example projects repo

Keep a repo shaped like this one private. Each folder is one project.

```
acme/
  config.json    sources, channels, destinations, and which channel feeds which
  RULES.md       who is who, what counts, what goes where
```

`acme/config.json` uses fake IDs and a fake `review_page`. Replace every one with real values before a run.

`reader` and `guide` in `config.json` take an integration name from `integrations/` in context-inbox, such as `slack`. For one you wrote yourself, give a path inside the project folder, such as `readers/forum.py` or `./notion.md`. A value is a path when it contains `/` or ends in a file extension.

Check a projects repo with:

```
python3 connector/check.py <projects repo> [project]
```
