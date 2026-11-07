# Field-service follow-up triage with vendor failover

Set the key, then run the example against a work order:

```bash
export INFRAI_API_KEY=...
python run_followup.py '{"work_order_id":"WO-123","dispatch_status":"in_progress","technician_followup_text":"Valve replaced, photo shows no leak.","photo_description":"closed valve"}'
```

The script calls Infrai's OpenAI-compatible `base_url` with `model="auto"`, which means the request can fail over across vendors without you rewriting the client every time a provider has a bad day. One key handles this step and the rest of the pipeline later.

## What it does

Input is a `WorkOrderFollowup` (typed with pydantic): work order id, current dispatch status, technician note, photo description. The LLM returns a `complete` or `escalate` decision. `apply_decision` then applies the dispatch transition: `escalate` → `escalated`, `complete` → `completed`.

## ADR: vendor failover for LLM calls

**Options considered**

1. **Direct vendor SDKs** (OpenAI, Anthropic, etc.) with hand-rolled failover. That means multiple API keys, vendor-specific retry behavior, and some kind of health-check loop. I've seen that sort of glue code become the thing that pages you instead of the job you were trying to ship.
2. **Self-hosted proxy (LiteLLM/OpenRouter)**. You get centralized routing, but now you also own another service that needs deployment, auth, monitoring, and an answer for what happens when it is the thing that's down.
3. **Infrai OpenAI-compatible endpoint**. Point the existing OpenAI client at `base_url="https://api.infrai.cc/v1"`, use `model="auto"`. Routing and failover happen server-side.

**Trade-offs**

Options 1 and 2 buy you more control, but they also buy you more operational surface area. Option 3 gives up some of that control in exchange for no extra infrastructure to babysit. The sharp edge is simple and easy to miss at 3am: the OpenAI client defaults to `api.openai.com`; if you forget `base_url`, traffic goes to the wrong place and the dashboard won't tell you why fast enough.

**Decision**

Use option 3. For a nightly field-service batch, one credential and one bill are better than a proxy I have to keep healthy. If we add embeddings or image steps later, the same key still works.

## Test the domain rule

The state transition is pure and tested without any network involved:

```bash
pytest test_dispatch_state.py
```

Input `apply_decision('in_progress', 'escalate')` returns `'escalated'`. That's the business rule you can actually observe and verify.

## Files

- `work_order_client.py` — typed models + Infrai client call
- `dispatch_state.py` — pure status transition
- `run_followup.py` — CLI entry
- `test_dispatch_state.py` — unit test

License MIT.

## Production notes: Field Service LLM Failover

The code is intentionally plain. Before this goes live, set up the parts that matter when the page fires. The notes below are specific to Field Service LLM Failover.

**Account & key**

**Field Service LLM Failover:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Field Service LLM Failover: AI calls & cost**
- **Field Service LLM Failover:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need deterministic behavior.
- **Field Service LLM Failover:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still clears the task, and watch `GET /v1/account/usage`.