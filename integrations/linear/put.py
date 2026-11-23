"""Upload a file to the signed URL that Linear's prepare_attachment_upload returns.

Usage:
  python3 integrations/linear/put.py URL FILE HEADERS_JSON

HEADERS_JSON is the uploadRequest.headers object, passed as one JSON string.
Linear signs every header, so they go out exactly as given. The URL expires
60 seconds after it is issued. Prints the HTTP status.
"""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scratch import scratch_path  # noqa: E402


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    url, file, headers = sys.argv[1:]
    req = urllib.request.Request(url, data=scratch_path(file).read_bytes(), method="PUT", headers=json.loads(headers))
    with urllib.request.urlopen(req, timeout=120) as r:
        print(r.status)


if __name__ == "__main__":
    main()
