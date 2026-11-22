# Changelog

Each upgrade reads the entries after the version a project was set up from.

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
