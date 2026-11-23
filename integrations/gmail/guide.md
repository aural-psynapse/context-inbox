# Gmail

Send with `integrations/gmail/send.py`, never with a mail connector: connectors send from the account's own address, and this destination sends from `send_as`.

```bash
python3 integrations/gmail/send.py CONFIG <destination id> <email json>
```

- Config: `{ "id": "gmail-acme", "type": "gmail", "guide": "gmail", "send_as": "sales@acme.com", "secret": "GMAIL_ACME_SEND" }`. The secret holds an OAuth client JSON with the `gmail.send` and `gmail.readonly` scopes for the Gmail account that has `send_as` under "Send mail as".
- `send_email`: one email. Write the email JSON the script's docstring describes from the item: `to`, `subject`, `text`, `html`, `pictures`, and `reply_to` when the item answers an earlier email. Use `decision.body` when present, else `body`, word for word.
- The marker: the script turns the item id into the email's Message-ID and searches for it before sending, so a second push never sends twice. Recipients never see the marker.
- `pushed.url` is the `url` the script prints, the Gmail thread.

## A complete record

An email holds: recipients, subject, a plain text version, an HTML version when the item has one, its pictures inside the email, and the earlier email it answers when it is a reply. Every email to an outside address carries the sender's opt-out line when the project's `RULES.md` asks for one.

Docs: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send

Docs checked: 2026-11-23
