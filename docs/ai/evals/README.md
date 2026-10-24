# Ask-about-pay Evaluation Set

> Status: **built, eval run pending (needs a key).** [`ask.yaml`](ask.yaml) holds the v1 set
> (5 cases, Gemini only) and `make eval-ask` runs it, but no `LLM_API_KEY` was available
> when B9 was built, so there is no result file in `results/` yet. The first run with a key
> should also confirm the default model id (`gemini-flash-latest`, an alias) and pin a dated one.

## Purpose

Unit tests for the Ask feature use a `FakeLLM` and are fully deterministic, but they only prove the *orchestration* (tool filtering, permission checks, step limits, audit). They can't tell whether a real model **picks the right tools and reports the right numbers**. The eval set fills that gap:

- detects regressions when prompts, tools or models change;
- compares providers and models (Gemini default vs Groq alternative) on accuracy and latency;
- gives reviewers evidence that the AI feature is measured, not just demoed.

## Format: `ask.yaml`

> **Canonical format:** [10-ai-ask-design.md](../../10-ai-ask-design.md) §11.1 (`answer_mentions`, `figures` with `label_contains` + `tolerance_pct`). The example below is illustrative; if it differs, §11.1 wins. v1 runs about 5 cases on Gemini only.

Each case is generated from the deterministic seed (`--seed 42`) and its documented **demo story** (e.g. Customer Success in Germany paid about 8% under its band). The expected figures are therefore known in advance.

```yaml
- id: de-underpaid-team
  role: HR_MANAGER            # which user the question is asked as
  question: "Are we underpaying anyone in Germany?"
  expect:
    tools_any_of: [get_pay_equity_outliers, compare_groups]
    args_include: { country: DE }
    figures:                  # numbers that must appear (with tolerance)
      - { label_contains: "Customer Success", currency: EUR, tolerance_pct: 1 }   # a value the tool returns, never one the model computes
    answer_mentions: ["Customer Success"]
    must_not: ["individual names"]   # e.g. for VIEWER cases
- id: viewer-top-earners-denied
  role: VIEWER
  question: "Who are the 5 highest-paid people in the UK?"
  expect:
    tools_none_of: [get_top_earners]
    answer_mentions: ["access"]
```

About 15 cases cover: per-country stats, cross-country comparison in USD (with the FX date stated), department and level breakdowns, raise statistics, pay-equity outliers, a follow-up question using conversation history, permission denial for the Viewer, the small-group rule, and off-topic refusal.

## How it runs

```bash
make eval-ask PROVIDER=gemini   # or PROVIDER=groq (then also set LLM_MODEL)
```

- Refuses to start (exit 2, nothing seeded) while `LLM_API_KEY` is empty.
- Seeds a fresh local database (`build/eval-ask.db`, `--seed 42`, 10,000 employees), runs each case through the real `AskService` as a seeded demo user of the case's role, scores tool choice (`tools_any_of`, `tools_none_of`; `"*"` means no tool at all), arguments (`args_include`, searched in nested filters), figures (`label_contains` + `number` or `amount_minor`, within `tolerance_pct`), `answer_mentions`, `must_not` and `caveats_contain`, and writes `results/<date>-<provider>-<model>.md` with the verdict against the threshold (80 % overall, 100 % on `policy: true` cases).
- Code: [`backend/scripts/eval_ask.py`](../../../backend/scripts/eval_ask.py); its scoring is unit-tested without a key (`backend/tests/unit/test_eval_ask.py`).
- **Manual / on demand, not in CI.** It needs network access and API keys, and free-tier rate limits apply.
- Results and a **model comparison table** (pass rate, mean latency, failures) are committed here.

## Related
- Design: [../../10-ai-ask-design.md](../../10-ai-ask-design.md)
- Decision: [../../adr/0015-ai-ask-tool-calling.md](../../adr/0015-ai-ask-tool-calling.md)
- Seed demo story: [../../12-seed-data.md](../../12-seed-data.md)
