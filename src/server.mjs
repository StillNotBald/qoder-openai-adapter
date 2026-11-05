// Minimal OpenAI-compatible shim over the official Qoder Agent SDK.
//
// Exposes:
//   GET  /v1/models
//   POST /v1/chat/completions   (stream: true|false)
//
// Each request runs the SDK with tools disabled and a single turn, so it is as
// close to a plain completion as Qoder allows. One shared qodercli daemon is
// reused across requests (warm), so there is no per-call cold start.
//
// Auth to Qoder: set QODER_PERSONAL_ACCESS_TOKEN (a `pt-...` token from the
// Qoder console -> Settings -> API Tokens). This process never logs it.
//
// Optional: SHIM_API_KEY protects this server. If set, callers must send
//   Authorization: Bearer <SHIM_API_KEY>
//
// Env: PORT (default 8787), QODER_MODEL (default "auto").

import http from 'node:http';
import { randomUUID } from 'node:crypto';
import { query, accessTokenFromEnv, shutdownDaemon } from '@qoder-ai/qoder-agent-sdk';

const PORT = Number(process.env.PORT || 8787);
const DEFAULT_MODEL = process.env.QODER_MODEL || 'qfmodel';
const SHIM_API_KEY = process.env.SHIM_API_KEY || '';
// Real Qoder internal model ids. Which are usable depends on your plan/credits;
// on a Free account typically only `qfmodel` (Qwen-Flash, free) is enabled.
const MODEL_IDS = [
  'qfmodel', 'auto', 'ultimate', 'fast', 'efficient',
  'smodel', 'cmodel', 'qmodel_38max',
  'kmodel', 'kmodel_latest', 'gmodel', 'gfmodel',
  'dmodel', 'dfmodel', 'mmodel',
];

if (!process.env.QODER_PERSONAL_ACCESS_TOKEN) {
  console.warn(
    '[warn] QODER_PERSONAL_ACCESS_TOKEN is not set. Requests will fail at the Qoder auth step until you set it.',
  );
}

// ---- helpers ---------------------------------------------------------------

function send(res, status, obj, headers = {}) {
  const body = JSON.stringify(obj);
  res.writeHead(status, { 'content-type': 'application/json', ...headers });
  res.end(body);
}

function oaiError(res, status, message, type = 'invalid_request_error') {
  send(res, status, { error: { message, type } });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > 8 * 1024 * 1024) reject(new Error('request body too large'));
      else chunks.push(c);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

function authorized(req) {
  if (!SHIM_API_KEY) return true;
  const h = req.headers['authorization'] || '';
  return h === `Bearer ${SHIM_API_KEY}`;
}

// Turn OpenAI chat `messages` into (systemPrompt, prompt) for a single turn.
function toSinglePrompt(messages) {
  const systemParts = [];
  const convo = [];
  for (const m of messages || []) {
    const text = normalizeContent(m.content);
    if (m.role === 'system') systemParts.push(text);
    else if (m.role === 'user') convo.push(`User: ${text}`);
    else if (m.role === 'assistant') convo.push(`Assistant: ${text}`);
    else if (m.role === 'tool') convo.push(`Tool result: ${text}`);
  }
  const systemPrompt = systemParts.join('\n\n').trim();
  // If there is only one user message, send it raw (cleanest single-turn case).
  const onlyUser = (messages || []).filter((m) => m.role !== 'system');
  const prompt =
    onlyUser.length === 1 && onlyUser[0].role === 'user'
      ? normalizeContent(onlyUser[0].content)
      : convo.join('\n\n');
  return { systemPrompt, prompt };
}

function normalizeContent(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map((p) => (typeof p === 'string' ? p : p?.text ?? ''))
      .filter(Boolean)
      .join('\n');
  }
  return '';
}

function textFromAssistant(msg) {
  const blocks = msg?.message?.content;
  if (!Array.isArray(blocks)) return '';
  return blocks.map((b) => (b?.type === 'text' ? b.text : '')).join('');
}

function mapUsage(u) {
  const prompt = u?.input_tokens ?? 0;
  const completion = u?.output_tokens ?? 0;
  return {
    prompt_tokens: prompt,
    completion_tokens: completion,
    total_tokens: prompt + completion,
  };
}

function buildQuery(model, systemPrompt, prompt) {
  const options = {
    auth: accessTokenFromEnv(), // reads QODER_PERSONAL_ACCESS_TOKEN
    model: model || DEFAULT_MODEL,
    tools: [], // no bash / file-editor / MCP: minimal agent overhead
    maxTurns: 1, // single turn -> closest to plain completion
  };
  if (systemPrompt) options.systemPrompt = systemPrompt;
  return query({ prompt, options });
}

// ---- handlers --------------------------------------------------------------

