"""Linear read tools and writer for the Context Inbox MCP server.

The server holds the key: a Linear API key in the env var the destination's
`secret` names. The agent session never gets it. LINEAR_API_URL overrides the
GraphQL address, for tests.

Writes, one per approved item, each carrying `ctx: <item id>` on its last line:
- create_issue: a new issue in the destination's `team` (a team key, such as ACM)
- comment_issue: a comment on the issue in `existing.id`
- update_issue: a new title and description on the issue in `existing.id`

Before each write it searches for the marker, so a write that already went
through is not made twice.
"""

import json
import os
import urllib.request

READ_TOOLS = [
    {
        "name": "search_issues",
        "description": "Issues whose title or description holds the words given, newest first, up to 20.",
        "inputSchema": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
    },
    {
        "name": "get_issue",
        "description": "One issue by id or key such as ACM-12, with its state and its last 20 comments.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}},
    },
]

ISSUE = "id identifier title url state { name } assignee { name } updatedAt"


def gql(dest: dict, query: str, variables: dict) -> dict:
    name = dest.get("secret")
    key = os.environ.get(name or "")
    if not key:
        raise RuntimeError(f"No Linear key: set the env var {name!r} in the MCP server's environment.")
    req = urllib.request.Request(
        os.environ.get("LINEAR_API_URL", "https://api.linear.app/graphql"),
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Content-Type": "application/json", "Authorization": key},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read())
    if body.get("errors"):
        raise RuntimeError("Linear: " + "; ".join(e.get("message", "?") for e in body["errors"]))
    return body["data"]


def read(tool: str, args: dict, dest: dict):
    if tool == "search_issues":
        q = f"query($t: String!) {{ searchIssues(term: $t, first: 20) {{ nodes {{ {ISSUE} }} }} }}"
        return gql(dest, q, {"t": str(args.get("query", ""))})["searchIssues"]["nodes"]
    if tool == "get_issue":
        comments = "comments(first: 20) { nodes { body createdAt user { name } } }"
        q = f"query($id: String!) {{ issue(id: $id) {{ {ISSUE} description {comments} }} }}"
        return gql(dest, q, {"id": str(args.get("id", ""))})["issue"]
    raise ValueError(f"no read tool {tool}")


def _marked(item: dict) -> str:
    body = (item.get("decision") or {}).get("body") or item.get("body") or ""
    return f"{body.rstrip()}\n\nctx: {item['id']}"


def _existing(item: dict) -> str:
    ex = (item.get("existing") or {}).get("id")
    if not ex:
        raise ValueError(f"{item['action']} needs existing.id, the issue to change")
    return ex


def write(item: dict, dest: dict) -> str:
    """Write one approved item and return the record's URL."""
    marker = f"ctx: {item['id']}"
    action = item.get("action")
    if action == "create_issue":
        q = "query($t: String!) { searchIssues(term: $t, first: 5) { nodes { url description } } }"
        for hit in gql(dest, q, {"t": marker})["searchIssues"]["nodes"]:
            if marker in (hit.get("description") or ""):
                return hit["url"]
        team = dest.get("team")
        q = "query($k: String!) { teams(filter: { key: { eq: $k } }) { nodes { id } } }"
        nodes = gql(dest, q, {"k": team})["teams"]["nodes"]
        if not nodes:
            raise ValueError(f"Linear has no team with key {team!r}")
        q = "mutation($i: IssueCreateInput!) { issueCreate(input: $i) { success issue { url } } }"
        i = {"teamId": nodes[0]["id"], "title": item.get("title", ""), "description": _marked(item)}
        return gql(dest, q, {"i": i})["issueCreate"]["issue"]["url"]
    if action == "comment_issue":
        issue_id = _existing(item)
        q = "query($id: String!) { issue(id: $id) { url comments(first: 100) { nodes { body url } } } }"
        issue = gql(dest, q, {"id": issue_id})["issue"]
        for c in issue["comments"]["nodes"]:
            if marker in (c.get("body") or ""):
                return c.get("url") or issue["url"]
        q = "mutation($i: CommentCreateInput!) { commentCreate(input: $i) { success comment { url } } }"
        return gql(dest, q, {"i": {"issueId": issue_id, "body": _marked(item)}})["commentCreate"]["comment"]["url"]
    if action == "update_issue":
        q = (
            "mutation($id: String!, $i: IssueUpdateInput!) "
            "{ issueUpdate(id: $id, input: $i) { success issue { url } } }"
        )
        i = {"title": item.get("title", ""), "description": _marked(item)}
        return gql(dest, q, {"id": _existing(item), "i": i})["issueUpdate"]["issue"]["url"]
    raise ValueError(f"Linear writer has no action {action!r}. It writes create_issue, comment_issue, update_issue.")
