#!/bin/bash
# Lists the system cards a change touches, so the review loop knows which system reviewers to wake.
#
# Usage: scripts/systems-touched.sh [--exclude <path>]... [base-ref]
#        (default base: see below)
# Output, one line per touched card:  <card path><TAB><involvement><TAB><why>
# A card is touched when a changed path matches one of its `owns` globs, or when an added line
# matches one of its `watch` patterns (a tripwire, which raises it to teach-me).
# Covers committed, uncommitted and untracked changes since the base, apart from each --exclude path
# (a file or folder that isn't part of the change, such as the owner's untracked notes), given from
# the repo root. The untracked
# files it counted go to stderr, so the agent can spot one it didn't write.

set -u
skip=()
base_arg=""
while [ $# -gt 0 ]; do
  case "$1" in
    --exclude) [ -n "${2:-}" ] || { echo "--exclude needs a path" >&2; exit 1; }
               skip+=(":(exclude)$2"); shift 2 ;;
    -*) echo "Unknown option: $1" >&2; exit 1 ;;
    *) [ -z "$base_arg" ] || { echo "One base only, not both $base_arg and $1" >&2; exit 1; }
       base_arg=$1; shift ;;
  esac
done
cards_dir="${CARDS_DIR:-docs/systems}"
root=$(git rev-parse --show-toplevel) || exit 1
cd "$root" || exit 1

# The base: the argument if given, else where this branch left the remote's default branch, so work
# that landed there since doesn't count as this change's. Printed on stderr for the review loop.
if [ -n "$base_arg" ]; then
  base=$base_arg
else
  default=$(git symbolic-ref -q --short refs/remotes/origin/HEAD) || {
    echo "Don't know origin's default branch. Run: git remote set-head origin --auto (or pass a base)" >&2
    exit 1; }
  fork=$(git merge-base "$default" HEAD 2>/dev/null) || {
    echo "No shared history with $default here (a shallow clone?). Pass a base." >&2; exit 1; }
  base=$(git rev-parse --short "$fork")
  echo "base: $base, where this branch left $default" >&2
fi

untracked=$(git ls-files --others --exclude-standard -- . ${skip[@]+"${skip[@]}"})
[ -n "$untracked" ] && printf '%s\n' "$untracked" | sed 's/^/untracked, counted: /' >&2
changed=$( { git diff --name-only "$base" -- . ${skip[@]+"${skip[@]}"}; printf '%s\n' "$untracked"; } \
  | sed '/^$/d' | sort -u)
# Tripwires look at code, not prose: Markdown is left out, so the cards don't trip themselves.
added=$( { git diff "$base" -- . ':(exclude)*.md' ${skip[@]+"${skip[@]}"} | grep -E '^\+[^+]'; \
  git ls-files --others --exclude-standard -z -- . ':(exclude)*.md' ${skip[@]+"${skip[@]}"} \
  | xargs -0 cat 2>/dev/null; } )

# Reads one list from a card's frontmatter: the lines "  - ..." under "<key>:". Write each item in
# single quotes, so a regex's backslashes are taken literally.
read_list() {
  awk -v key="$1:" '
    NR == 1 && $0 == "---" { inside = 1; next }
    inside && $0 == "---" { exit }
    inside && $0 == key { grab = 1; next }
    inside && grab && /^  - / { sub(/^  - /, ""); gsub(/^[\047"]|[\047"]$/, ""); print; next }
    inside && grab { grab = 0 }
  ' "$2"
}

for card in "$cards_dir"/*.md; do
  [ -f "$card" ] || continue
  involvement=$(awk '/^involvement:/ { print $2; exit }' "$card")
  [ -n "$involvement" ] || continue
  why=""

  owned=""
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    while IFS= read -r pattern; do
      [ -n "$pattern" ] || continue
      # In [[ == ]], * matches across /, so "app/*/actions.ts" covers nested folders too.
      if [[ "$file" == $pattern ]]; then
        owned="${owned:+$owned, }$file"
        break
      fi
    done < <(read_list owns "$card")
  done <<< "$changed"
  [ -n "$owned" ] && why="owns $owned"

  while IFS= read -r pattern; do
    [ -n "$pattern" ] || continue
    if printf '%s\n' "$added" | grep -qE -- "$pattern"; then
      involvement="teach-me"
      why="${why:+$why; }tripwire /$pattern/"
      break
    fi
  done < <(read_list watch "$card")

  [ -n "$why" ] && printf '%s\t%s\t%s\n' "$card" "$involvement" "$why"
done
exit 0
