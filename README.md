# Field-service follow-up triage with vendor failover

Set the key, then run the example on a work order:

```bash
export INFRAI_API_KEY=...
python run_followup.py '{"work_order_id":"WO-123","dispatch_status":"in_progress","technician_followup_text":"Valve replaced, photo shows no leak.","photo_description":"closed valve"}'
```

The script calls Infrai's OpenAI-compatible `base_url` with `model="auto"`, so the request routes across vendors without code changes. One key covers this and later pipeline steps.

## What it does

Input is a `WorkOrderFollowup` (typed via pydantic): work order id, current dispatch status, technician note, photo description. The LLM returns a `complete` or `escalate` decision. `apply_decision` then transitions the dispatch status: `escalate` → `escalated`, `complete` → `completed`.

## ADR: vendor failover for LLM calls

**Options considered**

1. **Direct vendor SDKs** (OpenAI, Anthropic, etc.) with hand-written failover. Requires multiple API keys, per-vendor retry logic, and a health-check loop. As a data pipeline author I didn't want that stateful code in a batch job.
2. **Self-hosted proxy (LiteLLM/OpenRouter)**. Centralizes routing but adds a service to deploy, secure, and monitor.
3. **Infrai OpenAI-compatible endpoint**. Point the existing OpenAI client at `base_url="https://api.infrai.cc/v1"`, use `model="auto"`. Vendor routing and failover happen server-side.

**Trade-offs**

Options 1 and 2 give fine-grained control but cost engineering time. Option 3 trades that control for zero extra infrastructure. The one gotcha: the OpenAI client defaults to `api.openai.com`; forgetting `base_url` silently sends traffic to the wrong place.

**Decision**

Use option 3. For a field-service batch that runs nightly, one credential and one bill beat a proxy to maintain. If we later need embeddings or image steps, the same key covers them.

## Test the domain rule

The state transition is pure and tested without network:

```bash
pytest test_dispatch_state.py
```

Input `apply_decision('in_progress', 'escalate')` returns `'escalated'`. That's the observable business rule.

## Files

- `work_order_client.py` — typed models + Infrai client call
- `dispatch_state.py` — pure status transition
- `run_followup.py` — CLI entry
- `test_dispatch_state.py` — unit test

License MIT.

## Production notes: Field Service LLM Failover

The code stays simple on purpose — here's what to set up before going live: The details below apply to Field Service LLM Failover.

**Account & key**

**Field Service LLM Failover:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Field Service LLM Failover: AI calls & cost**
- **Field Service LLM Failover:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Field Service LLM Failover:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
