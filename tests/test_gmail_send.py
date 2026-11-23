import base64
import email
import importlib.util
import os
import tempfile
import unittest
from email import policy
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("gmail_send", os.path.join(REPO, "integrations", "gmail", "send.py"))
send = importlib.util.module_from_spec(spec)
spec.loader.exec_module(send)

SEND_AS = "sales@example.com"


def item(tmp, reply=False):
    picture = Path(tmp) / "pair1.jpg"
    picture.write_bytes(b"\xff\xd8jpeg")
    data = {
        "item_id": "item-1",
        "to": ["mary@shop.ie"],
        "subject": "quotes for designer lamp lists",
        "text": "Hi Mary",
        "html": '<p>Hi Mary</p><img src="cid:pair1@example.com">',
        "pictures": [{"path": str(picture), "content_id": "pair1@example.com"}],
    }
    if reply:
        data["reply_to"] = {"message_id": "<first@mail.gmail.com>", "thread_id": "t1"}
    return data


class FakeGmail:
    def __init__(self, existing=None):
        self.existing = existing
        self.sent = []
        self.searches = []

    def get(self, path, **params):
        if path == "messages":
            self.searches.append(params["q"])
            return {"messages": [{"id": "old"}]} if self.existing else {}
        return {"id": "old", "threadId": "t0"}

    def post(self, path, body):
        self.sent.append(body)
        return {"id": "new", "threadId": body.get("threadId", "t9")}


class GmailSendTest(unittest.TestCase):
    def test_email_carries_text_html_and_inline_picture_from_send_as(self):
        with tempfile.TemporaryDirectory() as tmp:
            msg = send.build(item(tmp), SEND_AS)
        parsed = email.message_from_bytes(msg.as_bytes(), policy=policy.default)

        self.assertEqual(parsed["From"], SEND_AS)
        self.assertEqual(parsed["Message-ID"], send.message_id("item-1", SEND_AS))
        self.assertEqual(parsed.get_body(("plain",)).get_content().strip(), "Hi Mary")
        self.assertIn("cid:pair1@example.com", parsed.get_body(("html",)).get_content())
        pictures = [p for p in parsed.walk() if p.get_content_type() == "image/jpeg"]
        self.assertEqual(len(pictures), 1)
        self.assertEqual(pictures[0]["Content-ID"], "<pair1@example.com>")

    def test_sends_once_and_threads_replies(self):
        gmail = FakeGmail()
        with tempfile.TemporaryDirectory() as tmp:
            result = send.send(item(tmp, reply=True), SEND_AS, gmail.get, gmail.post)

        self.assertFalse(result["already_sent"])
        self.assertEqual(gmail.searches, [f"rfc822msgid:{send.message_id('item-1', SEND_AS)}"])
        self.assertEqual(gmail.sent[0]["threadId"], "t1")
        raw = email.message_from_bytes(base64.urlsafe_b64decode(gmail.sent[0]["raw"]), policy=policy.default)
        self.assertEqual(raw["In-Reply-To"], "<first@mail.gmail.com>")
        self.assertEqual(result["url"], "https://mail.google.com/mail/u/0/#all/t1")

    def test_an_email_already_sent_is_not_sent_again(self):
        gmail = FakeGmail(existing=True)
        with tempfile.TemporaryDirectory() as tmp:
            result = send.send(item(tmp), SEND_AS, gmail.get, gmail.post)

        self.assertTrue(result["already_sent"])
        self.assertEqual(gmail.sent, [])


if __name__ == "__main__":
    unittest.main()


class DailyLimitTest(unittest.TestCase):
    def test_counts_emails_sent_since_midnight(self):
        queries = []

        def get(path, **params):
            queries.append(params["q"])
            if "pageToken" in params:
                return {"messages": [{"id": "c"}]}
            return {"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "next"}

        self.assertEqual(send.sent_today(get, SEND_AS, 1_700_000_000.5), 3)
        self.assertEqual(queries[0], f"in:sent from:{SEND_AS} after:1699920000")
