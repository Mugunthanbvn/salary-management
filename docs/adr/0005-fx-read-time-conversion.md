# ADR-0005: FX conversion at read time only, with USD as the reporting currency

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The HR manager needs both per-country views ("what do we pay in India?") and org-wide views ("total payroll", "which country pays senior engineers most?"). Comparing raw amounts across currencies is meaningless, and summing INR with EUR is a classic mistake. The brief stresses answering "how the org pays people", so misleading cross-country numbers would be a product failure.

## Decision drivers

- Historical data must never silently change when rates change.
- Every cross-currency figure must be transparent about the rate used.
- Per-country analysis should stay in the currency people are actually paid in.

## Considered options

1. **Convert at read time** using an `fx_rates` table. Never persist converted amounts.
2. **Store a USD amount** alongside each salary at write time.
3. **Single currency (USD) only.**

### Option 1
- Pros: the stored data is exactly what was agreed with the employee. Reports are reproducible for a given rate snapshot, and updating rates doesn't rewrite history.
- Cons: conversion work on each read (trivial at 10k rows).

### Option 2
- Pros: fast reads.
- Cons: converted values go stale; historical totals shift unpredictably when rates are refreshed; two sources of truth.

### Option 3
- Pros: simplest.
- Cons: ignores the multi-country problem statement and shows naive product thinking.

## Decision

**Option 1.**
- `fx_rates(currency PK, rate_to_usd TEXT (Decimal string), as_of DATE, source TEXT)`. The rate is stored as a decimal string so it stays exact on SQLite.
- The seed loads a **static, illustrative snapshot** (as_of 2026-10-01). Admins can edit rates (`/admin/fx-rates`, audited).
- **Per-country statistics are computed in local currency.** USD values are computed in Python with `Decimal` from the per-row or per-group local amounts.
- Every API response containing USD figures includes `fx_as_of`, and the UI shows it ("USD at rates as of 2026-10-01").
- Local amounts are never summed or compared across different currencies; cross-country views use the USD fields only.
- Live FX feeds are **out of scope** (see [02-requirements-one-pager.md](../02-requirements-one-pager.md)).

## Consequences

### Positive
- Correct, explainable cross-country insights, with history stable over time.
- The AI "Ask" feature follows the same rule (always state the currency and FX date; see [ADR-0015](0015-ai-ask-tool-calling.md)).

### Negative / risks
- Static rates are illustrative, not market-accurate, and labelled as such.
- A single "current" rate per currency, with no rate history. Rate history is listed as future work.

## Links

- [ADR-0004](0004-money-integer-minor-units.md), [06-data-model.md](../06-data-model.md), [09-insights-pay-equity.md](../09-insights-pay-equity.md)
