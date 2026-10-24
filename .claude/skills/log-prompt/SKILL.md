---
name: log-prompt
description: Use after a material AI interaction - a design decision, a generated module, a rejected suggestion, an AI mistake caught, or a research finding. Appends a curated entry with the real prompt to docs/ai/prompt-log.md.
---

# /log-prompt

Policy: [docs/16-claude-code-setup.md](../../../docs/16-claude-code-setup.md) §10. Real prompts only; never invented.

1. Append an entry at the end of `docs/ai/prompt-log.md`, numbered after the last one, in this format:

   ```markdown
   ### <N>. <Short title>
   - **Date / block:** YYYY-MM-DD · B<n>
   - **Intent:** what the user wanted.
   - **Prompt:** "<the user's real prompt, lightly cleaned for grammar>" (curated) — or verbatim.
   - **AI produced:** a summary of what the AI did or proposed.
   - **Decision:** what was accepted, changed or rejected, and why.
   - **⚠ correction:** (only if the AI was wrong, outdated or over-scoped) what was wrong and how it was caught.
   - **Verification:** tests run, docs checked, manual check.
   - **Commit:** <hash or PR link, when available>
   ```

2. Mark the prompt `curated` (cleaned) or `verbatim`.
3. For an autonomous decision (no user prompt), write **Prompt:** "(autonomous: <what was unclear>)".
4. One entry per material interaction, not per keystroke. Routine completions are not logged.
5. Commit: `docs(ai): log <short title>`.
