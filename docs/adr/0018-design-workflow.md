# ADR-0018: UI design workflow: Claude Design canvases → DESIGN.md → build with frontend-design → Impeccable audit

- **Status:** Deferred (2026-10-24): the Claude Design phase is cut from v1 to fit a 1–2 day build. v1 uses shadcn/ui defaults with the frontend-design skill. See the [v1 scope](../README.md#v1-scope-decided-2026-10-24-read-this-first).
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

AI-generated UIs tend to share recognisable "AI slop" traits: purple gradients, Inter everywhere, cards inside cards, cramped spacing, generic hero layouts. The candidate wanted design skills involved (the official frontend-design skill plus an anti-slop skill) and asked whether to use **Google Stitch** or Claude's **`/design`** for screen designs.

This product is a **data-dense internal HR tool**, where legibility of numbers, trust and efficiency matter more than marketing flair.

## Decision drivers

- Design exists **before** code (mirrors spec-before-code).
- One coherent AI workflow story for the interview.
- Output that fits the chosen component system (shadcn/ui + Tailwind).
- Checkable quality rules, not just taste.

## Considered options

1. **Claude Design / `/design` canvases** → frozen `DESIGN.md` → build with **frontend-design** → **Impeccable** audit per screen.
2. **Google Stitch** (Gemini-based designer, DESIGN.md export, MCP server) → same build and audit steps.
3. No screen designs; go straight to shadcn with the skills only.

### Option 2: Google Stitch
- Pros: fast visual exploration; portable DESIGN.md export.
- Cons: an extra vendor and login; its HTML output doesn't match shadcn, so it gets rewritten anyway.

### Option 3: No screen designs
- Pros: fastest.
- Cons: design decisions get made ad hoc in code, with nothing to review before building.

## Decision

**Option 1.**
1. **Design phase (milestone 7b):** Claude Design canvases for 5 key screens (Insights dashboard, Employee list, Employee detail + salary timeline, Import preview, Ask), **2 options each**. The candidate picks.
2. Freeze the result as **`docs/design/DESIGN.md`** (tokens, typography, spacing, component rules) plus screenshots, and mirror it to **`.claude/rules/design.md`** so Claude follows it while building.
3. Build with shadcn/ui + Tailwind, guided by the official **frontend-design** skill.
4. Before each frontend PR merges, run an **Impeccable** audit (pbakaus/impeccable, Apache 2.0, deterministic anti-pattern rules). Findings and fixes are logged in [ai/prompt-log.md](../ai/prompt-log.md). **Impeccable's files are reviewed before installation**, because third-party skills can ship scripts and hooks.

**Design direction:**
- Tabular numerals for money and explicit currency labels.
- Neutral palette with one accent.
- Dense but breathable tables.
- Light and dark modes.
- Keyboard-friendly; WCAG AA.

## Consequences

### Positive
- Visible design-before-code artifacts, objective anti-slop checks, and one tool family across the workflow.

### Negative / risks
- Claude Design is a newer product; if canvases are unavailable, fall back to Option 3 with DESIGN.md written by hand.
- Supply-chain risk of a third-party skill, mitigated by reviewing its files first and pinning the version.
- Some critics say the frontend-design skill alone still produces generic output, which is why Impeccable is added as an objective check.

## Links

- [13-frontend-ux.md](../13-frontend-ux.md), [16-claude-code-setup.md](../16-claude-code-setup.md), [18-implementation-plan.md](../18-implementation-plan.md)
