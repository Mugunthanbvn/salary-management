# ACME Pay design system: "Marked-up printout"

The look-and-feel rules the frontend follows. Chosen on 2026-10-24 from the Claude Design canvas ([source](claude/README.md)). Behaviour and data rules live in [13-frontend-ux.md](../13-frontend-ux.md); this file covers look and feel only.

## Idea

HR's job today is reading Excel printouts with a highlighter and a red pen. The app keeps that habit:
- **Every section leads with the question HR is asking** ("What does a typical employee earn in each country?", "Is anyone paid unfairly?") in a large serif heading, with the answer beside it.
- **The figure that matters gets a highlighter mark.** Problems get a red-pen underline (or a red circle around a bad cell on import).
- **Short notes sit in the margin** in italic serif, explaining a number or a rule.

## Tokens

| Token | Value | Use |
|---|---|---|
| `paper` | `#FFFFFF` | Page background |
| `ink` | `#000000` | Headings, key text, primary buttons, bars |
| `ink-2` | `#3D3D3D` | Secondary text |
| `ink-3` | `#5C5C5C` | Small meta text (employee codes, dates) |
| `rule` | `#E2E2E2` | 1 px rules between rows and sections |
| `highlighter` | `#FFE45C` | The one key figure per section (a tweakable option: `#B9F2C8`, `#FFD1DC`, `#CDE4FF`) |
| `red-pen` | `#C62828` | Below band, errors, destructive actions |
| `blue-pen` | `#1F4FD8` (hover `#173A9E`) | Links, above band |

No other colours, no gradients except the highlighter mark itself, no shadows.

**Highlighter mark:** `background: linear-gradient(180deg, transparent 42%, var(--highlighter) 42%, var(--highlighter) 90%, transparent 90%)`, on the key phrase or figure only, at most once per section.
**Red-pen underline:** `text-decoration: underline; text-decoration-color: #C62828; text-decoration-thickness: 2–3px; text-underline-offset: 4–6px`.

## Type

- **Source Serif 4**: page titles (44–48), section questions (28), big figures (19–44), margin notes (italic 15).
- **Atkinson Hyperlegible Next**: body, tables, labels, buttons (13–17). Chosen for legibility of dense numbers.
- Tabular figures (`font-variant-numeric: tabular-nums`) on every number. Sentence case. No all-caps labels, no monospace, no emoji.

## Layout

- One column of sections, max width 1280 px, 32 px side padding (16 px on phones).
- A **section** is a two-column row: the question on the left (`flex: 1 1 280px`), the answer on the right (`flex: 999 1 640px`). Below about 960 px the question stacks above the answer.
- The page title block ends with a 2 px ink rule; sections are separated by 1 px rules.
- Summaries are sentences, not KPI tiles ("9,012 full-time employees in 10 countries, paid US$823.5M a year").
- Status is a word ("Below band" in red-pen underline, "Above band" in blue), not a pill badge.
- Corners 4 px on buttons and inputs only. Buttons: primary = ink fill, secondary = 1 px ink outline, destructive = red-pen text.
- Search and Ask inputs are large serif text on a 2 px ink underline, like writing on the page.

## Mobile

Phone layout per [13-frontend-ux.md](../13-frontend-ux.md) §8: one column, tables become list rows, a bottom navigation bar (Insights, Employees, Ask), and a fixed bottom bar for the main action on detail screens (e.g. "Record salary change"). Touch targets ≥ 44 px.

## Building it

shadcn/ui components restyled with these tokens (Tailwind theme). The canvas `.dc.html` files are a visual reference, not production code.
