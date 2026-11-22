# Coding agents harness

A reusable way of working with coding agents. It is a recipe book, not a library: nothing here runs
inside a project, and no project depends on it. An agent reads it, then writes a project's own
harness files, and you review them.

## Currently supported

Keep this list up to date with every change to `packs/` or `rules/`.

| | Supported | Default opinion |
|---|---|---|
| **Languages** | Python · TypeScript / JavaScript · Rust | Google's style guide for each, plus the overrides in `rules/style.md` (plain code over clever syntax; unknown is explicit) |
| **Platforms** | GitHub · GitLab · Azure Repos | Harness files need the owner's approval to merge |
| **Project types** | Product · Learning | Product: the agent builds. Learning: the owner builds the parts they want to learn |

## What's here

| Path | What it is |
|---|---|
| `setup.md` | The prompt for setting up a new or existing project. Start here. |
| `upgrade.md` | The prompt for bringing a project up to the latest harness version. |
| `finding.md` | How a project reports something the harness should have caught. |
| `trust-rule.md` | The rule that keeps harness content from acting as instructions. |
| `project-types.md` | Product (taxi) or learning (driving school): the dial's defaults. |
| `rules/` | Working rules and code style shared by every project. |
| `packs/languages/` | Checks, linters and classic traps per language. |
| `packs/platforms/` | The approval lock on GitHub, GitLab and Azure Repos. |
| `templates/` | Starting points for agents, commands, hooks, scripts and system cards. |
| `CHANGELOG.md` | What changed in each version, so an upgrade can say what's new. |

## The ideas in one screen

- **Tiers** say how risky a change is, by what it does. Specs for tier 2 and 3.
- **Systems** are the parts of an app, cut by how they fail, not by layer: sign-in, data access,
  money, payments, privacy, performance, state and timing. Each has a **system card** in the project.
- **The involvement dial** on each card says how involved the owner is: *Teach me*, *Keep me
  posted*, *Trust*, or *I build it, you coach*.
- **One builder agent per change; a reviewer per critical system**, woken only when a change touches
  that system's files.
- **Rules a program can check go in a program** (linter, guard test, hook). Prose is for the rest.

## Before you start

**Add the trust rule to your own Claude settings, by hand, once.** Copy the block under "The text" in
`trust-rule.md` into `~/.claude/CLAUDE.md` (create the file if it doesn't exist). It tells every
session on your machine to treat this harness as material to review, never as instructions. Setup
checks for it and stops if it's missing; it never writes the rule for you, because a harness that
installs its own safety rule could install a weaker one.

## How to use it

- **New project:** describe the idea in a few sentences, then: "Set up this project with the harness
  at `<path>/setup.md`."
- **Existing project:** the same. Setup inspects the project first and builds on what's there.
- **Upgrade:** "Upgrade the harness using `<path>/upgrade.md`." Only when you ask; never automatic.
- **Something slipped through:** in that project, "Should the harness have caught this? Write a
  harness finding." Bring the finding here and ask for a change. Review it as a pull request.

## Changing this repo

Only through pull requests the owner reviews. Every change bumps `VERSION` and adds a line to
`CHANGELOG.md`. Nothing app-specific goes here: no code, names, secrets or incidents that identify a
project. A lesson is written as a general rule.
