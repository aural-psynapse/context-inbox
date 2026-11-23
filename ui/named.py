"""Print the review page with the project's name in the browser tab and at the top left.

Usage:
  python3 ui/named.py CONFIG [OUT]

CONFIG is the project's config.json. When it sets "name", the page shows that
name in place of "Context Inbox". OUT is a file to write; without it the page
goes to stdout. integrations/sqlite/serve.py uses the same function, and a page
published to claude.ai is published from OUT.
"""

import html
import json
import sys
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "review.html"
DEFAULT = "Context Inbox"


def name_of(config) -> str:
    """The config's name, or "Context Inbox" when there is no config or no name."""
    try:
        name = json.loads(Path(config).read_text()).get("name") if config else None
    except (OSError, ValueError):
        name = None
    return name.strip() if isinstance(name, str) and name.strip() else DEFAULT


def page(name: str = DEFAULT) -> str:
    text = PAGE.read_text()
    safe = html.escape(name)
    for old, new in (
        (f"<title>{DEFAULT}</title>", f"<title>{safe}</title>"),
        (f'<div class="brand">{DEFAULT}</div>', f'<div class="brand">{safe}</div>'),
    ):
        if text.count(old) != 1:
            raise SystemExit(f"ui/review.html no longer holds {old!r} once. Update ui/named.py with it.")
        text = text.replace(old, new)
    return text


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    out = page(name_of(sys.argv[1]))
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(out)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
