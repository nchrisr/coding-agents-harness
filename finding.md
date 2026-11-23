# Harness findings

A finding is how a lesson from one project reaches every project.

## In the project
When something slipped through, ask the session: "Should the harness have caught this? Write a
harness finding." It writes this, in chat or a scratch file, never committed to the project:

```markdown
# Harness finding: <short name>

**What happened:** <the bug or slowdown, in general terms>
**Why the harness missed it:** <which stage should have caught it, and why it didn't —
the wrong system, no card, no check, a rule in prose that a tool could have enforced>
**Proposed rule:** <the general rule, written so it fits any project>
**Where it goes:** <file in the harness repo: a card template, a language pack, a working rule…>
**Can a program check it?** <yes: which linter, test or hook; or no, and why>
```

**Strip the project out.** No code, names, file paths, customers or numbers that identify it. If the
lesson can't be stated without them, it's a project rule, not a harness rule: it goes in the project's
own `AGENTS.md` or card instead.

**Sort the lesson first.** Is it about *how the agent works* (how it checks, searches, plans, reviews
or verifies), true whatever the project builds? Then it's a harness finding. Is it *what an expert in
this subject knows* (how money is rounded here, what this framework expects)? Then it belongs in that
project's card or docs, even if it took a bug to learn it.

**Never include an unfixed security hole.** Fix it in the project first.

**A finding that proposes a tool, hook or rule** is tested first, following `evaluate.md`.

## In the harness repo
Bring the finding to a session here: "Turn this finding into a harness change." It edits the files,
bumps `VERSION`, adds a `CHANGELOG.md` line, and opens a pull request. The owner reviews that pull
request; projects pick it up on their next upgrade.
