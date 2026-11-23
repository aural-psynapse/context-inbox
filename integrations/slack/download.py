"""Download one file shared in Slack, to attach it to a destination record.

Usage:
  python3 integrations/slack/download.py CONFIG SOURCE_ID FILE_ID OUT_DIR

FILE_ID is the "id" of a file in a message line, such as F0CHMV0K07N.
Saves the file as OUT_DIR/<file name> and prints that path, then its media
type and size in bytes, one per line. Uses the same token as the reader.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reader import fetch, make_call
from scratch import scratch_path  # noqa: E402


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    config, source_id, file_id, out_dir = sys.argv[1:]
    cfg = json.loads(Path(config).read_text())
    src = next((s for s in cfg.get("sources", []) if s.get("id") == source_id), None)
    if not src:
        sys.exit(f"no source with id {source_id!r} in {config}")
    token = os.environ.get(src.get("secret", ""), "")
    f = make_call(token)("files.info", file=file_id)["file"]
    url = f.get("url_private_download") or f.get("url_private")
    if f.get("is_external") or not url:
        sys.exit(f"{file_id}: no downloadable copy in Slack")
    data = fetch(url, token)
    name = re.sub(r"[^\w.\- ]", "_", f.get("name") or file_id).strip() or file_id
    out = scratch_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    path.write_bytes(data)
    print(path.resolve())
    print(f.get("mimetype") or "application/octet-stream")
    print(len(data))


if __name__ == "__main__":
    main()
