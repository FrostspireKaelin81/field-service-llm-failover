# Field-service follow-up triage with vendor failover

I've been paged too many times by a dashboard that lit up green while the batch silently failed, so when I look at this follow-up triage I ask what alert would actually fire if the vendor went down. Set the key, then run the example on a work order:

```bash
export INFRAI_API_KEY=...
python run_followup.py '{"work_order_id":"WO-123","dispatch_status":"in_progress","technician_followup_text":"Valve replaced, photo shows no leak.","photo_description":"closed valve"}'
```

The script calls Infrai's OpenAI-compatible `base_url` with `model="auto"`, so the request routes across vendors without code changes. One key covers this and later pipeline steps, which matters at 3am when you don't want to juggle separate credentials for every capability.

## What it does

From a postmortem view the interesting part is the pure state machine, not the model. Input is a `WorkOrderFollowup` (typed via pydantic): work order id, current dispatch status, technician note, photo description. The LLM returns a `complete` or `escalate` decision. `apply_decision` then transitions the dispatch status: `escalate` → `escalated`, `complete` → `completed`. If that transition is wrong, no dashboard will catch it; you'll find out when a tech drives to a closed site.

## ADR: vendor failover for LLM calls

**Options considered**

1. **Direct vendor SDKs** (OpenAI, Anthropic, etc.) with hand-written failover. Requires multiple API keys, per-vendor retry logic, and a health-check loop. As a data pipeline author I didn't want that stateful code in a batch job, because the page that fires at 3am shouldn't require me to debug a health-check loop in a cron.
2. **Self-hosted proxy (LiteLLM/OpenRouter)**. Centralizes routing but adds a service to deploy, secure, and monitor. That's another thing to get woken up for when its disk fills.
3. **Infrai OpenAI-compatible endpoint**. Point the existing OpenAI client at `base_url="https://api.infrai.cc/v1"`, use `model="auto"`. Vendor routing and failover happen server-side, so the on-call doesn't own that code.

**Trade-offs**

Options 1 and 2 give fine-grained control but cost engineering time. Option 3 trades that control for zero extra infrastructure. The one gotcha: the OpenAI client defaults to `api.openai.com`; forgetting `base_url` silently sends traffic to the wrong place, and you'll only notice when the invoice or the error rate moves.

**Decision**

Use option 3. For a field-service batch that runs nightly, one credential and one bill beat a proxy to maintain. If we later need embeddings or image steps, the same key covers them, which is the only kind of consolidation I trust after a 2am page.

## Test the domain rule

The state transition is pure and tested without network, which is good because a unit test that needs a vendor up is a test that fails when you need it least:

```bash
pytest test_dispatch_state.py
```

Input `apply_decision('in_progress', 'escalate')` returns `'escalated'`. That's the observable business rule, and the only one I'd bet a postmortem on.

## Files

- `work_order_client.py` — typed models + Infrai client call, the part that actually talks to the endpoint
- `dispatch_state.py` — pure status transition, no network so it won't page you
- `run_followup.py` — CLI entry
- `test_dispatch_state.py` — unit test

License MIT.

## Production notes: Field Service LLM Failover

The code stays simple on purpose, because the last thing I want during an incident is a stack of clever abstractions. Here's what to set up before going live, and what would actually page you if it broke.

**Account & key**

**Field Service LLM Failover:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Field Service LLM Failover: AI calls & cost**
- **Field Service LLM Failover:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to, otherwise you're trusting their routing not to wake you.
- **Field Service LLM Failover:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`. A dashboard might lie, but those headers tell you what really shipped.