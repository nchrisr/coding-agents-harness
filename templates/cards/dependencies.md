---
name: dependencies
title: Dependencies
involvement: teach-me
# Manifests and lock files. Adapt to the project's ecosystems.
owns:
  - 'package.json'
  - '*/package.json'
  - 'package-lock.json'
  - '*/package-lock.json'
  - 'pnpm-lock.yaml'
  - 'yarn.lock'
  - '.npmrc'
  - 'Cargo.toml'
  - '*/Cargo.toml'
  - 'Cargo.lock'
  - 'pyproject.toml'
  - 'uv.lock'
  - 'poetry.lock'
  - 'requirements*.txt'
watch:
  - 'ignore-scripts *= *false|onlyBuiltDependencies|trustedDependencies'
  - '--no-verify|--force|--legacy-peer-deps'
---

# Dependencies

**Involvement:** Teach me. Every package is code written by strangers that runs with your
permissions. A known-vulnerable version, a look-alike package, or a hijacked update can reach your
machine, your users or your secrets.
**The question:** what new code from outside does this change bring in, and do we trust it?

Think of a new package as a stranger asking to move into your house: check who they are before
handing over a key.

## Invariants (always true)
- The lock file is committed, and installs use the strict mode that refuses to change it
  (`npm ci`, `pnpm install --frozen-lockfile`, `cargo build --locked`, `uv sync --locked`).
- No change merges with a known high or critical vulnerability in a dependency it adds or upgrades,
  unless the owner accepts it in writing, with the reason and a date to revisit.
- Packages don't run install scripts, except the ones on the project's approved list.
- Every newly added package passes the stranger check below.

## The stranger check (for each newly added package)
`scripts/deps-check.sh` lists the new packages. For each, answer and report:
- **Name:** spelled exactly like the package you meant? (`reqeusts`, `lodahs` and `@scope`-less copies
  are classic traps.)
- **Age:** when was it first published? Under 90 days old is a flag.
- **Use:** weekly downloads, or dependents. Very low use is a flag.
- **Who:** the maintainers; a recent change of maintainer is a flag.
- **Install scripts:** does it, or anything it pulls in, run a script on install or build?
- **Need:** could the standard library or an existing dependency do this instead?
Where to look: npm `npm view <pkg> time.created maintainers scripts` and
`https://api.npmjs.org/downloads/point/last-week/<pkg>`; PyPI `https://pypi.org/pypi/<pkg>/json`;
crates.io `https://crates.io/api/v1/crates/<pkg>`.
Any flag goes to the owner as a question. None of this proves a package is safe; it catches the
common attacks.

## Tripwires (changes that pull you in, even from a trusted area)
- Turning install scripts back on, or adding to the approved list.
- Forcing an install past its checks (`--force`, `--legacy-peer-deps`, `--no-verify`).

## How it breaks
- <the project's own incidents>
- Supply-chain attacks are reported often: look-alike names, hijacked maintainer accounts, and
  install scripts that steal credentials.

## Checks
- **Programs:** `scripts/deps-check.sh <base>` runs the vulnerability scan (OSV-Scanner) and lists
  new and changed packages. On GitHub, Dependabot alerts and security updates watch weekly; elsewhere,
  a scheduled CI job runs the scan (see the platform pack).
- **Reviewer:** the stranger check for each new package; for each upgrade, is it a major version, and
  does its changelog mention security or breaking changes?

## Briefing
Teach me: the deps-check output unchanged, then the stranger check per new package in one line each,
and any vulnerability with its severity and fix version.
