---
paths:
  - "backend/src/**/domain/**"
  - "backend/src/**/modules/salaries/**"
  - "backend/src/**/modules/insights/**"
  - "backend/src/**/modules/imports/**"
  - "backend/src/**/seed/**"
  - "frontend/src/lib/money*"
---

# Money rules

Source: [docs/06-data-model.md](../../docs/06-data-model.md) §5, [ADR 0004](../../docs/adr/0004-money-integer-minor-units.md),
[ADR 0005](../../docs/adr/0005-fx-read-time-conversion.md), [glossary](../../docs/glossary.md) §3.

- **Integer minor units + ISO 4217 code**, always together: `{ amount_minor: int, currency: "EUR" }`.
  Never a `float`, never a bare number without its currency.
- **Exponent per currency** from `domain/currency.py`: JPY = 0; USD, EUR, GBP, INR, CAD, AUD, SGD, BRL = 2.
- **Reject excess decimals, don't round** them (`¥1,000.5` → 422 `too_many_decimals`).
- **Never add amounts in different currencies.** Stats within one country use local currency;
  cross-country comparisons use USD.
- **Convert to USD only at read time**, in `domain/money.py`, with a dated rate:
  `Decimal(amount_minor) / 10**exp * Decimal(rate_to_usd)`, then round half-even to minor units.
  Every response with a USD figure carries `fx_as_of` (the oldest `as_of` used). Never convert in SQL or the frontend.
- **`Decimal` only for rates, ratios and rounding** (compa-ratio, means, percentiles). Never `float` maths.
- **Rounding is half-even everywhere.** Compare pay-equity flags on the unrounded ratio.
- **Stored amounts are annual.** Monthly = annual ÷ 12, half-even, **display only**.
- **Salary currency is the employee's country `default_currency`.** A country change is a salary change.
- Frontend: format with `Intl.NumberFormat` using the currency exponent; split major/minor with `BigInt`
  or string maths, not division. Every amount shows its currency (`US$`, `CA$`, `A$` where `$` is ambiguous).
