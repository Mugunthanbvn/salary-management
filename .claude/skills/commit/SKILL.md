---
name: commit
description: Use when the user asks to commit, or when a TDD step (red, green or refactor) is complete. Stages one logical change and writes a Conventional Commit with the project's attribution trailer.
---

# /commit

1. Run `git status` and `git diff --staged`. If nothing is staged, propose a **single logical** change set and stage it
   by path (`git add <files>`), never blindly `git add -A`.
2. Keep red and green separate: never put a new failing test and its implementation in one commit during TDD pairing.
3. Write a Conventional Commit message:
   - Subject `type(scope): subject`, imperative, ≤ 72 characters, matching
     `^(feat|fix|test|refactor|docs|chore|ci|build|perf|style|revert)(\([a-z0-9-]+\))?!?: .{1,72}$`.
   - Scopes follow modules: money, auth, employees, salaries, insights, import, export, audit, ask, seed, ui, deploy, docs.
   - A body that explains **why**, when it isn't obvious.
4. End the message with the attribution trailer, exactly:

   ```
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   Claude-Session: https://claude.ai/code/session_01TeA7MkfNzAjPMWbzGMqgrL
   ```

5. Commit with a heredoc so the trailer survives:

   ```bash
   git commit -F - <<'EOF'
   test(money): reject float amounts

   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   Claude-Session: https://claude.ai/code/session_01TeA7MkfNzAjPMWbzGMqgrL
   EOF
   ```

6. If a git hook fails, fix the cause and make a new commit. Never `--no-verify`, never amend a pushed commit,
   never force-push, and don't push unless asked.
