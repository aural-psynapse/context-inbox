"""Read new Slack messages for one source in a project config.

Usage:
  python3 sources/slack.py CONFIG SOURCE_ID CURSORS OUT_DIR [--only CHANNEL_ID]

CONFIG     path to the project's config.json
SOURCE_ID  the "id" of a source with "type": "slack" in that config
CURSORS    JSON file {channel_id: last_read_ts}; read at start, rewritten at end.
           The caller loads it from the review page db and saves it back after
           proposals are written, so a crashed run re-reads instead of skipping.
OUT_DIR    folder for <channel_id>.jsonl, one message per line

Token: the env var named by the source's "secret". When it is unset (cloud runs),
requests go out without a token and the network proxy adds it.

Thread replies: every run lists the channel's whole history and pulls replies
from any thread whose latest reply is newer than the cursor, however old the
thread is, so no reply is missed.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

def make_call(token: str):
    def call(method: str, **params: str) -> dict:
        url = f"https://slack.com/api/{method}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
        while True:
            try:
                with urllib.request.urlopen(req) as r:
                    data = json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(int(e.headers.get("Retry-After", "5")))
                    continue
                raise
            if not data.get("ok"):
                raise RuntimeError(f"{method}: {data.get('error')}")
            return data
    return call


def main() -> None:
    args = sys.argv[1:]
    only = None
    if len(args) == 6 and args[4] == "--only":
        only = args[5]
        args = args[:4]
    if len(args) != 4:
        sys.exit(__doc__)
    config, source_id, cursors_path, out_dir = args
    cfg = json.loads(Path(config).read_text())
    src = next((s for s in cfg["sources"] if s["id"] == source_id and s["type"] == "slack"), None)
    if not src:
        sys.exit(f"no slack source with id {source_id!r} in {config}")
    call = make_call(os.environ.get(src.get("secret", ""), ""))

    def paged(method: str, key: str, **params: str) -> list:
        out, cursor = [], ""
        while True:
            p = dict(params, limit="200")
            if cursor:
                p["cursor"] = cursor
            d = call(method, **p)
            out += d.get(key, [])
            cursor = d.get("response_metadata", {}).get("next_cursor", "")
            if not cursor:
                return out

    base = call("auth.test")["url"].rstrip("/")
    users = {u["id"]: (u.get("real_name") or u["name"]) for u in paged("users.list", "members")}
    cursors_file = Path(cursors_path)
    cursors = json.loads(cursors_file.read_text()) if cursors_file.exists() else {}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for ch in src["channels"]:
        cid = ch["id"]
        if only and cid != only:
            continue
        cursor = float(cursors.get(cid, "0"))
        # Whole history every run: a reply can land under a thread of any age.
        parents = paged("conversations.history", "messages", channel=cid)
        rows = [m for m in parents if float(m["ts"]) > cursor]
        for m in parents:
            if m.get("reply_count") and (float(m["ts"]) > cursor or float(m.get("latest_reply", "0")) > cursor):
                replies = paged("conversations.replies", "messages", channel=cid, ts=m["ts"])
                rows += [r for r in replies if r["ts"] != m["ts"] and float(r["ts"]) > cursor]
        seen, uniq = set(), []
        for m in sorted(rows, key=lambda m: float(m["ts"])):
            if m["ts"] not in seen:
                seen.add(m["ts"])
                uniq.append(m)
        with (out / f"{cid}.jsonl").open("w") as f:
            for m in uniq:
                f.write(json.dumps({
                    "source": source_id,
                    "channel_id": cid,
                    "private": bool(ch.get("private")),
                    "feeds": ch.get("feeds", []),
                    "ts": m["ts"],
                    "thread_ts": m.get("thread_ts"),
                    "date": time.strftime("%Y-%m-%d %H:%M", time.gmtime(float(m["ts"]))),
                    "author_id": m.get("user", ""),
                    "author": users.get(m.get("user", ""), m.get("username") or "?"),
                    "text": m.get("text", ""),
                    "files": [x.get("name") for x in m.get("files", [])],
                    "link": f"{base}/archives/{cid}/p{m['ts'].replace('.', '')}",
                }, ensure_ascii=False) + "\n")
        if uniq:
            cursors[cid] = max(m["ts"] for m in uniq)
        print(f"{cid}: {len(uniq)} new")
    cursors_file.write_text(json.dumps(cursors, indent=2) + "\n")


if __name__ == "__main__":
    main()
