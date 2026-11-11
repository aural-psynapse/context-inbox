"""Find project folders, check their config, and print what the run should use.

Usage:
  python3 connector/check.py [PROJECTS_DIR] [PROJECT]

PROJECTS_DIR  folder holding one subfolder per project. Defaults to the
              CONTEXT_INBOX_PROJECTS env var.
PROJECT       check only this project folder name.

A project folder holds config.json and RULES.md. In config, `reader` and
`guide` take either an integration name (a folder in integrations/) or a
path relative to the project folder.

Prints one JSON object per project with resolved paths. Exits 1 when any
project has an error, so a run stops before reading or writing anything.
"""

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BAD_ID = re.compile(r"[#\s]")


def resolve(project: Path, value: str, kind: str) -> Path:
    if "/" in value:
        return project / value
    name = "reader.py" if kind == "reader" else "guide.md"
    return REPO / "integrations" / value / name


def check(project: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    out: dict = {"project": project.name, "folder": str(project), "errors": errors, "warnings": warnings}
    cfg_path = project / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        errors.append(f"config.json: {e}")
        return out
    if not (project / "RULES.md").exists():
        errors.append("RULES.md missing")
    page = cfg.get("review_page", "")
    if not page.startswith("https://claude.ai/"):
        errors.append("review_page must be a claude.ai artifact URL")
    out["review_page"] = page

    dests = {}
    for d in cfg.get("destinations", []):
        did = d.get("id", "")
        if not did or did in dests:
            errors.append(f"destination id missing or repeated: {did!r}")
            continue
        guide = resolve(project, d.get("guide", d.get("type", "")), "guide")
        if not guide.exists():
            errors.append(f"{did}: guide not found at {guide}")
        dests[did] = {**d, "guide_path": str(guide)}
    out["destinations"] = list(dests.values())

    sources = []
    seen = set()
    for s in cfg.get("sources", []):
        sid = s.get("id", "")
        if not sid or sid in seen:
            errors.append(f"source id missing or repeated: {sid!r}")
            continue
        seen.add(sid)
        src = {k: v for k, v in s.items() if k != "channels"}
        if "how" in s:
            src["read"] = {"how": s["how"]}
        else:
            reader = resolve(project, s.get("reader", s.get("type", "")), "reader")
            if not reader.exists():
                errors.append(f"{sid}: reader not found at {reader}")
            src["read"] = {"run": ["python3", str(reader)] if reader.suffix == ".py" else [str(reader)]}
        secret = s.get("secret")
        if secret and not os.environ.get(secret):
            warnings.append(f"{sid}: env var {secret} is unset; fine only where a network proxy adds the token")
        channels = s.get("channels", [])
        if not channels:
            errors.append(f"{sid}: no channels")
        for ch in channels:
            cid = ch.get("id", "")
            if not cid or BAD_ID.search(cid):
                errors.append(f"{sid}: channel id {cid!r} must be the exact ID, not a name")
            for f in ch.get("feeds", []):
                if f not in dests:
                    errors.append(f"{sid}/{cid}: feeds unknown destination {f!r}")
        src["channels"] = channels
        sources.append(src)
    out["sources"] = sources
    return out


def main() -> None:
    args = sys.argv[1:]
    root = Path(args[0]) if args else Path(os.environ.get("CONTEXT_INBOX_PROJECTS", ""))
    if not str(root) or not root.is_dir():
        sys.exit(__doc__)
    only = args[1] if len(args) > 1 else None
    folders = sorted(p for p in root.iterdir() if (p / "config.json").exists() and (not only or p.name == only))
    if not folders:
        sys.exit(f"no project folder with config.json in {root}" + (f" named {only!r}" if only else ""))
    failed = False
    for p in folders:
        r = check(p)
        failed |= bool(r["errors"])
        print(json.dumps(r, indent=2, ensure_ascii=False))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
