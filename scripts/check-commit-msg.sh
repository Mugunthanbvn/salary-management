#!/usr/bin/env bash
# commit-msg hook (lefthook.yml): the subject must be a Conventional Commit.
# Rule and regex: docs/15-tooling-devex.md sections 7 and 9.
# Usage: scripts/check-commit-msg.sh <commit-message-file>
set -euo pipefail

message_file="${1:?usage: scripts/check-commit-msg.sh <commit-message-file>}"
pattern='^(feat|fix|test|refactor|docs|chore|ci|build|perf|style|revert)(\([a-z0-9-]+\))?!?: .{1,72}$'

# The subject is the first line that is neither blank nor a git comment.
subject="$(grep -v -e '^#' -e '^[[:space:]]*$' "$message_file" | head -n 1 || true)"

case "$subject" in
  "Merge "* | 'Revert "'*) exit 0 ;; # written by git merge --no-ff and git revert
esac

if printf '%s\n' "$subject" | grep -Eq -- "$pattern"; then
  exit 0
fi

cat >&2 <<MSG
Commit subject is not a Conventional Commit:
  $subject
Expected: type(scope): subject   (subject 1-72 characters)
Types: feat fix test refactor docs chore ci build perf style revert. Scope: [a-z0-9-].
Example: test(money): reject float amounts
MSG
exit 1
