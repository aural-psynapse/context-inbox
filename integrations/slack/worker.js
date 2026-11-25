// Cloudflare Worker: Slack sends each new message here, and the Worker starts the
// project's scheduled task (a Claude Code routine) through its API trigger.
// Messages that arrive close together start one run. worker.md says how to deploy it.
//
// The same Worker is also a small MCP server at /mcp/<MCP_PATH>, added to claude.ai as
// a connector. Its one tool, run_now, starts a run: the review page calls it when a
// person approves an item, so the item is written without waiting for a Slack message.
//
// Settings (wrangler secrets and vars):
//   SLACK_SIGNING_SECRET  from the Slack app's "Basic Information" page
//   FIRE_URL, FIRE_TOKEN  the routine's API trigger URL and token
//   CHANNELS              optional: comma-separated channel ids; others are ignored
//   WAIT_SECONDS          optional: wait this long after a message for more (default 15)
//   GAP_SECONDS           optional: at least this long between two runs (default 90)
//   MCP_PATH              optional: a long random string; without it there is no MCP server

const enc = new TextEncoder();

async function signed(req, body, secret) {
  const ts = req.headers.get("x-slack-request-timestamp") || "";
  const sig = req.headers.get("x-slack-signature") || "";
  if (!secret || !/^\d+$/.test(ts) || Math.abs(Date.now() / 1000 - Number(ts)) > 300) return false;
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(`v0:${ts}:${body}`)));
  const want = "v0=" + [...mac].map((b) => b.toString(16).padStart(2, "0")).join("");
  if (want.length !== sig.length) return false;
  let diff = 0;
  for (let i = 0; i < want.length; i++) diff |= want.charCodeAt(i) ^ sig.charCodeAt(i);
  return diff === 0;
}

function poke(env, ctx) {
  const stub = env.RUNS.get(env.RUNS.idFromName("runs"));
  ctx.waitUntil(stub.fetch("https://runs/poke", { method: "POST" }));
}

const TOOL = {
  name: "run_now",
  description: "Start a Context Inbox run now. It writes approved items and reads new messages. Returns at once.",
  inputSchema: { type: "object", properties: {} },
};

// Streamable HTTP MCP, answered as plain JSON: one request in, one response out.
async function mcp(req, env, ctx) {
  if (req.method !== "POST") return new Response(null, { status: 405, headers: { allow: "POST" } });
  let msg;
  try {
    msg = await req.json();
  } catch {
    return Response.json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "parse error" } }, { status: 400 });
  }
  if (msg.id === undefined || msg.id === null) return new Response(null, { status: 202 });
  const reply = (result) => Response.json({ jsonrpc: "2.0", id: msg.id, result });
  if (msg.method === "initialize")
    return reply({
      protocolVersion: msg.params?.protocolVersion || "2025-06-18",
      capabilities: { tools: {} },
      serverInfo: { name: "context-inbox-runs", version: "1.0.0" },
    });
  if (msg.method === "ping") return reply({});
  if (msg.method === "tools/list") return reply({ tools: [TOOL] });
  if (msg.method === "tools/call" && msg.params?.name === TOOL.name) {
    poke(env, ctx);
    return reply({ content: [{ type: "text", text: "A run starts within a minute." }] });
  }
  return Response.json({ jsonrpc: "2.0", id: msg.id, error: { code: -32601, message: "unknown method" } });
}

export default {
  async fetch(req, env, ctx) {
    if (env.MCP_PATH && new URL(req.url).pathname === `/mcp/${env.MCP_PATH}`) return mcp(req, env, ctx);
    if (req.method !== "POST") return new Response("ok");
    const body = await req.text();
    let data;
    try {
      data = JSON.parse(body);
    } catch {
      return new Response("bad request", { status: 400 });
    }
    // Echoing Slack's address check starts nothing, so it works before the signing secret is set.
    if (data.type === "url_verification") return new Response(String(data.challenge || ""), { headers: { "content-type": "text/plain" } });
    if (!(await signed(req, body, env.SLACK_SIGNING_SECRET))) return new Response("bad signature", { status: 401 });
    // Slack retries when it got no answer within 3 seconds. The first delivery already counted.
    if (req.headers.get("x-slack-retry-num")) return new Response("ok");
    const ev = data.event || {};
    const only = (env.CHANNELS || "").split(",").map((c) => c.trim()).filter(Boolean);
    if (data.type === "event_callback" && ev.type === "message" && (!only.length || only.includes(ev.channel))) poke(env, ctx);
    return new Response("ok");
  },
};

// One instance for the whole project. It keeps one alarm: the time the next run starts.
export class Runs {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async fetch() {
    if ((await this.state.storage.getAlarm()) == null) {
      const last = (await this.state.storage.get("last")) || 0;
      const wait = Number(this.env.WAIT_SECONDS || 15) * 1000;
      const gap = Number(this.env.GAP_SECONDS || 90) * 1000;
      await this.state.storage.setAlarm(Math.max(Date.now() + wait, last + gap));
    }
    return new Response("ok");
  }

  async alarm() {
    await this.state.storage.put("last", Date.now());
    const r = await fetch(this.env.FIRE_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.env.FIRE_TOKEN}`,
        "anthropic-beta": "experimental-cc-routine-2026-04-01",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: "{}",
    });
    if (!r.ok) console.log("starting the run failed", r.status, await r.text());
  }
}
