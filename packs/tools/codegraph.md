# CodeGraph pack (optional)

**What it is:** CodeGraph (https://github.com/colbymchenry/codegraph, MIT) parses the project into a
local SQLite index of every function, class, import and call. Agents ask it where something is, who
calls it, and what a change affects, instead of searching file by file.

**When to offer it:** at setup or upgrade, for a project of a few hundred source files or more, as a
choice the owner makes. It's optional: without it, nothing in the harness changes.

**Why this way:** in an A/B test on a ~480-file TypeScript project (5 questions, 2 runs per arm, graded
blind), its default MCP tool cut tool calls by half and was the fastest, but cost the same as no
index, because it answers with whole blocks of source. Its small commands, which answer with names and
file:line, cost 17% less at the same score. So this pack uses only those. See `evaluate.md` for how
it was tested.

## How it's set up
- **Pinned dev dependency,** never global: `npm install --save-dev --ignore-scripts
  @colbymchenry/codegraph@<version>`. Verify it with `npm audit signatures` (npm 10 or newer; older
  npm misreads its attestations). The `dependencies` card's stranger check applies, and so does every
  upgrade of it. Projects without `package.json` keep it in a tools folder of their own, with its own
  lock file.
- **Never run `codegraph install`.** It writes into the agent's personal instructions file, adds
  auto-approve permissions, and adds a prompt hook, for every project on the machine. Don't add its
  MCP server either.
- **`scripts/cg`** from the template: the only way agents call it. It allows four commands (`query`,
  `callers`, `callees`, `impact`), turns off telemetry, update checks and the background helper, and
  syncs the index before each answer.
- **The index:** `node_modules/.bin/codegraph init --yes`, run by the owner. It writes `.codegraph/`,
  which ignores itself in git. Rebuild it any time with `codegraph index`.
- **In `AGENTS.md`,** a short, conditional note: "If `.codegraph/` exists, find code with
  `scripts/cg query|callers|callees|impact <symbol>` before searching; it answers with file:line.
  Then read only the lines you need."
- **Allowlist:** `Bash(scripts/cg:*)` in `.claude/settings.json`.

## What it brings in (version 1.6.4, checked 2026-11-23)
- `@colbymchenry/codegraph` plus one platform package. No dependencies of their own outside the
  bundle, and no install scripts.
- The platform package bundles its own Node (v24), a compiled Rust engine (`codegraph-kernel.node`),
  and 10 packages: `commander`, `fast-string-truncated-width`, `fast-string-width`, `fast-wrap-ansi`,
  `ignore`, `jsonc-parser`, `picomatch`, `sisteransi` and `web-tree-sitter` (MIT), and
  `tree-sitter-wasms` (Unlicense). None has an install script. About 200 MB on disk.
- Its network use, all off in `scripts/cg`: anonymous usage counts, on by default; a daily check for
  a new version; an opt-in waitlist prompt in `codegraph install`, which this pack never runs.

## Limits
- Repositories under 500 files: its MCP server hides `callers` and `impact`. The command line isn't
  affected. Reported upstream as issue #3462.
- Resolving calls across files is best-effort name matching; a common name can return extra matches.
- On an index kept up to date incrementally, the maintainers measured about 4% of links drifting from
  a full rebuild. Rebuild with `codegraph index` if answers look wrong.

## Removing it
`npm uninstall @colbymchenry/codegraph`, delete `.codegraph/` and `scripts/cg`, and remove the
`AGENTS.md` note and the allowlist entry.
