# ADR-0015: "Ask about pay" via read-only LLM tool calling over existing insight services; OpenAI-compatible adapter with Gemini (default) and Groq (alternative)

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The brief wants the HR manager to "**answer questions about how the org pays people**", and the role is "Python/React/**AI**". None of the reviewed competitor submissions had an AI feature. The idea: the HR manager types a plain-English question ("Are we underpaying anyone in Germany?") and gets an answer grounded in real data, with figures, currency, FX date, and a "How I got this" trace.

The candidate asked for a **free** LLM provider (**Gemini** personal key or **Groq** free key) instead of a paid one, and chose **Gemini as default, Groq as alternative**. Research findings (Oct 2026):
- **Gemini free tier:** Flash-class models (Pro left the free tier in April 2026), roughly 15 RPM and 1,500 RPD (Google no longer publishes a fixed table). **Free-tier prompts may be used to improve Google's products** (except in the EU, UK and Switzerland).
- **Groq free tier:** open models (e.g. gpt-oss-120b, Llama 3.3 70B) with tool calling, roughly 30 RPM and 1,000 RPD, but **about 6–12k tokens per minute** per organisation, which is often the real bottleneck. Groq states it doesn't train on API data (to verify at signup).
- Both expose **OpenAI-compatible** chat-completions endpoints with function/tool calling.

## Decision drivers

- Correctness: AI numbers must match the dashboard.
- Safety: the model must not be able to write data or exceed the user's permissions.
- Determinism in CI (no network, no flakiness).
- $0 cost; provider-agnostic.
- Privacy awareness (salary data).

## Considered options

1. **Read-only tool calling over the existing InsightService**, with one OpenAI-compatible adapter.
2. **Text-to-SQL** (the LLM writes SQL against the database).
3. **RAG over exported reports.**
4. No AI feature (AI only in the dev workflow).
5. Provider-specific SDKs (Gemini SDK, Groq SDK, Anthropic SDK) per provider.

### Option 2: Text-to-SQL
- Rejected: injection and permission-bypass risk, cross-currency mistakes, and results that differ from the dashboard.

### Option 3: RAG
- Rejected: aggregates go stale, and retrieval isn't suited to numeric questions.

### Option 5: per-provider SDKs
- Rejected: more code paths for the same capability.

## Decision

**Option 1.**
- `LLMClient` interface (protocol). Production implementation: **OpenAI-compatible adapter** (`openai` SDK) configured by `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`. **Default: Gemini (free); alternative: Groq (free).** Exact model IDs are TBD at implementation.
- **Feature flag:** no key means the endpoint is disabled and the UI hides the Ask page.
- **Tools (read-only)**, thin wrappers over InsightService: `get_pay_overview`, `get_pay_by_group`, `compare_groups` (returns the % difference itself, so the model never does arithmetic), `get_salary_distribution`, `get_pay_equity_outliers`, `get_raise_stats`. Plus `get_top_earners` and `search_employees`, which need `SALARY_READ`. Arguments are enum-validated against reference data.
- **Role safety, three layers:**
  1. Tools the user may not use are not offered to the model.
  2. The executor re-checks permission.
  3. The service layer applies masking and the small-group rule ([ADR-0009](0009-permission-rbac-small-group-rule.md)).
- **Prompt injection through data** (e.g. a malicious employee name from an import): tool results are treated as data, and all tools are read-only and role-scoped, so the worst case is a wrong answer, never a write or a leak beyond the role.
- **Currency rule** in the system prompt: always state the currency and FX date; compare across countries only via USD fields.
- **Limits:** max 4 tool steps; compact system prompt (reference data inline); on a 429 from the provider, show a friendly "busy, retry in X s"; per-user limit (e.g. 20/hour, counted from `audit_events`).
- **Conversation:** follow-ups supported. The client keeps and sends the last ~6 turns; nothing is stored server-side. UI shows a **spinner** (no streaming in v1).
- **Response:** `{answer, figures[], tool_calls[], caveats[]}`. Each question is audited (`ask.query`).
- **Testing:** `FakeLLM` plays back scripted tool calls, so CI is deterministic. An **eval set** (`docs/ai/evals/ask.yaml`, about 15 questions with expected tools and figures from the seed's documented "demo story") is run manually with `make eval-ask PROVIDER=gemini|groq`, and the results plus a **model comparison table** are committed.

## Consequences

### Positive
- A grounded, auditable, role-safe AI feature at $0, with numbers identical to the dashboard.
- Provider swap is configuration only, and the eval set makes the choice measurable.

### Negative / risks
- **Privacy:** Gemini's free tier may train on prompts. That's acceptable only because the demo data is **synthetic**. A real deployment must use a paid or no-training tier (or self-hosting), and tools return aggregates by default (data minimisation). Documented in [08-security-rbac.md](../08-security-rbac.md).
- Free-tier rate and token limits can throttle demos. Mitigated by compact prompts, the step cap, and graceful 429 handling.
- LLM answers can still be phrased wrongly. Mitigated by the `compare_groups` tool (no model arithmetic), the visible tool trace, and the eval set.

## Implementation notes (B9, 2026-10-24)

- Default model: `gemini-flash-latest` on `https://generativelanguage.googleapis.com/v1beta/openai/` (empty `LLM_MODEL` / `LLM_BASE_URL` mean these). No key was available at build time, so the id is unconfirmed; pin a dated Flash id after the first `make eval-ask` run.
- Seven tools were built (no distribution or raises tools, no `include_employees`); see [10 §4](../10-ai-ask-design.md#4-tools).
- Invalid output after the repair retry is a 502 (glossary §5), not the raw text.
- Figures are grounded: one whose number no tool returned is dropped with a caveat.

## Links

- [10-ai-ask-design.md](../10-ai-ask-design.md), [08-security-rbac.md](../08-security-rbac.md), [14-testing-strategy.md](../14-testing-strategy.md), [ai/evals/README.md](../ai/evals/README.md)
