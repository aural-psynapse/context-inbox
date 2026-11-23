"""Read new emails from a Gmail mailbox for one source in a project config.

Usage:
  python3 integrations/gmail/reader.py CONFIG SOURCE_ID CURSORS OUT_DIR [--only CHANNEL_ID]

CONFIG     path to the project's config.json
SOURCE_ID  the "id" of a source in that config
CURSORS    JSON file {channel_id: newest_internal_date_ms}. A missing file, an empty
           file or {} means read every matching email from the start. Rewritten at the end.
OUT_DIR    folder for <channel_id>.jsonl, one message per line, oldest first
--only     read just this channel

Channels: each channel has a short "id" for its file name and a Gmail search in
"query", such as "to:sales@example.com" or "label:clients". The search runs over
the whole mailbox, sent mail and archived mail included.

Token: the env var named by the source's "secret" holds either a Gmail access
token, or JSON {"client_id", "client_secret", "refresh_token"} from a Google OAuth
client with the gmail.readonly scope. The reader turns the JSON into an access
token on each run. When the env var is unset (cloud runs), requests go out
without a token and the network proxy adds it.

Each email is one message. Emails in one Gmail thread share its "thread_ts".
"text" holds the subject line, then the plain text body, cut to 20,000 characters.
Attachments come back in "files" with their text: plain text, CSV, Word (.docx),
Excel (.xlsx) and PDF (needs pdftotext on PATH). An attachment it cannot read,
such as an image, gets an empty "text" and a "note" saying why.

Cursor: Gmail's internal date of the newest email read, never later than the
moment this run started, so an email that arrives while the run is reading
comes back next time.

A channel that fails keeps its old cursor and gets no output file. The other
channels still run. The script then exits 1.
"""

import base64
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
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path

API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"
TIMEOUT = 30
MAX_RETRIES = 8
MAX_CHARS = 20_000
MAX_FILE_BYTES = 20_000_000
TEXT_TYPES = ("text/plain", "text/csv", "text/markdown", "application/json")


