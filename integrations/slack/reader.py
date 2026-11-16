"""Read new Slack messages for one source in a project config.

Usage:
  python3 integrations/slack/reader.py CONFIG SOURCE_ID CURSORS OUT_DIR [--only CHANNEL_ID]

CONFIG     path to the project's config.json
SOURCE_ID  the "id" of a source in that config
CURSORS    JSON file {channel_id: last_read_ts}. A missing file, an empty file
           or {} means read every channel from the start. Rewritten at the end.
OUT_DIR    folder for <channel_id>.jsonl, one message per line, oldest first
--only     read just this channel

Token: the env var named by the source's "secret". When it is unset (cloud runs),
requests go out without a token and the network proxy adds it.

Thread replies: every run lists the channel's whole history and pulls replies
from any thread whose latest reply is newer than the cursor, however old the
thread is. Big channels take longer for that reason.

Cursor: the newest message read, but never later than the moment this run
started, so a message posted while the run is reading comes back next time.
A message edited after it was read keeps its time and is not read again.

Files: each file shared in a message comes back with its text. The reader
downloads plain text, Word (.docx), PDF (needs pdftotext on PATH) and Slack
canvases, and keeps the first 20,000 characters. A file it cannot read, such as
an image or a Google Doc link, gets an empty "text" and a "note" saying why.
The token needs the files:read scope. In cloud runs, store the token as a
network secret for files.slack.com as well as slack.com.

A channel that fails keeps its old cursor and gets no output file. The other
channels still run. The script then exits 1.
"""

import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

TIMEOUT = 30
MAX_RETRIES = 8
MAX_FILE_BYTES = 20_000_000
MAX_FILE_CHARS = 20_000
TEXT_TYPES = {"text", "markdown", "csv", "tsv", "json", "xml", "yaml", "html", "email", "post"}


def make_call(token: str):
    def call(method: str, **params: str) -> dict:
        url = f"https://slack.com/api/{method}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    data = json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < MAX_RETRIES - 1:
                    time.sleep(int(e.headers.get("Retry-After", "5")))
                    continue
                raise
            if not data.get("ok"):
                raise RuntimeError(f"{method}: {data.get('error')}")
            return data
        raise RuntimeError(f"{method}: rate limited {MAX_RETRIES} times")

    return call


def fetch(url: str, token: str) -> bytes:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read(MAX_FILE_BYTES + 1)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(int(e.headers.get("Retry-After", "5")))
                continue
            if e.code == 403:
                raise RuntimeError("403 Forbidden, the token likely lacks files:read") from e
            raise
    raise RuntimeError(f"rate limited {MAX_RETRIES} times")


def strip_tags(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|li|tr)>", "\n", markup)
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def pdf_text(data: bytes) -> str:
    if not shutil.which("pdftotext"):
        raise RuntimeError("PDF needs pdftotext on PATH")
    r = subprocess.run(["pdftotext", "-q", "-", "-"], input=data, capture_output=True, timeout=TIMEOUT, check=True)
    return r.stdout.decode("utf-8", "replace")