function handleModels(res) {
  const now = Math.floor(Date.now() / 1000);
  send(res, 200, {
    object: 'list',
    data: MODEL_IDS.map((id) => ({
      id,
      object: 'model',
      created: now,
      owned_by: 'qoder',
    })),
  });
}

async function handleChat(req, res, body) {
  let payload;
  try {
    payload = JSON.parse(body);
  } catch {
    return oaiError(res, 400, 'Request body is not valid JSON.');
  }
  if (!Array.isArray(payload.messages) || payload.messages.length === 0) {
    return oaiError(res, 400, '`messages` must be a non-empty array.');
  }

  // Pass whatever model the client asks for straight through to Qoder; only
  // fall back to the default when none is given.
  const model = (payload.model && String(payload.model).trim()) || DEFAULT_MODEL;
  const { systemPrompt, prompt } = toSinglePrompt(payload.messages);
  if (!prompt.trim()) return oaiError(res, 400, 'No user content found in `messages`.');

  const id = `chatcmpl-${randomUUID()}`;
  const created = Math.floor(Date.now() / 1000);

  if (payload.stream) return streamChat(res, { id, created, model, systemPrompt, prompt });

  // --- non-streaming ---
  let full = '';
  let usage = null;
  let errored = null;
  try {
    for await (const msg of buildQuery(model, systemPrompt, prompt)) {
      if (msg.type === 'assistant') full += textFromAssistant(msg);
      else if (msg.type === 'result') {
        if (msg.subtype === 'success' && typeof msg.result === 'string' && msg.result) full = msg.result;
        if (msg.usage) usage = msg.usage;
        if (msg.is_error) errored = msg.subtype || 'error_during_execution';
        break;
      }
    }
  } catch (e) {
    return oaiError(res, 502, `Qoder SDK error: ${e?.message || e}`, 'api_error');
  }
  if (errored) return oaiError(res, 502, `Qoder run failed: ${errored}`, 'api_error');

  send(res, 200, {
    id,
    object: 'chat.completion',
    created,
    model,
    choices: [
      {
        index: 0,
        message: { role: 'assistant', content: full },
        finish_reason: 'stop',
      },
    ],
    usage: mapUsage(usage),
  });
}

async function streamChat(res, { id, created, model, systemPrompt, prompt }) {
  res.writeHead(200, {
    'content-type': 'text/event-stream',
    'cache-control': 'no-cache',
    connection: 'keep-alive',
  });
  const chunk = (delta, finish = null) => {
    res.write(
      `data: ${JSON.stringify({
        id,
        object: 'chat.completion.chunk',
        created,
        model,
        choices: [{ index: 0, delta, finish_reason: finish }],
      })}\n\n`,
    );
  };
  chunk({ role: 'assistant' });
  let sent = '';
  try {
    for await (const msg of buildQuery(model, systemPrompt, prompt)) {
      if (msg.type === 'assistant') {
        const t = textFromAssistant(msg);
        if (t && t.startsWith(sent)) {
          const delta = t.slice(sent.length);
          if (delta) chunk({ content: delta });
          sent = t;
        } else if (t) {
          chunk({ content: t });
          sent += t;
        }
      } else if (msg.type === 'result') {
        if (msg.subtype === 'success' && typeof msg.result === 'string' && msg.result.length > sent.length) {
          chunk({ content: msg.result.slice(sent.length) });
        }
        break;
      }
    }
    chunk({}, 'stop');
    res.write('data: [DONE]\n\n');
  } catch (e) {
    chunk({ content: `\n[error: ${e?.message || e}]` }, 'stop');
    res.write('data: [DONE]\n\n');
  }
  res.end();
}

// ---- server ----------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  if (req.method === 'GET' && url.pathname === '/healthz') return send(res, 200, { ok: true });
  if (!authorized(req)) return oaiError(res, 401, 'Missing or invalid API key.', 'authentication_error');
  if (req.method === 'GET' && url.pathname === '/v1/models') return handleModels(res);
  if (req.method === 'POST' && url.pathname === '/v1/chat/completions') {
    try {
      const body = await readBody(req);
      return await handleChat(req, res, body);
    } catch (e) {
      return oaiError(res, 400, e?.message || 'bad request');
    }
  }
  return oaiError(res, 404, `No route for ${req.method} ${url.pathname}`);
});

server.listen(PORT, () => {
  console.log(`qoder-oai-shim listening on http://127.0.0.1:${PORT}`);
  console.log(`  default model: ${DEFAULT_MODEL}  |  shim auth: ${SHIM_API_KEY ? 'on' : 'off'}`);
});

async function stop(sig) {
  console.log(`\n${sig} -> shutting down daemon...`);
  try { await shutdownDaemon(); } catch {}
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 3000).unref();
}
process.on('SIGINT', () => stop('SIGINT'));
process.on('SIGTERM', () => stop('SIGTERM'));
