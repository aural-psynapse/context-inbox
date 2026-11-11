"""Find project folders, check their config, and print what the run should use.

Usage:
  python3 connector/check.py PROJECTS_DIR [PROJECT]
  CONTEXT_INBOX_PROJECTS=PROJECTS_DIR python3 connector/check.py

PROJECTS_DIR  folder holding one subfolder per project.
PROJECT       check only this project folder name.

A project folder holds config.json and RULES.md. In config, `reader` and
`guide` take an integration name (a folder in integrations/, such as "slack")
or a path inside the project folder. A value is a path when it contains "/"
or ends in a file extension, such as "readers/forum.py" or "./notion.md".

Prints one JSON object per project with resolved paths. Exits 1 when any
project has an error, so a run stops before reading or writing anything.
"""

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SAFE_ID = re.compile(r"^[A-Za-z0-9_.~:@+-]+$")
SLACK_CHANNEL = re.compile(r"^[CDG][A-Z0-9]{6,}$")
PAGE = re.compile(r"^https://claude\.ai/(code/)?artifact/[A-Za-z0-9-]+$")
TOP_KEYS = {"project", "review_page", "routine", "sources", "destinations"}
TYPOS = {
    "feed": "feeds",
    "channel": "channels",
    "destination": "destinations",
    "source": "sources",
    "guides": "guide",
    "readers": "reader",
    "privat": "private",
}
DEST_KEYS = {"id", "type", "guide"}  # other keys are read by the guide


def is_path(value: str) -> bool:
    return "/" in value or bool(re.search(r"\.[A-Za-z0-9]+$", value))


def resolve(project: Path, value: str, kind: str, errors: list, label: str):
    if not isinstance(value, str) or not value:
        errors.append(f"{label}: {kind} must be a non-empty string")
        return None
    if is_path(value):
        p = (project / value).resolve()
        if project.resolve() not in p.parents:
            errors.append(f"{label}: {kind} {value!r} points outside the project folder")
            return None
    else:
        p = REPO / "integrations" / value / ("reader.py" if kind == "reader" else "guide.md")
    if not p.is_file():
        errors.append(f"{label}: {kind} not found at {p}")
        return None
    return p


def unknown(d: dict, allowed, label: str, errors: list) -> None:
    """Catch misspelt keys. Sources and channels may carry extra keys for their reader."""
    known = {"id", "type", "reader", "how", "secret", "channels", "feeds", "private", "guide"}
    for k in d:
        if k not in known and k.lower() in known:
            errors.append(f"{label}: unknown key {k!r}, did you mean {k.lower()!r}? Keys are case-sensitive.")
        elif k in TYPOS:
            errors.append(f"{label}: unknown key {k!r}, did you mean {TYPOS[k]!r}?")
        elif allowed is not None and k not in allowed:
            errors.append(f"{label}: unknown key {k!r}")


