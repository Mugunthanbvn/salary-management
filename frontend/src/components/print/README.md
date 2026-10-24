# Printout components

The few building blocks of the "Marked-up printout" look ([docs/design/DESIGN.md](../../../../docs/design/DESIGN.md)).
Import them from `@/components/print`. Build screens from these and the restyled shadcn primitives in
`@/components/ui`; add a new one here only when two screens need it.

| Component    | Use                                                                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `PageTitle`  | Every page starts with it: serif `h1` (`title`), one summary sentence (`children`), optional `actions` (toggles) on the right, 2 px ink rule below                                         |
| `Section`    | One question and its answer: `question` (serif `h2`, left, `flex 1 1 280px`) and `children` (right, `flex 999 1 640px`). Stacks below about 960 px. It is a `region` named by its question |
| `Highlight`  | The highlighter mark on the one key figure or phrase of a section, at most once (`<mark>`)                                                                                                 |
| `RedPen`     | Red-pen underline for a problem ("8% below its pay bands")                                                                                                                                 |
| `MarginNote` | Italic serif note that explains a number or a rule                                                                                                                                         |
| `StatusWord` | A status as a word, never a pill: `tone="problem"` for "Below band" (red-pen underline), `"notice"` for "Above band" (blue), `"plain"` for "In band"                                       |
| `Money`      | `amountMinor` + `currency` (+ `formatMoney` options) on one line, `tabular-nums`. Use it, or `formatMoney` from `@/lib/money`, for every amount                                            |
| `EmptyState` | Nothing to show: `title`, an explanation (`children`) and the next `action`                                                                                                                |
| `ErrorState` | An API problem: `title`, `detail`, `requestId`, and "Try again" (`onRetry`, or a refresh of the page's server data). Client Component: pass plain fields, not a `ProblemError`             |
| `Forbidden`  | A page the person's permissions don't allow: "You don't have access to this", an optional `reason`, a link to Insights                                                                     |

Rules they already follow: tokens only (`paper`, `ink`, `ink-2`, `ink-3`, `rule`, `highlighter`, `red-pen`,
`blue-pen`), sentence case, no shadows, no rounded corners except buttons and inputs, 44 px targets.

## Related helpers

- `@/lib/money`: `formatMoney(amountMinor, currency, { period, compact, minorUnits, locale })`.
- `@/lib/numbers`: `formatRatio("0.9234")` → `0.92`, `formatPercent("0.44")` → `44%`, `formatCount(9012)` → `9,012`.
- `@/components/shell/me-context`: `useMe()` in Client Components (`me.user`, `me.features`, `me.can("IMPORT")`).
- `@/lib/api/me`: `getMe()` in Server Components; `@/lib/permissions`: `can(me, "SALARY_READ")`, `canAsk(me)`.
- `@/components/shell/skeletons`: `PageSkeleton` for a page's own `loading.tsx`.
