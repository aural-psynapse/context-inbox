"""Read new and changed Cal.com bookings for one source in a project config.

Usage:
  python3 integrations/calcom/reader.py CONFIG SOURCE_ID CURSORS OUT_DIR [--only CHANNEL_ID]

CONFIG     path to the project's config.json
SOURCE_ID  the "id" of a source in that config
CURSORS    JSON file {channel_id: last_change_time}. A missing file, an empty file
           or {} means read every booking from the start. Rewritten at the end.
OUT_DIR    folder for <channel_id>.jsonl, one message per line, oldest first
--only     read just this channel

Channels: a channel's "id" is an event type slug, such as "intro-call", and takes
bookings of that event type only. The id "all" takes every booking.

Token: a Cal.com API key (it starts with cal_) in the env var named by the
source's "secret". When it is unset (cloud runs), requests go out without a key
and the network proxy adds it.

Each booking comes back once when it is made, and again each time it changes:
cancelled, moved to a new time, or confirmed. Every message about one booking
shares its "thread_ts", the booking's uid.

Cursor: the change time of the newest booking read, but never later than the
moment this run started, so a booking made while the run is reading comes back
next time.

A channel that fails keeps its old cursor and gets no output file. The other
channels still run. The script then exits 1.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.cal.com/v2/bookings"
API_VERSION = "2026-05-01"
TIMEOUT = 30
MAX_RETRIES = 8
PAGE = 100


def make_get(token: str):
    headers = {"cal-api-version": API_VERSION, "User-Agent": "context-inbox"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def get(params: dict) -> dict:
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers)
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    data = json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < MAX_RETRIES - 1:
                    time.sleep(int(e.headers.get("Retry-After", "5")))
                    continue
                raise
            if data.get("status") != "success":
                raise RuntimeError(f"bookings: {data.get('error') or data}")
            return data
        raise RuntimeError(f"bookings: rate limited {MAX_RETRIES} times")

    return get


def iso(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def changed_at(b: dict) -> str:
    return b.get("updatedAt") or b["createdAt"]


def bookings_since(get, after: str) -> list:
    """Every booking made or changed after `after`, each once, by its latest change."""
    found: dict = {}
    for key in ("afterCreatedAt", "afterUpdatedAt"):
        params: dict = {key: after, "limit": PAGE} if after else {"limit": PAGE}
        while True:
            data = get(params)
            for b in data.get("data", []):
                found[(b["uid"], changed_at(b))] = b
            page = data.get("pagination") or {}
            if not page.get("hasMore") or not page.get("nextCursor"):
                break
            params = {**params, "cursor": page["nextCursor"]}
        if not after:
            break
    return sorted(found.values(), key=lambda b: parse(changed_at(b)))


def what_happened(b: dict) -> str:
    status = b.get("status", "")
    if status == "cancelled":
        return "Booking cancelled"
    if b.get("rescheduledFromUid"):
        return "Booking moved to a new time"
    if status == "pending":
        return "Booking waiting for confirmation"
    if b.get("updatedAt") and b.get("updatedAt") != b.get("createdAt"):
        return "Booking changed"
    return "New booking"


def text_of(b: dict) -> str:
    start = parse(b["start"]).strftime("%Y-%m-%d %H:%M UTC")
    people = ", ".join(f"{a.get('name', '')} <{a.get('email', '')}>" for a in b.get("attendees", []))
    parts = [f"{what_happened(b)}: {b.get('title', '')}.", f"Starts {start}, {b.get('duration', '?')} minutes."]
    if people:
        parts.append(f"Booked by {people}.")
    slug = (b.get("eventType") or {}).get("slug")
    if slug:
        parts.append(f"Event type: {slug}.")
    if b.get("cancellationReason"):
        parts.append(f"Reason given: {b['cancellationReason']}")
    if b.get("reschedulingReason"):
        parts.append(f"Reason given: {b['reschedulingReason']}")
    if b.get("rescheduledFromUid"):
        parts.append(f"Replaces booking {b['rescheduledFromUid']}.")
    return " ".join(parts)


def message(src: dict, ch: dict, b: dict) -> dict:
    first = (b.get("attendees") or [{}])[0]
    return {
        "source": src["id"],
        "channel_id": ch["id"],
        "private": bool(ch.get("private")),
        "feeds": ch.get("feeds", []),
        "ts": f"{b['uid']}@{changed_at(b)}",
        "thread_ts": b["uid"],
        "date": parse(changed_at(b)).strftime("%Y-%m-%d %H:%M"),
        "author_id": first.get("email", ""),
        "author": first.get("name", ""),
        "text": text_of(b),
        "files": [],
        "link": f"https://app.cal.com/booking/{b['uid']}",
    }


def read(src: dict, cursors: dict, out_dir: Path, get, started: float, only=None) -> bool:
    """Write each channel's new messages and move its cursor. False when a channel failed."""
    ok = True
    for ch in src.get("channels", []):
        cid = ch["id"]
        if only and cid != only:
            continue
        try:
            rows = bookings_since(get, cursors.get(cid, ""))
        except Exception as e:  # noqa: BLE001 - one failed channel must not stop the others
            print(f"{cid}: failed: {e}", file=sys.stderr)
            ok = False
            continue
        if cid != "all":
            rows = [b for b in rows if (b.get("eventType") or {}).get("slug") == cid]
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / f"{cid}.jsonl", "w") as f:
            for b in rows:
                f.write(json.dumps(message(src, ch, b), ensure_ascii=False) + "\n")
        if rows:
            newest = parse(changed_at(rows[-1])).timestamp()
            cursors[cid] = iso(min(newest, started - 1))
        print(f"{cid}: {len(rows)} new")
    return ok


def main() -> None:
    args = sys.argv[1:]
    only = None
    if len(args) == 6 and args[4] == "--only":
        only = args[5]
        args = args[:4]
    if len(args) != 4:
        sys.exit(__doc__)
    config, source_id, cursors_path, out_dir = args
    started = time.time()
    cfg = json.loads(Path(config).read_text())
    src = next((s for s in cfg.get("sources", []) if s.get("id") == source_id), None)
    if not src:
        sys.exit(f"no source with id {source_id!r} in {config}")
    get = make_get(os.environ.get(src.get("secret", ""), ""))
    cursors_file = Path(cursors_path)
    raw = cursors_file.read_text().strip() if cursors_file.exists() else ""
    cursors = json.loads(raw) if raw else {}
    ok = read(src, cursors, Path(out_dir), get, started, only)
    cursors_file.write_text(json.dumps(cursors, indent=2) + "\n")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
