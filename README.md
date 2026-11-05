# qoder-openai-adapter

A tiny **OpenAI-compatible** (`/v1/chat/completions`) HTTP server backed by the
**official [Qoder Agent SDK](https://docs.qoder.com/cli/sdk/overview)**. Point any
OpenAI-style client — your own coding/QA agent, an OpenAI SDK, Cursor, etc. — at
it and get Qoder-hosted models, **without running the Qoder IDE, terminal, or CLI
front-end**.

> **Why:** the Qoder desktop app / CLI is heavy. This adapter talks to Qoder
> through its official SDK (a ~35 MB worker runtime) with your own Personal
> Access Token, running each request with **tools disabled** and **a single
> turn** — as close to a plain completion as Qoder allows — and keeps one warm
> daemon so there's no per-request cold start.

## This is the legitimate route

- ✅ Uses the **official** `@qoder-ai/qoder-agent-sdk` and your **own** Qoder
  Personal Access Token.
- ✅ No reverse engineering, no client impersonation, no scraped endpoints.
- ❌ Not affiliated with or endorsed by Qoder.
- ⚠️ **Check [Qoder's Terms of Service](https://qoder.com) for your plan before
  use.** Programmatic access via PAT is an official feature, but you are
  responsible for staying within your plan's terms and limits.

## Free model

On a **Free** Qoder plan, exactly one model is enabled at **zero cost**:

| | value | context | output | notes |
|---|---|---|---|---|
| **Qwen3.8-Flash** | `qfmodel` | up to **1M tokens** (200K default) | 32K | reasoning + vision, `isFree: true` |

Qoder's docs confirm **failed requests cost nothing**. Note this is a *promotion*
(free since Oct 2026, extended with no fixed end date) and could change. Paid
plans enable the full lineup (DeepSeek, Kimi, GLM, Qwen-Max, and premium tiers)
but those draw plan Credits.

## Setup

Requires Node 18+ (tested on Node 24).

```bash
npm install                 # pulls the official SDK + its worker runtime
cp .env.example .env        # then edit .env and paste your pt-... token
npm start                   # http://127.0.0.1:8787
```

## Use

```bash
curl http://127.0.0.1:8787/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"qfmodel","messages":[{"role":"user","content":"reverse a string in python"}]}'
```

OpenAI client config: base URL `http://127.0.0.1:8787/v1`, any api key (or the
`SHIM_API_KEY` you set). `stream: true` is supported. `GET /v1/models` lists the
Qoder model ids.

## Benchmark harness (`eval/`)

A small grader to compare any OpenAI-compatible model on coding tasks with
**hidden test cases** (correctness, not vibes), including efficiency limits and a
bug-fix task. See [`eval/README.md`](eval/README.md).

Early finding: on simple-to-medium self-contained coding logic, free Qwen-Flash
matched Claude Haiku **and** Sonnet (perfect pass@5). It has not yet been tested
on hard, ambiguous, or long-context/repo-scale tasks — that's the next round.

## Limitations

- No tool-call passthrough; no `temperature`/`top_p`/`logprobs`.
- Token usage fields may be `0` (Qoder doesn't always report counts).
- Multi-message histories are flattened into one single-turn prompt.
- You bring your own Qoder account, token, and quota.

## License

MIT — see [LICENSE](LICENSE).
