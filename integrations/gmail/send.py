"""Send one approved email through the Gmail API, at most once.

Usage:
  python3 integrations/gmail/send.py CONFIG DESTINATION_ID EMAIL_JSON

EMAIL_JSON is a file:
  {
    "item_id": "the Context Inbox item id",
    "to": ["mary@shop.ie"],
    "subject": "quotes for designer lamp lists",
    "text": "plain text version",
    "html": "<p>HTML version, pictures as <img src=\\"cid:pair1@x\\"></p>",
    "pictures": [{"path": "/abs/pair1.jpg", "content_id": "pair1@x"}],
    "reply_to": {"message_id": "<abc@mail.gmail.com>", "thread_id": "18c..."}   (optional)
  }

The sender is the destination's "send_as" address, which must be set up under
"Send mail as" in the Gmail account the token belongs to. The email carries both
the plain text and the HTML version; the reader's mail app picks one. Pictures
travel inside the email.

At most once: the email's Message-ID comes from the item id. Before sending, the
script searches the mailbox for that Message-ID and, when it finds it, prints the
earlier email instead of sending again.

Token: the env var named by the destination's "secret" holds JSON
{"client_id", "client_secret", "refresh_token"} from a Google OAuth client with the
gmail.send and gmail.readonly scopes, or an access token.

Prints {"id", "thread_id", "url", "already_sent"} as JSON.
"""

import base64
import hashlib
import importlib.util
import json
import mimetypes
import os
import sys
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("gmail_reader", HERE / "reader.py")
reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reader)


def message_id(item_id: str, send_as: str) -> str:
    digest = hashlib.sha256(item_id.encode()).hexdigest()[:24]
    return f"<ctx-{digest}@{send_as.split('@')[-1]}>"


def build(email: dict, send_as: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = send_as
    msg["To"] = ", ".join(email["to"])
    msg["Subject"] = email["subject"]
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = message_id(email["item_id"], send_as)
    reply = email.get("reply_to") or {}
    if reply.get("message_id"):
        msg["In-Reply-To"] = reply["message_id"]
        msg["References"] = reply["message_id"]
    msg.set_content(email["text"])
    if email.get("html"):
        msg.add_alternative(email["html"], subtype="html")
        html_part = msg.get_payload()[-1]
        for picture in email.get("pictures", []):
            path = Path(picture["path"])
            kind = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            maintype, subtype = kind.split("/", 1)
            html_part.add_related(
                path.read_bytes(), maintype=maintype, subtype=subtype,
                cid=f"<{picture['content_id']}>", filename=path.name, disposition="inline",
            )
    return msg


def make_post(token: str):
    def post(path: str, body: dict) -> dict:
        req = urllib.request.Request(
            f"{reader.API}/{path}", data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=reader.TIMEOUT) as r:
            return json.load(r)

    return post


def send(email: dict, send_as: str, get, post) -> dict:
    mid = message_id(email["item_id"], send_as)
    found = get("messages", q=f"rfc822msgid:{mid}", includeSpamTrash="true").get("messages", [])
    if found:
        earlier = get(f"messages/{found[0]['id']}", format="minimal")
        thread = earlier["threadId"]
        return {"id": earlier["id"], "thread_id": thread, "url": f"https://mail.google.com/mail/u/0/#all/{thread}", "already_sent": True}
    raw = base64.urlsafe_b64encode(build(email, send_as).as_bytes()).decode()
    body = {"raw": raw}
    thread_id = (email.get("reply_to") or {}).get("thread_id")
    if thread_id:
        body["threadId"] = thread_id
    sent = post("messages/send", body)
    thread = sent["threadId"]
    return {"id": sent["id"], "thread_id": thread, "url": f"https://mail.google.com/mail/u/0/#all/{thread}", "already_sent": False}


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    config, dest_id, email_path = sys.argv[1:]
    cfg = json.loads(Path(config).read_text())
    dest = next((d for d in cfg.get("destinations", []) if d.get("id") == dest_id), None)
    if not dest:
        sys.exit(f"no destination with id {dest_id!r} in {config}")
    if not dest.get("send_as"):
        sys.exit(f"destination {dest_id!r} needs a send_as address")
    token = reader.access_token(os.environ.get(dest.get("secret", ""), ""))
    email = json.loads(Path(email_path).read_text())
    result = send(email, dest["send_as"], reader.make_get(token), make_post(token))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