def check(project: Path) -> dict:
    errors: list = []
    warnings: list = []
    out: dict = {"project": project.name, "folder": str(project), "errors": errors, "warnings": warnings}
    try:
        cfg = json.loads((project / "config.json").read_text())
    except (OSError, ValueError) as e:
        errors.append(f"config.json: {e}")
        return out
    if not isinstance(cfg, dict):
        errors.append("config.json must hold an object")
        return out
    unknown(cfg, TOP_KEYS, "config", errors)
    if not (project / "RULES.md").is_file():
        errors.append("RULES.md missing")
    page = cfg.get("review_page")
    if not isinstance(page, str) or not PAGE.match(page) or re.search(r"replace|example|00000000", page):
        errors.append("review_page must be a published claude.ai artifact URL, not a placeholder")
    out["review_page"] = page
    routine = cfg.get("routine")
    if routine is not None and (not isinstance(routine, str) or not re.match(r"^trig_[A-Za-z0-9]+$", routine)):
        errors.append("routine must be a scheduled task id like trig_01ABC")

    dests: dict = {}
    raw_dests = cfg.get("destinations")
    if not isinstance(raw_dests, list) or not raw_dests:
        errors.append("destinations must be a non-empty list")
        raw_dests = []
    for i, d in enumerate(raw_dests):
        if not isinstance(d, dict):
            errors.append(f"destinations[{i}] must be an object")
            continue
        did = d.get("id")
        label = f"destination {did!r}"
        if not isinstance(did, str) or not SAFE_ID.match(did):
            errors.append(f"{label}: id must use only letters, digits and _ . ~ : @ + -")
            continue
        if did in dests:
            errors.append(f"{label}: id repeated")
            continue
        if not isinstance(d.get("type"), str) or not d.get("type"):
            errors.append(f"{label}: type missing")
        guide = resolve(project, d.get("guide", d.get("type")), "guide", errors, label)
        dests[did] = {**d, "guide_path": str(guide) if guide else None}
    out["destinations"] = list(dests.values())

    sources = []
    seen: set = set()
    raw_sources = cfg.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        errors.append("sources must be a non-empty list")
        raw_sources = []
    for i, s in enumerate(raw_sources):
        if not isinstance(s, dict):
            errors.append(f"sources[{i}] must be an object")
            continue
        sid = s.get("id")
        label = f"source {sid!r}"
        if not isinstance(sid, str) or not SAFE_ID.match(sid):
            errors.append(f"{label}: id must use only letters, digits and _ . ~ : @ + -")
            continue
        if sid in seen:
            errors.append(f"{label}: id repeated")
            continue
        seen.add(sid)
        unknown(s, None, label, errors)
        stype = s.get("type")
        if not isinstance(stype, str) or not stype:
            errors.append(f"{label}: type missing")
        src = {k: v for k, v in s.items() if k != "channels"}
        if "how" in s and "reader" in s:
            errors.append(f"{label}: set reader or how, not both")
        if "how" in s:
            if not isinstance(s["how"], str) or not s["how"].strip():
                errors.append(f"{label}: how must be plain instructions")
            src["read"] = {"how": s.get("how")}
        else:
            reader = resolve(project, s.get("reader", stype), "reader", errors, label)
            if reader:
                src["read"] = {"run": ["python3", str(reader)] if reader.suffix == ".py" else [str(reader)]}
        secret = s.get("secret")
        if isinstance(secret, str) and secret and not os.environ.get(secret):
            warnings.append(f"{label}: env var {secret} is unset. Fine only where a network proxy adds the token.")
        channels = s.get("channels")
        if not isinstance(channels, list) or not channels:
            errors.append(f"{label}: channels must be a non-empty list")
            channels = []
        cids: set = set()
        for j, ch in enumerate(channels):
            if not isinstance(ch, dict):
                errors.append(f'{label}: channels[{j}] must be an object like {{"id": ..., "feeds": [...]}}')
                continue
            cid = ch.get("id")
            if not isinstance(cid, str):
                errors.append(f"{sid}: channels[{j}] id must be a string")
                continue
            clabel = f"{sid}/{cid}"
            unknown(ch, None, clabel, errors)
            if not isinstance(cid, str) or not cid or re.search(r"[#\s/]", cid):
                errors.append(f"{clabel}: channel id must be the exact ID, not a name")
            elif stype == "slack" and not SLACK_CHANNEL.match(cid):
                errors.append(f"{clabel}: Slack channel ids look like C0123456789, not a name")
            if cid in cids:
                errors.append(f"{clabel}: channel listed twice")
            cids.add(cid)
            feeds = ch.get("feeds")
            if not isinstance(feeds, list) or not feeds:
                errors.append(f"{clabel}: feeds must list at least one destination id")
                feeds = []
            for f in feeds:
                if not isinstance(f, str) or f not in dests:
                    errors.append(f"{clabel}: feeds unknown destination {f!r}")
            if "private" in ch and not isinstance(ch["private"], bool):
                errors.append(f"{clabel}: private must be true or false")
        src["channels"] = channels
        sources.append(src)
    out["sources"] = sources
    return out


def main() -> None:
    args = sys.argv[1:]
    root_arg = args[0] if args else os.environ.get("CONTEXT_INBOX_PROJECTS", "")
    if not root_arg or not Path(root_arg).is_dir():
        sys.exit(__doc__)
    root = Path(root_arg)
    only = args[1] if len(args) > 1 else None
    folders = sorted(p for p in root.iterdir() if (p / "config.json").exists() and (not only or p.name == only))
    if not folders:
        sys.exit(f"no project folder with config.json in {root}" + (f" named {only!r}" if only else ""))
    failed = False
    for p in folders:
        r = check(p)
        failed |= bool(r["errors"])
        print(json.dumps(r, indent=2, ensure_ascii=False))
        for e in r["errors"]:
            print(f"error: {p.name}: {e}", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