def file_of(f: dict, call, token: str) -> dict:
    """One shared file: name, type, link, and its text when the reader can read it."""
    if f.get("file_access") == "check_file_info":
        try:
            f = call("files.info", file=f["id"])["file"]
        except Exception as e:
            return {"name": f.get("id", "?"), "type": "", "link": "", "text": "", "note": f"files.info failed: {e}"}
    out = {
        "name": f.get("title") or f.get("name") or "?",
        "type": f.get("filetype", ""),
        "link": f.get("permalink", ""),
        "text": "",
    }
    kind, mime = out["type"], f.get("mimetype", "")
    url = f.get("url_private_download") or f.get("url_private")
    if f.get("is_external"):
        out["note"] = f"external file ({f.get('external_type') or 'link'}), read it through its own tool"
        return out
    if not url:
        out["note"] = "no download link"
        return out
    if (f.get("size") or 0) > MAX_FILE_BYTES:
        out["note"] = "file too large to read"
        return out
    readable = kind in TEXT_TYPES or mime.startswith("text/") or kind in ("docx", "pdf", "quip", "canvas")
    if not readable:
        out["note"] = "not a text file"
        return out
    try:
        data = fetch(url, token)
        if len(data) > MAX_FILE_BYTES:
            out["note"] = "file too large to read"
            return out
        if kind == "docx":
            text = docx_text(data)
        elif kind == "pdf":
            text = pdf_text(data)
        elif kind in ("html", "quip", "canvas") or mime == "text/html":
            text = strip_tags(data.decode("utf-8", "replace"))
        else:
            text = data.decode("utf-8", "replace")
    except Exception as e:  # one unreadable file must not drop the message
        out["note"] = f"could not read: {e}"
        return out
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS]
        out["note"] = f"cut to the first {MAX_FILE_CHARS} characters"
    out["text"] = text
    return out


def text_of(m: dict) -> str:
    """Message text, plus the text of attachments and forwarded messages."""
    parts = [m.get("text") or ""]
    for a in m.get("attachments", []):
        got = [a[k] for k in ("pretext", "title", "text") if a.get(k) and a[k] not in parts]
        if not got and a.get("fallback") and a["fallback"] not in parts:
            got = [a["fallback"]]
        parts += got
    return "\n".join(p for p in parts if p).strip()


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
    token = os.environ.get(src.get("secret", ""), "")
    call = make_call(token)

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
    raw = cursors_file.read_text().strip() if cursors_file.exists() else ""
    cursors = json.loads(raw) if raw else {}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    failed = []

    for ch in src.get("channels", []):
        cid = ch["id"]
        if only and cid != only:
            continue
        try:
            cursor = float(cursors.get(cid, "0"))
            parents = paged("conversations.history", "messages", channel=cid)
            rows = [m for m in parents if float(m["ts"]) > cursor]
            for m in parents:
                if m.get("reply_count") and (float(m["ts"]) > cursor or float(m.get("latest_reply", "0")) > cursor):
                    replies = paged("conversations.replies", "messages", channel=cid, ts=m["ts"])
                    rows += [r for r in replies if r["ts"] != m["ts"] and float(r["ts"]) > cursor]
        except Exception as e:  # one bad channel must not stop the rest
            failed.append(cid)
            print(f"{cid}: failed: {e}", file=sys.stderr)
            continue
        seen, uniq = set(), []
        for m in sorted(rows, key=lambda m: float(m["ts"])):
            if m["ts"] not in seen:
                seen.add(m["ts"])
                uniq.append(m)
        with (out / f"{cid}.jsonl").open("w") as f:
            for m in uniq:
                link = f"{base}/archives/{cid}/p{m['ts'].replace('.', '')}"
                if m.get("thread_ts") and m["thread_ts"] != m["ts"]:
                    link += f"?thread_ts={m['thread_ts']}&cid={cid}"
                f.write(
                    json.dumps(
                        {
                            "source": source_id,
                            "channel_id": cid,
                            "private": bool(ch.get("private")),
                            "feeds": ch.get("feeds", []),
                            "ts": m["ts"],
                            "thread_ts": m.get("thread_ts"),
                            "date": time.strftime("%Y-%m-%d %H:%M", time.gmtime(float(m["ts"]))),
                            "author_id": m.get("user") or m.get("bot_id", ""),
                            "author": users.get(
                                m.get("user", ""), m.get("username") or (m.get("bot_profile") or {}).get("name") or "?"
                            ),
                            "text": text_of(m),
                            "files": [file_of(x, call, token) for x in m.get("files", [])],
                            "link": link,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        if uniq:
            newest = max(float(m["ts"]) for m in uniq)
            cursors[cid] = f"{min(newest, started - 1):.6f}"
        print(f"{cid}: {len(uniq)} new")
    cursors_file.write_text(json.dumps(cursors, indent=2) + "\n")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
