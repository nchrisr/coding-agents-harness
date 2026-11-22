# Changelog

Each upgrade reads the entries after the version a project was set up from.

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
