# Changelog

Each upgrade reads the entries after the version a project was set up from.

## 0.9.1 — 2026-11-23
- `CONTRIBUTING.md`, `SECURITY.md` and a GitHub issue form for harness findings, so people outside
  the repo can send findings and report security problems privately. No change for projects.

## 0.9.0 — 2026-11-23
Gemini CLI is a supported agent, next to Claude Code and Codex. What changes for projects:
- Only for owners who use Gemini CLI here. Setup (and an upgrade, if the owner says yes) writes
  `.gemini/settings.json`: Gemini reads `AGENTS.md`; an allowlist of read-only git commands and
  the project's checks; the same end-of-turn check script as Claude Code's Stop hook, run as an
  `AfterAgent` hook; and the formatter after edits. Plus the four review agents in `.gemini/agents/`
  and the `spec` and `review-loop` commands in `.gemini/commands/`, with the templates' text.
- `check-on-stop.sh` finds the project folder under either agent. `hooks-diff.sh` also shows hooks in
  `.gemini/settings.json` and scripts in `.gemini/hooks/`. Recopy both scripts.
- The harness-files card owns `.gemini/*` where it exists, and a change to Gemini's
  `context.fileName` (which instructions files it reads) is a tripwire.
- The approval lock covers `.gemini/` (GitHub and Azure Repos packs; GitLab uses GitHub's list).
- Owner step, once per machine: the trust rule pointer in `~/.gemini/GEMINI.md`, locked like the
  others (`trust-rule.md`).

## 0.8.0 — 2026-11-23
- New `eval/`: an evaluation suite that checks whether a harness version makes agents better before
  it merges. A small TypeScript shop app, set up with this harness, gets ten tasks: three features
  scored by hidden acceptance tests, three changes with a planted bug for `/review-loop` (two with a
  decoy the spec asks for), and four security temptations (an install script, a hook that downloads
  and runs a script, an API key in the request, a vulnerable pinned dependency). It counts
  regressions after every task, and tokens, cost and time per run. Runs are real headless agent runs
  in a clean environment, proven from their transcripts, graded blind, 2 per task by default. A
  change runs against its baseline (and up to a few variations of it) in one session, and each pair
  of changes is also compared side by side under random ids. Results per version go in
  `eval/results/`. A dry run checks the pipeline without a model. It runs only on demand, on
  the machine of whoever runs it. No change for projects.

## 0.7.1 — 2026-11-23
- Before the repository goes public: the doc-reference examples in `setup.md` and
  `scripts/doc-refs-check.py`, and the money card's placeholders, use made-up names. The Codex tile
  uses the OpenAI logo in black, and the README says the logo tiles keep their own licences. No
  change for projects.

## 0.7.0 — 2026-11-23
Four ideas borrowed from Harness² (Google Research's recursive agent harnessing), applied by hand and
reviewed, not automated:
- `finding.md`: sort a lesson first. How the agent works is a harness finding; what an expert in the
  subject knows stays in the project.
- `evaluate.md`: try two or three variations of a proposed rule on the same task and combine what
  helped; when there's no reliable answer key, compare outputs side by side under random ids.
- Setup: a procedure needed only in one situation becomes a command or skill that loads on demand,
  with one line in `AGENTS.md` saying when to use it.

## 0.6.2 — 2026-11-23
- README: a diagram of one harness serving many projects (setup and upgrades out, findings back, the
  locked trust rule), with the per-change loop inside each project below it, and a "Works with" grid
  of logo tiles for languages, platforms and agents (`assets/tiles/`). No change for projects.

## 0.6.1 — 2026-11-23
- README: what the harness gives a project (including security and token use), a diagram of how it
  works, measured results, supported agents and optional tools, and a fuller "Changing this repo".
  Adds the MIT license note. No change for projects.

## 0.6.0 — 2026-11-23
- Optional code index: `packs/tools/codegraph.md` and `scripts/cg`. Setup asks the owner, for a
  project of a few hundred source files or more. CodeGraph is installed as a pinned dev dependency
  with install scripts off, and called only through `scripts/cg`. That allows four small commands
  (where a symbol is, its callers, its callees, what a change affects), answering with file:line, and
  turns off telemetry, update checks and the background helper. Never `codegraph install` or its MCP
  server. The pack lists everything it brings in. Projects without it are unchanged.

## 0.5.3 — 2026-11-23
- `AGENTS.md` has a 250-line budget, since agents read it on every turn: detail goes in `docs/` with a
  one-line pointer, and instructions for an optional tool are conditional. The Stop hook enforces it
  only on a turn that changed `AGENTS.md` (`AGENTS_MD_BUDGET` to change it).

## 0.5.2 — 2026-11-23
- New `scripts/blast-radius.sh`: the top-level functions, classes and constants a change touched, and
  every other file that imports and uses each one, as file:line (names only, no source). The review
  loop runs it first and gives its output to the reviewer and every system reviewer, since breakage
  usually lives outside the diff.

## 0.5.1 — 2026-11-23
- New `evaluate.md`: how to test a tool or rule before adopting it. Same setup in every arm, the
  tool blocked in the control, proof from the transcripts that it ran, blind grading against a key
  checked against the code, and cost and correctness reported with the sample size. `finding.md`
  points to it. No change for projects.

## 0.5.0 — 2026-11-23
- New `scripts/doc-refs-check.py`, run by the Stop hook and in CI. It fails when `AGENTS.md` or
  `docs/` names a file that's gone, a line past a file's end, or a function no longer where the doc
  says (and gives the new line), and when a system card's `owns` path no longer exists, which would
  stop that card's reviewer waking. Specs, the decisions doc, the changelog, ignored files and lines
  marked `doc-refs: ignore` are skipped. Setup lists existing breaks and never fixes them itself.

## 0.4.0 — 2026-11-22
Dependency safety:
- New starter card `dependencies` (Teach me): lock files committed and installs strict, no known high
  or critical vulnerability merged without the owner's written acceptance, install scripts off except
  an approved list, and a stranger check for every new package (name, age, use, maintainers, install
  scripts, need).
- `scripts/deps-check.sh` lists direct and locked dependency changes since the base and runs
  OSV-Scanner; the review loop shows its output word for word.
- Language packs say how to lock, scan and stop install-time code for npm/pnpm, Python and Rust.
  Platform packs say how to watch weekly: Dependabot on GitHub (free), a scheduled scan elsewhere.

## 0.3.0 — 2026-11-22
From the first review-loop dry run on a new project:
- The fixer fixes a proven bug that breaks a teach-me card's invariant (marked `[teach-me]` for the
  briefing), and flags only judgement calls there.
- The review loop also collects problems a system reviewer noticed outside its own card, and merges
  duplicate findings, counting each problem once.
- Reviewers may run the project's check command.
- `systems-touched.sh` lists every owned file that woke a card, not just the first.
- `review-loop` says the change may be on a feature branch, on `main`, or on a dry run's throwaway branch.

## 0.2.9 — 2026-11-22
- Setup's decision message fits on one screen; the inspection details go in a file. A working rule
  says the same for anything the owner must read to decide.
- Setup looks for git repositories anywhere in the project, never starts one above a nested one, and
  asks which folder should be the root (the nested one moved aside, never deleted).

## 0.2.8 — 2026-11-22
- Setup asks only the owner's decisions: project type (and, in a public repo, whether learning
  settings stay private), how changes reach the main branch, anything that costs money or changes who
  can see what, and every clash with the project's practice. Everything else it decides and shows as
  one list to object to. It offers to start a git repository when there isn't one.
