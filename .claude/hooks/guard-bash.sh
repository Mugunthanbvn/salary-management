#!/usr/bin/env bash
# PreToolUse guard for Bash (see docs/16-claude-code-setup.md §7.2).
# The allow rules for uv, uvx, npx and pnpm would let any command through them, so this hook checks
# the command itself:
#   block (exit 2): a .env / .env.<name> file other than .env.example; curl or wget as a command word
#   ask:            vercel or turso as a command word
# A command word starts the command or follows ; && || | & ( $( ` or a newline, or a wrapper such as
# env, sudo, time, xargs, uv run, uvx, npx, pnpm exec / dlx, bash -c. Quoted text and heredoc bodies
# are arguments, so `grep -r curl docs/` and commit messages pass.
# Needs python3 to parse the command; without it the hook allows (settings.json rules still apply).
set -u

if ! command -v python3 >/dev/null 2>&1; then
  echo "guard-bash: python3 not found; Bash guard skipped" >&2
  exit 0
fi

exec python3 -I -c "$(
  cat <<'PY'
import json, re, shlex, sys

ENV_FILE = re.compile(r"\.env([.*?\[].*)?")
WRAPPERS = {"sudo", "env", "time", "nohup", "exec", "command", "builtin", "nice", "xargs", "timeout",
            "then", "do", "else", "elif", "if", "while", "until", "!", "{"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
VALUE_FLAGS = {"--with", "--from", "-p", "--package", "--python", "--directory", "--project", "-C",
               "--dir", "--filter", "-F", "-u", "--user", "-n", "-s", "--signal", "-k", "--kill-after"}
ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
OPERATOR_CHARS = set("();<>|&")

blocks, asks = [], []


def strip_heredocs(text):
    """Drop heredoc bodies: they are data (e.g. a commit message), not commands."""
    out, pending = [], []
    for line in text.split("\n"):
        if pending:
            delim, dash = pending[0]
            if (line.lstrip("\t") if dash else line) == delim:
                pending.pop(0)
            continue
        out.append(line)
        for m in re.finditer(r"(?<!<)<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2", line):
            pending.append((m.group(3), m.group(1) == "-"))
    return "\n".join(out)


def tokens(text):
    text = text.replace("\\\n", " ").replace("\n", " ; ").replace("`", " ( ")
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        return list(lex)
    except ValueError:  # unbalanced quotes: fall back to a rough split
        return re.findall(r"[^\s;&|()<>]+|[;&|()<>]+", text.replace('"', " ").replace("'", " "))


def is_operator(tok):
    return set(tok) <= OPERATOR_CHARS


def is_separator(tok):
    return is_operator(tok) and (tok in ("&", "&&") or any(c in tok for c in ";|()"))


def base(word):
    return word.rsplit("/", 1)[-1]


def program(word):
    """Program name of a command word: /usr/bin/curl -> curl, vercel@latest -> vercel."""
    if word.startswith("@"):
        word = word.split("/", 1)[-1]
    return base(word.split("@", 1)[0])


def skip_flags(words, i):
    while i < len(words) and words[i].startswith("-") and words[i] != "--":
        flag = words[i]
        i += 1
        if flag in VALUE_FLAGS and i < len(words):
            i += 1
    if i < len(words) and words[i] == "--":
        i += 1
    return i


def command_word(words):
    """Return (command word, args) of one simple command, looking through wrappers."""
    i, n = 0, len(words)
    while i < n:
        word = words[i]
        name = base(word)
        if ASSIGN.fullmatch(word):
            i += 1
        elif name in WRAPPERS:
            i = skip_flags(words, i + 1)
            if name == "timeout" and i < n:
                i += 1  # the duration
        elif name == "uv" and i + 1 < n and words[i + 1] == "run":
            i = skip_flags(words, i + 2)
        elif name in ("uvx", "npx", "bunx"):
            i = skip_flags(words, i + 1)
        elif name in ("pnpm", "npm", "yarn", "bun"):
            j = skip_flags(words, i + 1)
            if j < n and words[j] in ("exec", "dlx", "x"):
                i = skip_flags(words, j + 1)
            elif name == "pnpm":
                i = j  # `pnpm <bin>` runs a local binary
            else:
                return word, words[i + 1:]
        elif name in SHELLS:
            for j in range(i + 1, n):
                flag = words[j]
                if not flag.startswith("-"):
                    break
                if not flag.startswith("--") and "c" in flag and j + 1 < n:
                    return "<script>", [words[j + 1]]
            return word, words[i + 1:]
        else:
            return word, words[i + 1:]
    return None, []


def check_command(words, depth):
    plain, skip_next = [], False
    for w in words:
        if skip_next:
            skip_next = False
        elif is_operator(w):  # a redirection; its target is not the command
            skip_next = True
        else:
            plain.append(w)
    word, args = command_word(plain)
    if word is None:
        return
    if word == "<script>":
        if depth < 3:
            analyse(args[0], depth + 1)
        return
    prog = program(word)
    if prog in ("curl", "wget"):
        blocks.append(f"'{prog}' fetches from the network in the shell. Use the web tools instead, so research stays visible.")
    elif prog in ("vercel", "turso"):
        asks.append(f"'{prog}' is a deploy or cloud database CLI; the user confirms it first.")
    elif prog == "git":
        check_git(args)


GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
PUSH_DANGER = {"--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete", "--prune"}
PUSH_VALUE_OPTS = {"--push-option", "--repo", "--receive-pack", "--exec"}


def check_git(args):
    """Block git push that rewrites or deletes remote history, wherever the flag is."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in GIT_VALUE_OPTS else 1
    if i >= len(args) or args[i] != "push":
        return
    rest, j = args[i + 1:], 0
    while j < len(rest):
        arg = rest[j]
        j += 1
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if name in PUSH_DANGER:
                bad = arg
            else:
                j += 1 if name in PUSH_VALUE_OPTS and "=" not in arg else 0
                continue
        elif arg.startswith("-") and len(arg) > 1:
            if "f" not in arg[1:] and "d" not in arg[1:]:
                j += 1 if arg.endswith("o") else 0  # -o <push option>
                continue
            bad = arg
        elif arg.startswith(("+", ":")):
            bad = arg  # +refspec forces, :ref deletes
        else:
            continue
        blocks.append(f"'git push ... {bad}' rewrites or deletes remote history. Push normally "
                      "(git push [-u] origin <branch>); never force-push or delete remote branches.")


def analyse(text, depth=0):
    toks = tokens(strip_heredocs(text))
    for tok in toks:
        if any(c.isspace() for c in tok):
            continue  # quoted text such as a commit message; `bash -c` scripts are analysed below
        for part in tok.split("="):
            name = base(part)
            if ENV_FILE.fullmatch(name) and name != ".env.example":
                blocks.append(f"'{part}' is a secrets file. Agents may not read or change .env files "
                              "(only .env.example); ask the user to check their own env file.")
    words = []
    for tok in toks + [";"]:
        if is_separator(tok):
            check_command(words, depth)
            words = []
        else:
            words.append(tok)


try:
    command = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
except Exception:
    sys.exit(0)
if isinstance(command, str):
    analyse(command)

if blocks:
    print("Blocked by .claude/hooks/guard-bash.sh:", file=sys.stderr)
    for msg in dict.fromkeys(blocks):
        print(f"- {msg}", file=sys.stderr)
    sys.exit(2)
if asks:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": " ".join(dict.fromkeys(asks)),
    }}))
sys.exit(0)
PY
)"
