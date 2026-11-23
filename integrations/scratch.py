"""Keep the files a reader or a download writes inside a temporary folder.

A run starts the repo's readers and download scripts with paths it chooses.
These scripts write only under the system temporary folder or /tmp, so a run
cannot point them at a program, a config or the review store and overwrite it.
"""

import sys
import tempfile
from pathlib import Path

ROOTS = {Path(tempfile.gettempdir()).resolve(), Path("/tmp").resolve()}


def scratch_path(value: str) -> Path:
    path = Path(value).resolve()
    if not any(root == path or root in path.parents for root in ROOTS):
        sys.exit(f"{value}: write the cursors file and output folder inside a temporary folder, such as /tmp")
    return path