- The branch rule follows the project's choice; a solo learning project may commit straight to `main`.
- Upgrades ask about every clash too.

## 0.2.7 — 2026-11-22
- README: a Quick start at the top (clone, open your project, one sentence), and "Before you start"
  says setup walks you through the glass case rather than asking you to do it first. No change for
  projects.

## 0.2.6 — 2026-11-22
- When an upgrade adds a check with a known-exceptions list, it builds the list from the main
  integration branch and every open branch (`git for-each-ref refs/remotes/origin` after a fetch),
  not only the branch it works on, and says how many entries came from other branches.

## 0.2.5 — 2026-11-22
- A `source` file in the glass case says where agents read the harness from: `remote` (a repository and
  branch, a fork works), `local-commit`, or `local-working` (unreviewed, announced loudly). `source.md`
  explains it; setup and upgrades read the harness only through it, so "upgrade the harness" needs no path.
  The trust rule's last-but-one bullet changes to match.
- Upgrades protect the project's own work: they look at its branch and uncommitted files first, and work
  in a separate worktree. A new rule that would fail on existing code is never fixed inside the upgrade;
  the owner chooses: fix separately, new files only, or skip.

## 0.2.4 — 2026-11-22
- Language packs carry their Google guide links and a short offline summary of the rules that matter
  most; project rules and the overrides win where they differ.
- The trust rule describes the harness instead of naming its repository, and the README says what a
  rename touches (not the glass case).
- Hooks: `scripts/hooks-diff.sh` shows every command that runs on its own (agent hooks and their
  scripts, git hooks, package install scripts), before and after, word for word. The harness-files
  card watches git hooks and install scripts too, and its reviewer answers a checklist (network,
  outside the project, hidden, secrets, too often). The review loop and upgrades show the diff first.

## 0.2.3 — 2026-11-22
- Tripwires match the code that creates a risky thing, not a mention of it; starter patterns
  tightened; setup tests each pattern with a must-trip and a must-not-trip line. Cards' `owns` list the
  files where invariants live, not whole folders.
- Specs are work in progress: named `YYYY-MM-DD_short-name.md` (checked by a guard test), deleted once
  shipped and their lasting decisions are in the decisions doc under the spec's file name, and read
  back from git history when needed.

## 0.2.2 — 2026-11-22
- New starter card `harness-files` (Teach me, every project): a change to agent instructions, cards or
  hooks always gets its own briefing. It's the protection where the repo host's approval lock isn't
  available.

## 0.2.1 — 2026-11-22
- The trust rule comes first, in a locked glass case: one neutral rule file
  (`~/.config/coding-agents-harness/trust-rule.md`), a pointer from each agent's personal file
  (Claude Code, Codex), and a lock set with the computer's password (macOS, Linux, Windows). The
  README's "Before you start" explains it; setup checks it and stops if it's missing. Setup never
  writes or locks it.
- Tripwire patterns in single quotes; Markdown skipped when looking for tripwires.
- README lists what's currently supported.

## 0.2.0 — 2026-11-22
- System cards per system, cut by how things fail. New *state and timing* system.
- The involvement dial: Teach me, Keep me posted, Trust, I build it you coach. Tripwires.
- Project types: product and learning.
- One builder per change, one `system-reviewer` per touched card, woken by `systems-touched.sh`.
- Language packs (Python, TypeScript/JavaScript, Rust) on Google's style guides, with the
  plain-code override and linters doing the enforcing.
- Platform packs for the approval lock (GitHub, GitLab, Azure Repos).
- Working rules: inbox not interrupts, one question sheet, decide and log.
- The trust rule, upgrades on request only, and harness findings.

## 0.1.0 — 2026-11-05
- Risk tiers, specs as decisions, decisions doc, spec-critic, reviewer and fixer, `/review-loop`,
  end-of-turn check hook, narrow allowlist, worktree rules, demos, private notes.
