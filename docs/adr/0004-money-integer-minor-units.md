# ADR-0004: Money stored as integer minor units plus an ISO 4217 currency code

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

ACME pays employees in about 10 countries and 9 currencies (USD, INR, GBP, EUR, CAD, SGD, AUD, JPY, BRL). Money must never suffer floating-point drift. Currencies have different numbers of decimal places: ISO 4217 defines the "minor unit" exponent per currency (JPY = 0, USD = 2, KWD = 3).

**SQLite has no true DECIMAL type**: SQLAlchemy's `Numeric` on SQLite is stored with REAL (float) affinity. The candidate asked us to research the industry standard before deciding.

## Decision drivers

- Exactness (no float math on money, ever).
- Portability between SQLite/Turso and Postgres ([ADR-0002](0002-sqlite-everywhere-turso.md)).
- Correct handling of zero-decimal and three-decimal currencies.
- Industry practice (payments platforms, money libraries such as Dinero.js).

## Considered options

1. **Integer minor units (BIGINT) + ISO 4217 code**, with a per-currency exponent table.
2. **DECIMAL/NUMERIC(19,4)** with an explicit scale in the schema.
3. **Float** columns.
4. **Decimal stored as a string** in a TEXT column.

### Option 1
- Pros: exact; portable to every SQL engine; integer aggregates (`SUM`) are exact; widely used by payment systems.
- Cons: the application must apply the exponent consistently, so a `Money` value object is mandatory.

### Option 2
- Pros: the scale lives in the schema.
- Cons: **not portable to SQLite** (stored as REAL there), which breaks the "one dialect" guarantee.

### Option 3
- Rejected outright: rounding drift when summing.

### Option 4
- Pros: exact.
- Cons: no SQL arithmetic or aggregation.

## Decision

**Option 1.**
- Columns are named `*_minor` (e.g. `base_minor`, `amount_minor`) and typed `BIGINT`, alongside `currency CHAR(3)`.
- A pure domain module `domain/currency.py` holds the ISO exponents, and `domain/money.py` provides an immutable `Money(amount_minor: int, currency: str)` value object. Arithmetic is only allowed within one currency; cross-currency operations raise.
- Input validation **rejects** amounts with more decimals than the currency allows (e.g. `¥1000.5`) instead of silently rounding.
- Conversions use Python `Decimal` with an explicit rounding mode (half-up, documented).
- The API returns money as `{amount_minor: int, currency: "EUR"}`, and the frontend formats it with `Intl.NumberFormat` driven by the exponent. No float math on totals in JavaScript.
- FX conversion rules are in [ADR-0005](0005-fx-read-time-conversion.md).

## Consequences

### Positive
- Exact and portable. Easy to test with Hypothesis properties (round-trip, addition associativity, exponent correctness).
- JPY and other zero-decimal currencies work correctly by construction.

### Negative / risks
- Every developer (and the AI) must remember the convention. Mitigation: `.claude/rules/money.md`, the reviewer agent's checklist, and naming (`_minor`).
- `BIGINT` limits are far above any salary, so overflow isn't a practical concern.

## Links

- [06-data-model.md](../06-data-model.md), [09-insights-pay-equity.md](../09-insights-pay-equity.md), [16-claude-code-setup.md](../16-claude-code-setup.md)
- Research sources summarised in [04-research.md](../04-research.md)
