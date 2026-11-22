#!/bin/bash
# Runs the fast checks when a turn ends with code changed. A failure exits 2, which makes the agent
# fix it before finishing. It runs at the end of a turn rather than after each edit, because a
# multi-file change is often broken halfway through. Slow checks run before committing.

input=$(cat)

# Already continuing because of this hook: stop here so an unfixable failure can't loop forever.
if [ "$(printf '%s' "$input" | jq -r '.stop_hook_active // false')" = "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR" || exit 0

# ADAPT: skip if dependencies aren't installed, as in a new worktree.

changed=$(
  git diff --name-only HEAD 2>/dev/null
  git ls-files --others --exclude-standard 2>/dev/null
)
# ADAPT: the language pack's trigger pattern. Docs-only turns skip the checks.
if ! printf '%s\n' "$changed" | grep -qE '\.(ts|tsx|json)$'; then
  exit 0
fi

# ADAPT: the language pack's fast checks, one block each.
if ! output=$(npm test 2>&1); then
  printf 'Tests failed. Fix this before finishing:\n%s\n' "$output" | tail -60 >&2
  exit 2
fi

exit 0
