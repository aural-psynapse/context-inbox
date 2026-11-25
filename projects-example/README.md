# Example project

Copy a folder from here into `projects/` at the top of context-inbox, such as `projects/acme/`. Each folder in `projects/` is one project. Git ignores `projects/`, so your settings never get pushed.

```
acme/
  config.json    sources, channels, destinations, and which channel feeds which
  RULES.md       who is who, what counts, what goes where
```

`acme/config.json` uses fake IDs. Replace every one with real values before a run. It keeps its items in a SQLite file, the default `review_store`.

`reader`, `guide` and `review_store` in `config.json` take an integration name from `integrations/` in context-inbox, such as `slack`. For one you wrote yourself, give a path inside the project folder, such as `readers/forum.py` or `./notion.md`. A value is a path when it contains `/` or ends in a file extension.

Check every project, or one by its folder name:

```
python3 connector/check.py [project]
```
