#!/usr/bin/env bash
# PostToolUse formatter for Edit/Write (see docs/16-claude-code-setup.md §7.2).
#   backend/**/*.py                          -> ruff format + ruff check --fix
#   frontend/**/*.{ts,tsx,css,json,md}       -> prettier --write
# Input: the hook JSON on stdin. Exit 0 = done or nothing to do (also when the tool isn't installed yet).
# Exit 2 = the edit stays, but a formatter/linter problem is reported back to Claude on stderr.
set -u

input="$(cat)"

if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
elif command -v python3 >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | python3 -I -c '
import json, sys
try:
    print((json.load(sys.stdin).get("tool_input") or {}).get("file_path") or "")
except Exception:
    pass
' 2>/dev/null)"
else
  exit 0
fi

[ -n "${file:-}" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
case "$file" in
  "$root"/*) rel="${file#"$root"/}"; abs="$file" ;;
  /*) exit 0 ;; # outside the repo
  *) rel="${file#./}"; abs="$root/$rel" ;;
esac
[ -f "$abs" ] || exit 0

report() {
  printf 'format-changed-file: %s reported problems in %s:\n%s\n' "$1" "$rel" "$(printf '%s' "$2" | head -n 40)" >&2
  exit 2
}

case "$rel" in
  backend/.venv/* | */node_modules/* | frontend/.next/*)
    exit 0 ;;

  backend/*.py)
    command -v uv >/dev/null 2>&1 || exit 0
    [ -f "$root/backend/pyproject.toml" ] || exit 0
    [ -x "$root/backend/.venv/bin/ruff" ] || exit 0 # project ruff not installed yet (run make setup)
    cd "$root/backend" || exit 0
    out="$(uv run --quiet --no-sync ruff format "$abs" 2>&1)" || report "ruff format" "$out"
    # F401 is not auto-fixed: an import added in one edit is used in the next.
    out="$(uv run --quiet --no-sync ruff check --fix --unfixable F401 "$abs" 2>&1)" || report "ruff check" "$out"
    ;;

  frontend/*.ts | frontend/*.tsx | frontend/*.css | frontend/*.json | frontend/*.md)
    [ -d "$root/frontend/node_modules" ] || exit 0
    prettier="$root/frontend/node_modules/.bin/prettier" # the binary 'pnpm prettier' runs
    [ -x "$prettier" ] || exit 0
    command -v node >/dev/null 2>&1 || exit 0
    cd "$root/frontend" || exit 0
    out="$("$prettier" --write --log-level warn "$abs" 2>&1)" || report "prettier" "$out"
    ;;
esac

exit 0
