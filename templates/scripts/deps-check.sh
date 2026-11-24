#!/bin/bash
# Shows what outside code a change brings in, and whether any dependency has a known vulnerability.
#   1. Direct dependencies added, removed or changed since the base, per manifest.
#   2. Every locked package added or changed since the base (the full tree, from the lock files).
#   3. A known-vulnerability scan of the lock files with OSV-Scanner (https://google.github.io/osv-scanner/).
# The reviewer pastes the output into the owner's briefing unchanged, then runs the stranger check
# (docs/systems/dependencies.md) on each newly added package.
#
# Usage: scripts/deps-check.sh [--exclude <path>]... [base-ref]     (default base: see below)
# Each --exclude path, from the repo root, is left out of the untracked files it reads.
# Needs jq for npm projects. Reaches the network only for the vulnerability scan.

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

# Prints a file at the base ref, or in the working tree when ref is "WORKTREE".
read_at() {
  if [ "$1" = "WORKTREE" ]; then
    cat "$2" 2>/dev/null
  else
    git show "$1:$2" 2>/dev/null
  fi
}

tracked_and_new() {
  git ls-files -co --exclude-standard -- . ${skip[@]+"${skip[@]}"} | grep -E "$1" | grep -v '/node_modules/'
}

# "name version" for each direct dependency in a manifest.
direct_deps() {
  case "$2" in
    *package.json)
      read_at "$1" "$2" | jq -r '
        [(.dependencies // {}), (.devDependencies // {}), (.optionalDependencies // {})]
        | add // {} | to_entries[] | "\(.key) \(.value)"' 2>/dev/null ;;
    *Cargo.toml)
      read_at "$1" "$2" | awk '
        /^\[/ { inside = ($0 ~ /dependencies\]$/) ; next }
        inside && /^[A-Za-z0-9_-]+ *=/ { split($0, a, "="); gsub(/ /, "", a[1]); v = $0; sub(/^[^=]*= */, "", v); print a[1], v }' ;;
    *requirements*.txt)
      read_at "$1" "$2" | grep -vE '^\s*(#|-|$)' | sed 's/[[:space:]]*#.*//' ;;
    *pyproject.toml)
      read_at "$1" "$2" | awk '
        /^dependencies *= *\[/ { inside = 1; next }
        inside && /^\]/ { inside = 0 }
        inside { gsub(/[",]/, ""); gsub(/^ +| +$/, ""); if ($0 != "") print }' ;;
  esac
}

# "name@version" for every package in a lock file.
locked_packages() {
  case "$2" in
    *package-lock.json)
      read_at "$1" "$2" | jq -r '
        (.packages // {}) | to_entries[] | select(.key != "")
        | "\(.key | sub(".*node_modules/"; ""))@\(.value.version)"' 2>/dev/null ;;
    *Cargo.lock|*uv.lock|*poetry.lock)
      read_at "$1" "$2" | awk '
        /^name = / { gsub(/"/, "", $3); name = $3 }
        /^version = / { gsub(/"/, "", $3); if (name != "") print name "@" $3; name = "" }' ;;
    *pnpm-lock.yaml)
      read_at "$1" "$2" | grep -E "^  '?/?[^ ]+@[0-9][^:]*'?:$" | sed -E "s/^  '?\/?//; s/'?:$//" ;;
  esac
}

compare() {
  diff <(printf '%s\n' "$1" | sort -u) <(printf '%s\n' "$2" | sort -u) | grep -E '^[<>]' |
    sed -e 's/^< /  - removed: /' -e 's/^> /  + added or changed: /'
}

echo "== Direct dependencies (since $base)"
found=0
# Read line by line, so a path with a space stays one path.
while IFS= read -r manifest; do
  [ -n "$manifest" ] || continue
  changes=$(compare "$(direct_deps "$base" "$manifest")" "$(direct_deps WORKTREE "$manifest")")
  if [ -n "$changes" ]; then
    found=1
    echo "$manifest"
    echo "$changes"
  fi
done < <(tracked_and_new '(^|/)(package\.json|Cargo\.toml|pyproject\.toml|requirements[^/]*\.txt)$')
[ "$found" = 1 ] || echo "  no changes"

echo
echo "== Locked packages, full tree (since $base)"
found=0
while IFS= read -r lockfile; do
  [ -n "$lockfile" ] || continue
  changes=$(compare "$(locked_packages "$base" "$lockfile")" "$(locked_packages WORKTREE "$lockfile")")
  if [ -n "$changes" ]; then
    found=1
    count=$(printf '%s\n' "$changes" | grep -c 'added or changed')
    echo "$lockfile ($count added or changed)"
    echo "$changes" | head -60
  fi
done < <(tracked_and_new '(^|/)(package-lock\.json|pnpm-lock\.yaml|Cargo\.lock|uv\.lock|poetry\.lock)$')
[ "$found" = 1 ] || echo "  no changes"

echo
echo "== Known vulnerabilities (OSV-Scanner)"
if ! command -v osv-scanner >/dev/null 2>&1; then
  echo "  NOT RUN: osv-scanner isn't installed. Install it (macOS: brew install osv-scanner;"
  echo "  others: https://google.github.io/osv-scanner/installation/) and run this again."
  exit 0
fi
# Scan each lock file by name. Walking the folder (--recursive .) skips whatever .gitignore ignores,
# so inside an agent's worktree under an ignored folder (.claude/worktrees/...) it scans nothing.
lockfiles=()
while IFS= read -r lockfile; do
  lockfiles+=("-L" "$lockfile")
done < <(tracked_and_new '(^|/)(package-lock\.json|npm-shrinkwrap\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lock|Cargo\.lock|uv\.lock|poetry\.lock|Pipfile\.lock|pdm\.lock|requirements[^/]*\.txt|go\.mod|Gemfile\.lock|composer\.lock|pubspec\.lock|mix\.lock|gradle\.lockfile|pom\.xml|packages\.lock\.json)$')
if [ "${#lockfiles[@]}" = 0 ]; then
  echo "  nothing to scan: no lock file in this project."
  exit 0
fi
printf '  scanning:'; printf ' %s' "${lockfiles[@]}" | sed 's/ -L//g'; echo
if osv-scanner scan --help >/dev/null 2>&1; then
  output=$(osv-scanner scan source "${lockfiles[@]}" 2>&1)
else
  output=$(osv-scanner "${lockfiles[@]}" 2>&1)
fi
status=$?
# Exit codes: 0 no vulnerabilities, 1 some found, 127 an error, 128 no packages found.
if [ "$status" -gt 1 ] || printf '%s\n' "$output" | grep -qi 'no package sources found'; then
  echo "  NOT RUN: the project has lock files, but OSV-Scanner did not scan them (exit $status)."
  echo "  This is not a clean result. Its output:"
  printf '%s\n' "$output" | tail -20 | sed 's/^/    /'
  exit 0
fi
printf '%s\n' "$output" | tail -80
exit 0
