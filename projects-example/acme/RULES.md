# Acme rules

People are named by Slack user ID.

| ID | Who |
|---|---|
| U0123456789 | founder, approves on the review page |
| U0987654321 | engineer |
| U0345678901 | sales lead |

## What counts

- Bug reports and feature requests from customers go to Linear.
- Leads, deals and customer follow-ups go to Attio.
- Unsure: write the item with `"unsure": true` and a question.
- In the private DM D0123456789, take only messages about customers and deals. Skip the rest entirely.

## Destinations

- **linear-acme**: one issue per bug or request, in project "Customer requests", assignee U0987654321.
- **attio-acme**: one deal per company. Stage follows the latest cited message. Follow-ups are tasks for U0345678901.
