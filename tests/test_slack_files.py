import importlib.util
import io
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("reader", os.path.join(REPO, "integrations", "slack", "reader.py"))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def docx(*paras):
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paras)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body>{body}</w:body></w:document>")
    return buf.getvalue()


def no_call(*a, **k):
    raise AssertionError("no API call expected")


class SlackFilesTest(unittest.TestCase):
    def read(self, f, data=b""):
        with mock.patch.object(reader, "fetch", return_value=data):
            return reader.file_of(f, no_call, "t")

    def test_plain_text(self):
        out = self.read(
            {"name": "n.md", "title": "Notes", "filetype": "markdown", "url_private": "u", "permalink": "p"},
            b"# Hi\nthere",
        )
        self.assertEqual(out, {"name": "Notes", "type": "markdown", "link": "p", "text": "# Hi\nthere"})

    def test_docx(self):
        out = self.read(
            {"name": "c.docx", "filetype": "docx", "url_private": "u"}, docx("Scope: two pages", "Price &amp; terms")
        )
        self.assertEqual(out["text"], "Scope: two pages\nPrice & terms")

    def test_canvas_html(self):
        out = self.read(
            {"name": "c", "filetype": "quip", "url_private": "u"},
            b"<h1>Plan</h1><p>Ship <b>Monday</b></p><script>x</script>",
        )
        self.assertEqual(out["text"], "Plan\nShip Monday")

    @unittest.skipUnless(shutil.which("pdftotext") and shutil.which("cupsfilter"), "needs pdftotext and cupsfilter")
    def test_pdf(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt") as t:
            t.write("Invoice total 4200 EUR")
            t.flush()
            pdf = subprocess.run(["cupsfilter", t.name], capture_output=True).stdout
        out = self.read({"name": "i.pdf", "filetype": "pdf", "url_private": "u"}, pdf)
        self.assertIn("Invoice total 4200 EUR", out["text"])

    def test_image_skipped(self):
        out = self.read({"name": "a.png", "filetype": "png", "mimetype": "image/png", "url_private": "u"})
        self.assertEqual((out["text"], out["note"]), ("", "not a text file"))

    def test_external_google_doc(self):
        out = self.read({"name": "Doc", "filetype": "gdoc", "is_external": True, "external_type": "gdrive"})
        self.assertIn("external file (gdrive)", out["note"])

    def test_long_text_cut(self):
        out = self.read({"name": "l.txt", "filetype": "text", "url_private": "u"}, b"a" * (reader.MAX_FILE_CHARS + 5))
        self.assertEqual(len(out["text"]), reader.MAX_FILE_CHARS)
        self.assertIn("cut to the first", out["note"])

    def test_download_error_keeps_message(self):
        with mock.patch.object(reader, "fetch", side_effect=OSError("403")):
            out = reader.file_of({"name": "x.txt", "filetype": "text", "url_private": "u"}, no_call, "t")
        self.assertEqual(out["text"], "")
        self.assertIn("could not read: 403", out["note"])

    def test_check_file_info(self):
        full = {"name": "real.txt", "filetype": "text", "url_private": "u"}
        with mock.patch.object(reader, "fetch", return_value=b"hello"):
            out = reader.file_of({"id": "F1", "file_access": "check_file_info"}, lambda m, **p: {"file": full}, "t")
        self.assertEqual(out["text"], "hello")


if __name__ == "__main__":
    unittest.main()
