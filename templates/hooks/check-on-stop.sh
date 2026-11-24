#!/bin/bash
# Runs the fast checks when a turn ends with code changed. A failure exits 2, which makes the agent
# fix it before finishing. It runs at the end of a turn rather than after each edit, because a
# multi-file change is often broken halfway through. Slow checks run before committing.
# Claude Code runs it as a Stop hook, Gemini CLI as an AfterAgent hook: both pass stop_hook_active
# and read exit 2 as "keep working". Messages go to stderr only; Gemini reads stdout as JSON.

input=$(cat)

# Already continuing because of this hook: stop here so an unfixable failure can't loop forever.
if [ "$(printf '%s' "$input" | jq -r '.stop_hook_active // false')" = "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$GEMINI_PROJECT_DIR}" || exit 0

# ADAPT: skip if dependencies aren't installed, as in a new worktree.

# ADAPT: folders that hold the owner's local-only code: git-ignored, never committed, never seen by
# CI (asked at setup), such as (notes scratch). Empty means every failure stops the turn.
local_only=()

# A failed check stops the turn, unless every path its output names is a git-ignored file inside one
# of those folders. That is reported to the owner instead, and the other checks still run. Any other
# path (tracked code, node_modules, build output, one it can't find) stops the turn.
notes=""
failed() {
  local paths f d n=0 all_local=1 shown=""
  paths=$(printf '%s\n' "$2" | grep -oE '[A-Za-z0-9_.@-]*/[A-Za-z0-9_./@-]+\.[A-Za-z0-9]+' | sort -u)
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    n=$((n + 1)); f="${f#"$PWD"/}"; shown="$shown$f "
    inside=0
    for d in ${local_only[@]+"${local_only[@]}"}; do
      case "$f" in "${d%/}"/*) inside=1 ;; esac
    done
    if [ "$inside" = 0 ] || [ ! -f "$f" ] || ! git check-ignore -q "$f"; then all_local=0; fi
  done <<< "$paths"
  if [ "$n" -gt 0 ] && [ "$all_local" = 1 ]; then
    notes="${notes}$1 failed only in local-only files, which CI never sees: ${shown% }. Fix them, or leave those folders out of the project's checker configs. "
    return
  fi
  printf '%s failed. Fix this before finishing:\n%s\n' "$1" "$2" | tail -60 >&2
  exit 2
}

changed=$(
  git diff --name-only HEAD 2>/dev/null
  git ls-files --others --exclude-standard 2>/dev/null
)
# Docs can break from either side: a renamed function breaks a doc, and so does a doc edit. Fast, so
# it runs on any change. Warnings don't stop the turn; broken references do.
if [ -n "$changed" ] && [ -f scripts/doc-refs-check.py ]; then
  if ! output=$(python3 scripts/doc-refs-check.py 2>&1); then
    printf 'A doc points at code that has moved or gone. Fix the doc before finishing:\n%s\n' \
      "$output" | tail -40 >&2
    exit 2
  fi
fi

# AGENTS.md is read on every turn of every session, so it has a size budget. Checked only when this
# turn changed it, so it never blocks unrelated work.
budget="${AGENTS_MD_BUDGET:-250}"
if printf '%s\n' "$changed" | grep -qx 'AGENTS.md' && [ "$(wc -l < AGENTS.md)" -gt "$budget" ]; then
  printf 'AGENTS.md is %s lines, over its %s-line budget. Move detail into docs/ and leave a\n' \
    "$(wc -l < AGENTS.md | tr -d ' ')" "$budget" >&2
  printf 'one-line pointer saying when to read it.\n' >&2
  exit 2
fi

# ADAPT: the language pack's trigger pattern. Docs-only turns skip the checks.
if ! printf '%s\n' "$changed" | grep -qE '\.(ts|tsx|json)$'; then
  exit 0
fi

# ADAPT: the language pack's fast checks, one line each.
output=$(npm test 2>&1) || failed Tests "$output"

# Shown to the owner, without stopping the turn. Both agents read this field from stdout.
if [ -n "$notes" ]; then
  jq -n --arg m "$notes" '{systemMessage: $m}' 2>/dev/null || printf '%s\n' "$notes" >&2
fi
exit 0
