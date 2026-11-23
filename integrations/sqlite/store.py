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

On proposals the command line never approves or rejects, never changes or
deletes a decided item, and saves `pushed` only alone, on an approved item.
"""

import hashlib
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


def write(db: str, collection: str, doc_id: str, change) -> dict | None:
    """Read, change and save one doc under one lock. `change(old or None)` returns the new doc, or None to delete."""
    _known(collection)
    with closing(_open(db)) as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            row = con.execute("SELECT data FROM docs WHERE collection = ? AND id = ?", (collection, doc_id)).fetchone()
            new = change(json.loads(row[0]) if row else None)
            if new is None:
                con.execute("DELETE FROM docs WHERE collection = ? AND id = ?", (collection, doc_id))
            else:
                text = json.dumps({k: v for k, v in _object(new).items() if k != "id"}, ensure_ascii=False)
                con.execute(
                    "INSERT OR REPLACE INTO docs (collection, id, data) VALUES (?, ?, ?)", (collection, doc_id, text)
                )
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    return None if new is None else {**new, "id": doc_id}


def text_rev(doc: dict) -> str:
    """A fingerprint of everything a reviewer sees on an item. Equal text gives an equal fingerprint, always."""
    seen = {k: v for k, v in doc.items() if k not in ("id", "decision", "pushed", "rev")}
    return hashlib.sha256(json.dumps(seen, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _status(doc) -> str:
    return ((doc or {}).get("decision") or {}).get("status") or "pending"


def decided(doc) -> bool:
    return bool(doc) and (bool(doc.get("pushed")) or _status(doc) in ("approved", "rejected"))


def agent_change(verb: str, data=None):
    """What a run may do to an item: everything except deciding, and nothing once a person decided.

    The one write left on a decided item is `pushed`, alone, on an approved item not written yet.
    Every other change sets `rev` to the fingerprint of the new text, so an approval given to other text
    no longer counts, even after a withdraw and a new item with the same id.
    """
    data = _object(data if data is not None else {})

    def change(old):
        if verb == "delete":
            if not old:
                raise StoreError("there is no such item")
            if decided(old):
                raise Refused("the item is decided or written. It can no longer change.")
            return None
        if ((data.get("decision") or {}).get("status") or "pending") != "pending":
            raise Refused("only a person on the review page approves or rejects an item")
        if "pushed" in data:
            if verb != "update" or set(data) != {"pushed"}:
                raise Refused("save pushed alone, with update, after the write went through")
            if not old or _status(old) != "approved" or old.get("pushed"):
                raise Refused("pushed goes only on an approved item that is not written yet")
            return {**old, **data}
        if decided(old):
            raise Refused("the item is decided or written. Put the news in a new item.")
        if verb == "update" and not old:
            raise StoreError("there is no such item")
        new = {**old, **data} if verb == "update" else dict(data)
        new["rev"] = text_rev(new)
        return new

    return change


def page_change(decision: dict):
    """What the review page may do: set `decision` on an unwritten item, for the text the person saw."""
    _object(decision)

    def change(old):
        if not old:
            raise StoreError("there is no such item")
        if old.get("pushed"):
            raise Refused("This item is already written. It can no longer change.")
        # An item saved before fingerprints existed gets one now, from the text the page showed.
        rev = old.get("rev") or text_rev(old)
        if str(decision.get("rev") or "") not in (rev, "" if not old.get("rev") else rev):
            raise Refused("This item changed while you looked at it. Read the new text, then decide again.")
        return {**old, "rev": rev, "decision": {**decision, "rev": rev}}

    return change


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
        elif collection == "proposals":
            # The command line is what a run uses, so it follows the run's rules.
            write(db, collection, rest[0], agent_change(verb, None if verb == "delete" else json.load(sys.stdin)))
        elif verb == "delete":
            delete_doc(db, collection, rest[0])
        elif verb == "set":
            set_doc(db, collection, rest[0], json.load(sys.stdin))
        else:
            update_doc(db, collection, rest[0], json.load(sys.stdin))
    except (StoreError, ValueError, sqlite3.Error) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
