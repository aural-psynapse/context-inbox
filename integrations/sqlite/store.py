"""Review store in one SQLite file: the items, the saved cursors and the run log.

Usage:
  python3 integrations/sqlite/store.py DB list COLLECTION
  python3 integrations/sqlite/store.py DB get COLLECTION ID
  python3 integrations/sqlite/store.py DB set COLLECTION ID < doc.json
  python3 integrations/sqlite/store.py DB update COLLECTION ID < keys.json
  python3 integrations/sqlite/store.py DB delete COLLECTION ID

DB          path to the file. It is made on first use.
COLLECTION  proposals, state or runs.

list prints a JSON array, each doc with its `id`. get prints one doc, or null.
set replaces the doc with the JSON object on stdin. update replaces only the
top-level keys that object names and keeps the rest. It exits 1 when the doc
does not exist.
"""

import json
import sqlite3
import sys
from contextlib import closing

COLLECTIONS = ("proposals", "state", "runs")


class StoreError(Exception):
    pass


class Refused(StoreError):
    """The doc exists, and the caller's `refuse` check said it must not change."""


def _open(db: str) -> sqlite3.Connection:
    # isolation_level=None: each write below opens and closes its own transaction.
    con = sqlite3.connect(db, timeout=10, isolation_level=None)
    con.execute(
        "CREATE TABLE IF NOT EXISTS docs (collection TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, "
        "PRIMARY KEY (collection, id))"
    )
    return con


def _known(collection: str) -> None:
    if collection not in COLLECTIONS:
        raise StoreError(f"unknown collection {collection!r}. Use one of: {', '.join(COLLECTIONS)}")


def _object(data) -> dict:
    if not isinstance(data, dict):
        raise StoreError("a doc must be a JSON object")
    return data


def list_docs(db: str, collection: str) -> list:
    _known(collection)
    with closing(_open(db)) as con:
        rows = con.execute("SELECT id, data FROM docs WHERE collection = ? ORDER BY id", (collection,)).fetchall()
    return [{**json.loads(data), "id": doc_id} for doc_id, data in rows]


def get_doc(db: str, collection: str, doc_id: str):
    _known(collection)
    with closing(_open(db)) as con:
        row = con.execute("SELECT data FROM docs WHERE collection = ? AND id = ?", (collection, doc_id)).fetchone()
    return {**json.loads(row[0]), "id": doc_id} if row else None


def set_doc(db: str, collection: str, doc_id: str, data: dict) -> None:
    _known(collection)
    text = json.dumps(_object(data), ensure_ascii=False)
    with closing(_open(db)) as con:
        con.execute("INSERT OR REPLACE INTO docs (collection, id, data) VALUES (?, ?, ?)", (collection, doc_id, text))


def update_doc(db: str, collection: str, doc_id: str, keys: dict, refuse=None) -> dict:
    """Replace the top-level keys given and keep the rest. `refuse(doc)` may return a reason to stop."""
    _known(collection)
    _object(keys)
    with closing(_open(db)) as con:
        # Take the write lock before reading, so two writers cannot both merge into the same old doc.
        con.execute("BEGIN IMMEDIATE")
        try:
            row = con.execute("SELECT data FROM docs WHERE collection = ? AND id = ?", (collection, doc_id)).fetchone()
            if not row:
                raise StoreError(f"no doc {doc_id!r} in {collection}")
            doc = json.loads(row[0])
            reason = refuse(doc) if refuse else None
            if reason:
                raise Refused(reason)
            doc.update(keys)
            con.execute(
                "UPDATE docs SET data = ? WHERE collection = ? AND id = ?",
                (json.dumps(doc, ensure_ascii=False), collection, doc_id),
            )
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    return {**doc, "id": doc_id}


def delete_doc(db: str, collection: str, doc_id: str) -> None:
    _known(collection)
    with closing(_open(db)) as con:
        con.execute("DELETE FROM docs WHERE collection = ? AND id = ?", (collection, doc_id))


def _agent_may_write(db: str, verb: str, doc_id: str, data) -> None:
    """The command line is what a run uses, so it never approves or rejects. Only the review page decides."""
    status = ((data or {}).get("decision") or {}).get("status") if isinstance(data, dict) else None
    if status not in (None, "pending"):
        raise StoreError("only a person on the review page approves or rejects an item")
    old = get_doc(db, "proposals", doc_id)
    if not old or not (old.get("pushed") or (old.get("decision") or {}).get("status") in ("approved", "rejected")):
        return
    # A decided item is frozen. The one write left is saving `pushed` on an approved, unwritten item.
    approved = (old.get("decision") or {}).get("status") == "approved"
    if verb == "update" and set(data) == {"pushed"} and approved and not old.get("pushed"):
        return
    raise StoreError(f"item {doc_id!r} is decided or written. It can no longer change.")


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 3 or args[1] not in ("list", "get", "set", "update", "delete"):
        sys.exit(__doc__)
    db, verb, collection, *rest = args
    if (verb == "list") != (not rest) or len(rest) > 1:
        sys.exit(__doc__)
    try:
        if verb == "list":
            print(json.dumps(list_docs(db, collection), indent=2, ensure_ascii=False))
        elif verb == "get":
            print(json.dumps(get_doc(db, collection, rest[0]), indent=2, ensure_ascii=False))
        elif verb == "delete":
            if collection == "proposals":
                _agent_may_write(db, verb, rest[0], {})
            delete_doc(db, collection, rest[0])
        else:
            data = json.load(sys.stdin)
            if collection == "proposals":
                _agent_may_write(db, verb, rest[0], data)
            if verb == "set":
                set_doc(db, collection, rest[0], data)
            else:
                update_doc(db, collection, rest[0], data)
    except (StoreError, ValueError, sqlite3.Error) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
