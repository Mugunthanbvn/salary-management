---
paths:
  - "frontend/src/**"
---

# Design rules

Mirrors [docs/design/DESIGN.md](../../docs/design/DESIGN.md) ("Marked-up printout"). If they differ, DESIGN.md wins
on look and feel and [docs/13-frontend-ux.md](../../docs/13-frontend-ux.md) wins on behaviour.
Visual reference: `docs/design/claude/*.dc.html` (reference only, not production code).

## Tokens (Tailwind theme)

`paper #FFFFFF` · `ink #000000` · `ink-2 #3D3D3D` · `ink-3 #5C5C5C` · `rule #E2E2E2` ·
`highlighter #FFE45C` · `red-pen #C62828` · `blue-pen #1F4FD8` (hover `#173A9E`).
No other colours, no gradients except the highlighter mark, no shadows. One light theme: DESIGN.md defines no dark palette.

- **Highlighter mark:** `linear-gradient(180deg, transparent 42%, var(--highlighter) 42%, var(--highlighter) 90%, transparent 90%)`,
  on the one key figure or phrase per section, at most once.
- **Red-pen underline** for problems (below band, errors): underline, colour `red-pen`, 2–3 px thick, 4–6 px offset.

## Type

- Source Serif 4: page titles (44–48), section questions (28), big figures (19–44), margin notes (italic 15).
- Atkinson Hyperlegible Next: body, tables, labels, buttons (13–17).
- `tabular-nums` on every number; numeric table cells right-aligned. Sentence case.

## Layout and components

- One column of sections, max width 1280 px, 32 px side padding (16 px on phones).
- A section = question on the left (`flex: 1 1 280px`), answer on the right (`flex: 999 1 640px`);
  stacks below about 960 px. Title block ends with a 2 px ink rule; sections split by 1 px rules.
- Summaries are sentences, not KPI tiles. Status is a word ("Below band" red-pen underline, "Above band" blue), not a pill.
- Radius 4 px on buttons and inputs only. Primary = ink fill; secondary = 1 px ink outline; destructive = red-pen text.
- Search and Ask inputs: large serif text on a 2 px ink underline.
- shadcn/ui components restyled with these tokens; reuse before creating new ones.
- **Currency labelling:** every amount shows its currency via `lib/money.ts`; money never wraps between symbol and number.

## Mobile

One column, tables become list rows, bottom navigation (Insights, Employees, Ask), fixed bottom bar for the main
action on detail screens, touch targets ≥ 44 px, no horizontal page scroll from 360 px. Check at 390 × 844.

## Anti-patterns (don't)

Card grids, cards inside cards, KPI tiles, pill badges, all-caps labels, monospace, emoji, gradients,
shadows, glassmorphism, generic hero sections, extra accent colours, colour as the only signal.
