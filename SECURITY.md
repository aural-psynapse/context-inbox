# Security

Report a security problem through [GitHub's private vulnerability reporting](../../security/advisories/new) for this repo. Please do not open a public issue for it.

Things worth reporting:

- A way for the daily run to write to a destination without an approved item.
- A way for a message to make the agent run commands or leak data.
- A way for someone with view access to the review page to change it.

Tokens never belong in this repo or a projects repo. Keep them in environment variables or your cloud environment's secrets.