def access_token(secret: str) -> str:
    """The secret itself, or a fresh access token made from OAuth client JSON."""
    secret = secret.strip()
    if not secret.startswith("{"):
        return secret
    info = json.loads(secret)
    body = urllib.parse.urlencode(
        {
            "client_id": info["client_id"],
            "client_secret": info["client_secret"],
            "refresh_token": info["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body), timeout=TIMEOUT) as r:
        return json.load(r)["access_token"]


def make_get(token: str):
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    def get(path: str, **params: str) -> dict:
        url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, headers=headers)
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 503) and attempt < MAX_RETRIES - 1:
                    time.sleep(min(2**attempt, 30))
                    continue
                raise
        raise RuntimeError(f"{path}: rate limited {MAX_RETRIES} times")

    return get


def decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def strip_tags(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|li|tr)>", "\n", markup)
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def xlsx_text(data: bytes) -> str:
    """Every cell's text, row by row, from each sheet. Shared strings are filled in."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            xml = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
            for si in re.findall(r"(?s)<si>(.*?)</si>", xml):
                shared.append(html.unescape("".join(re.findall(r"(?s)<t[^>]*>(.*?)</t>", si))))
        lines = []
        for name in sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n)):
            xml = z.read(name).decode("utf-8", "replace")
            for row in re.findall(r"(?s)<row[^>]*>(.*?)</row>", xml):
                cells = []
                for attrs, inner in re.findall(r"(?s)<c([^>]*)>(.*?)</c>", row):
                    value = re.search(r"(?s)<v>(.*?)</v>", inner)
                    inline = re.search(r"(?s)<t[^>]*>(.*?)</t>", inner)
                    if 't="s"' in attrs and value:
                        cells.append(shared[int(value.group(1))])
                    elif value:
                        cells.append(html.unescape(value.group(1)))
                    elif inline:
                        cells.append(html.unescape(inline.group(1)))
                lines.append("\t".join(cells))
    return "\n".join(lines)


def pdf_text(data: bytes) -> str:
    if not shutil.which("pdftotext"):
        raise RuntimeError("PDF needs pdftotext on PATH")
    r = subprocess.run(["pdftotext", "-q", "-", "-"], input=data, capture_output=True, timeout=TIMEOUT, check=True)
    return r.stdout.decode("utf-8", "replace")


def file_text(name: str, mime: str, data: bytes) -> str:
    lower = name.lower()
    if mime.startswith(TEXT_TYPES) or lower.endswith((".txt", ".csv", ".md", ".json")):
        return data.decode("utf-8", "replace")
    if lower.endswith(".docx"):
        return docx_text(data)
    if lower.endswith(".xlsx"):
        return xlsx_text(data)
    if lower.endswith(".pdf") or mime == "application/pdf":
        return pdf_text(data)
    raise RuntimeError(f"no reader for {mime or name}")


def walk(part: dict):
    yield part
    for child in part.get("parts", []) or []:
        yield from walk(child)


def header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def body_text(msg: dict) -> str:
    plain, markup = "", ""
    for part in walk(msg.get("payload", {})):
        if part.get("filename"):
            continue
        data = (part.get("body") or {}).get("data")
        if not data:
            continue
        if part.get("mimeType") == "text/plain" and not plain:
            plain = decode(data).decode("utf-8", "replace")
        elif part.get("mimeType") == "text/html" and not markup:
            markup = strip_tags(decode(data).decode("utf-8", "replace"))
    return (plain or markup).strip()


def files_of(msg: dict, get) -> list:
    out = []
    for part in walk(msg.get("payload", {})):
        name = part.get("filename")
        if not name:
            continue
        body = part.get("body") or {}
        item = {
            "id": body.get("attachmentId", ""),
            "name": name,
            "type": part.get("mimeType", ""),
            "link": f"https://mail.google.com/mail/u/0/#all/{msg['threadId']}",
            "text": "",
        }
        try:
            if int(body.get("size", 0)) > MAX_FILE_BYTES:
                raise RuntimeError("file is larger than 20 MB")
            if body.get("data"):
                data = decode(body["data"])
            else:
                data = decode(get(f"messages/{msg['id']}/attachments/{body['attachmentId']}")["data"])
            item["text"] = file_text(name, item["type"], data)[:MAX_CHARS]
        except Exception as e:  # noqa: BLE001 - one unreadable file must not drop the email
            item["note"] = f"not read: {e}"
        out.append(item)
    return out


def message(src: dict, ch: dict, msg: dict, get) -> dict:
    name, address = parseaddr(header(msg, "From"))
    millis = int(msg["internalDate"])
    subject = header(msg, "Subject")
    text = f"Subject: {subject}\n\n{body_text(msg)}" if subject else body_text(msg)
    return {
        "source": src["id"],
        "channel_id": ch["id"],
        "private": bool(ch.get("private")),
        "feeds": ch.get("feeds", []),
        "ts": msg["id"],
        "thread_ts": msg["threadId"],
        "date": datetime.fromtimestamp(millis / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "author_id": address,
        "author": name or address,
        "text": text[:MAX_CHARS],
        "files": files_of(msg, get),
        "link": f"https://mail.google.com/mail/u/0/#all/{msg['threadId']}",
    }


def emails_since(get, query: str, after_ms: int) -> list:
    q = query
    if after_ms:
        q += f" after:{after_ms // 1000}"
    ids, token = [], ""
    while True:
        params = {"q": q, "maxResults": "500", "includeSpamTrash": "false"}
        if token:
            params["pageToken"] = token
        data = get("messages", **params)
        ids += [m["id"] for m in data.get("messages", [])]
        token = data.get("nextPageToken", "")
        if not token:
            break
    emails = [get(f"messages/{i}", format="full") for i in ids]
    emails = [m for m in emails if int(m["internalDate"]) > after_ms]
    return sorted(emails, key=lambda m: int(m["internalDate"]))


def read(src: dict, cursors: dict, out_dir: Path, get, started: float, only=None) -> bool:
    ok = True
    for ch in src.get("channels", []):
        cid = ch["id"]
        if only and cid != only:
            continue
        try:
            emails = emails_since(get, ch.get("query", ""), int(cursors.get(cid, "0")))
            rows = [message(src, ch, m, get) for m in emails]
        except Exception as e:  # noqa: BLE001 - one failed channel must not stop the others
            print(f"{cid}: failed: {e}", file=sys.stderr)
            ok = False
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / f"{cid}.jsonl", "w") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if emails:
            newest = int(emails[-1]["internalDate"])
            cursors[cid] = str(min(newest, int(started * 1000) - 1))
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
    secret = os.environ.get(src.get("secret", ""), "")
    get = make_get(access_token(secret) if secret else "")
    cursors_file = Path(cursors_path)
    raw = cursors_file.read_text().strip() if cursors_file.exists() else ""
    cursors = json.loads(raw) if raw else {}
    ok = read(src, cursors, Path(out_dir), get, started, only)
    cursors_file.write_text(json.dumps(cursors, indent=2) + "\n")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
