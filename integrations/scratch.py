"""Keep the files a reader or a download writes inside a temporary folder.

A run starts the repo's readers and download scripts with paths it chooses.
These scripts write only under the system temporary folder or /tmp, so a run
cannot point them at a program, a config or the review store and overwrite it.
"""

import sys
import tempfile
from pathlib import Path

ROOTS = {Path(tempfile.gettempdir()).resolve(), Path("/tmp").resolve()}


def scratch_path(value: str, also=()) -> Path:
    """The path, when it sits in a temporary folder or in one of `also`. Otherwise stop the script."""
    path = Path(value).resolve()
    roots = ROOTS | {Path(a).resolve() for a in also}
    if not any(root == path or root in path.parents for root in roots):
        where = "a temporary folder, such as /tmp" + (" or the project folder" if also else "")
        sys.exit(f"{value}: use a file inside {where}")
    return path
