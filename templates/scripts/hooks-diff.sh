#!/bin/bash
# Shows, word for word, every command that runs on its own in this project, before and after a
# change: agent hooks, their scripts, git hooks, and package install scripts. A reviewer pastes the
# output into the owner's briefing unchanged, so the owner reads the commands themselves, not a
# description of them.
#
# Usage: scripts/hooks-diff.sh [base-ref]     (default base: origin/main; set per project)
# Prints a unified diff, or "No changes to anything that runs on its own." Needs jq.

set -u
base="${1:-origin/main}"
root=$(git rev-parse --show-toplevel) || exit 1
cd "$root" || exit 1

# Files whose whole content runs: hook scripts and git hooks.
script_pattern='^(\.claude/hooks/|\.codex/hooks/|\.gemini/hooks/|\.husky/|\.githooks/)|^\.pre-commit-config\.ya?ml$'
# Files whose hook entries run: agent settings and package manifests.
settings_files='.claude/settings.json .codex/config.json .gemini/settings.json package.json'

# Prints a file's content at the base ref, or in the working tree when ref is "WORKTREE".
read_at() {
  if [ "$1" = "WORKTREE" ]; then
    cat "$2" 2>/dev/null
  else
    git show "$1:$2" 2>/dev/null
  fi
}

# Prints, one per line, every command that runs on its own, as of the given ref.
collect() {
  ref="$1"
  for file in $settings_files; do
    content=$(read_at "$ref" "$file")
    [ -n "$content" ] || continue
    if [ "$file" = "package.json" ]; then
      printf '%s' "$content" | jq -r '
        (.scripts // {}) | to_entries[]
        | select(.key | test("^(pre|post)?install$|^prepare$|^prepublish(Only)?$|^postpack$"))
        | "package.json script \(.key): \(.value)"' 2>/dev/null
    else
      printf '%s' "$content" | jq -r --arg f "$file" '
        (.hooks // {}) | to_entries[] | .key as $event
        | .value[] | (.matcher // "*") as $matcher
        | (.hooks // [])[] | "\($f) hook \($event) [\($matcher)]: \(.command // .prompt // "?")"' 2>/dev/null
    fi
  done

  if [ "$ref" = "WORKTREE" ]; then
    paths=$(git ls-files -co --exclude-standard | grep -E "$script_pattern")
  else
    paths=$(git ls-tree -r --name-only "$ref" | grep -E "$script_pattern")
  fi
  for path in $paths; do
    printf '=== %s\n' "$path"
    read_at "$ref" "$path"
    printf '\n'
  done
  # A hooks folder set in git's own config would run outside every list above.
  hooks_path=$(git config --get core.hooksPath)
  if [ -n "$hooks_path" ]; then
    printf 'git config core.hooksPath: %s\n' "$hooks_path"
  fi
}

before=$(collect "$base")
after=$(collect WORKTREE)
if [ "$before" = "$after" ]; then
  echo "No changes to anything that runs on its own."
  exit 0
fi
diff -u --label "before ($base)" --label "after (this change)" <(printf '%s\n' "$before") <(printf '%s\n' "$after")
exit 0
