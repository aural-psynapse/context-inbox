import base64
import importlib.util
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("gmail", os.path.join(REPO, "integrations", "gmail", "reader.py"))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

SRC = {"id": "mail", "channels": [{"id": "sales", "query": "to:sales@example.com", "feeds": ["crm"]}]}


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def xlsx(rows):
    buf = io.BytesIO()
    strings = [c for r in rows for c in r]
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", "<sst>" + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
        body, n = "", 0
        for r in rows:
            cells = ""
            for _ in r:
                cells += f'<c t="s"><v>{n}</v></c>'
                n += 1
            body += f"<row>{cells}</row>"
        z.writestr("xl/worksheets/sheet1.xml", f"<worksheet><sheetData>{body}</sheetData></worksheet>")
    return buf.getvalue()


def email(mid, millis, subject="Price request", attachments=()):
    parts = [{"mimeType": "text/plain", "body": {"data": b64(b"Hi, please price the list.")}}]
    for i, (name, mime, data) in enumerate(attachments):
        parts.append({"filename": name, "mimeType": mime, "body": {"attachmentId": f"a{i}", "size": len(data)}})
    return {
        "id": mid,
        "threadId": f"t-{mid}",
        "internalDate": str(millis),
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [{"name": "From", "value": "Mary Byrne <mary@design.ie>"}, {"name": "Subject", "value": subject}],
            "parts": parts,
        },
    }


class FakeGmail:
    def __init__(self, emails, attachments=None):
        self.emails = {m["id"]: m for m in emails}
        self.attachments = attachments or {}
        self.queries = []

    def __call__(self, path, **params):
        if path == "messages":
            self.queries.append(params["q"])
            return {"messages": [{"id": i} for i in self.emails]}
        if "/attachments/" in path:
            return {"data": b64(self.attachments[path.rsplit("/", 1)[1]])}
        return self.emails[path.split("/")[1]]


class GmailReaderTest(unittest.TestCase):
    def run_reader(self, api, cursors, started=2_000_000_000):
        with tempfile.TemporaryDirectory() as d:
            ok = reader.read(SRC, cursors, Path(d), api, started)
            out = {p.stem: [json.loads(x) for x in p.read_text().splitlines()] for p in Path(d).glob("*.jsonl")}
        return ok, out

    def test_reads_emails_oldest_first_with_attachment_text(self):
        sheet = xlsx([["Lamp", "Qty"], ["Brass task lamp", "2"]])
        api = FakeGmail(
            [email("m2", 1_700_000_200_000), email("m1", 1_700_000_100_000, attachments=[
                ("list.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", sheet),
                ("photo.jpg", "image/jpeg", b"jpg")])],
            {"a0": sheet, "a1": b"jpg"},
        )
        cursors = {}

        ok, out = self.run_reader(api, cursors)

        self.assertTrue(ok)
        self.assertEqual(api.queries, ["to:sales@example.com"])
        first, second = out["sales"]
        self.assertEqual((first["ts"], second["ts"]), ("m1", "m2"))
        self.assertEqual(first["thread_ts"], "t-m1")
        self.assertEqual((first["author"], first["author_id"]), ("Mary Byrne", "mary@design.ie"))
        self.assertEqual(first["text"], "Subject: Price request\n\nHi, please price the list.")
        self.assertEqual(first["files"][0]["text"], "Lamp\tQty\nBrass task lamp\t2")
        self.assertIn("not read", first["files"][1]["note"])
        self.assertEqual(cursors["sales"], "1700000200000")

    def test_later_run_asks_only_for_newer_emails(self):
        api = FakeGmail([email("m1", 1_700_000_100_000), email("m2", 1_700_000_300_000)])

        _, out = self.run_reader(api, {"sales": "1700000200000"})

        self.assertEqual(api.queries, ["to:sales@example.com after:1700000200"])
        self.assertEqual([m["ts"] for m in out["sales"]], ["m2"])

    def test_failed_channel_keeps_its_cursor(self):
        def broken(path, **params):
            raise RuntimeError("401")

        cursors = {"sales": "5"}
        ok, out = self.run_reader(broken, cursors)

        self.assertFalse(ok)
        self.assertEqual(out, {})
        self.assertEqual(cursors["sales"], "5")

    def test_plain_token_is_used_as_is(self):
        self.assertEqual(reader.access_token(" ya29.token "), "ya29.token")


if __name__ == "__main__":
    unittest.main()
