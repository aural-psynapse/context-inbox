"""Attach a file to an Attio record through Attio's file upload API.

Usage:
  python3 integrations/attio/upload.py CONFIG DEST_ID OBJECT RECORD_ID FILE

OBJECT     the object slug, such as deals or companies
RECORD_ID  the record's id
FILE       the local file to attach, at most 50 MB

Token: the env var named by the destination's "secret", an Attio API token
with the file:read-write, object_configuration:read and record_permission:read
scopes. When it is unset (cloud runs), the request goes out without a token and
the network proxy adds it. Prints Attio's JSON reply.
"""

import json
import mimetypes
import os
import sys
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scratch import scratch_path  # noqa: E402

API = "https://api.attio.com/v2/files/upload"


def main() -> None:
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    config, dest_id, obj, record_id, file = sys.argv[1:]
    cfg = json.loads(Path(config).read_text())
    dest = next((d for d in cfg.get("destinations", []) if d.get("id") == dest_id), None)
    if not dest:
        sys.exit(f"no destination with id {dest_id!r} in {config}")
    token = os.environ.get(dest.get("secret", ""), "")
    # Only a downloaded file or one in the project folder goes out, never a key file elsewhere.
    path = scratch_path(file, also=[Path(config).resolve().parent])
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("object", obj), ("record_id", record_id)):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n".encode()
        + path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{b}--\r\n".encode())
    headers = {"Content-Type": f"multipart/form-data; boundary={b}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API, data=b"".join(parts), method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        print(r.read().decode())


if __name__ == "__main__":
    main()
