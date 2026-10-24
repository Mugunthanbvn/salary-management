---
name: adr
description: Use when a decision is made or changed that affects architecture, data, security, tooling or a trade-off. Writes a new numbered Architecture Decision Record in docs/adr/ from the template and links it from the docs index.
---

# /adr <title>

1. Find the highest number in `docs/adr/`. The new number is that + 1, zero-padded to 4 digits.
2. Copy `docs/adr/0000-template.md` to `docs/adr/NNNN-<kebab-title>.md`.
3. Fill in:
   - **Context:** the forces (requirements, constraints, time, cost). Facts, with links.
   - **Decision drivers** and **Considered options**, each option with pros and cons and why it was rejected.
   - **Decision:** one paragraph, active voice ("We choose X because …").
   - **Consequences:** positive, negative (with mitigation), follow-ups.
   - Status `Proposed`, today's date.
4. If it supersedes an ADR, set the old one's status to `Superseded by ADR-NNNN` and link both ways.
5. Add a row to the ADR table in `docs/README.md`.
6. Update every doc the decision changes, in the same commit.
7. Ask the user to accept, then set Status `Accepted`. In an autonomous session (decisions delegated),
   set `Accepted` and log the decision in `docs/ai/prompt-log.md`.
8. Commit: `docs(adr): add NNNN <short title>`.
