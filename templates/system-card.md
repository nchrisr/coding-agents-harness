---
# One card per system. The frontmatter is read by scripts/systems-touched.sh; keep its shape.
name: <kebab-case-name>
title: <Plain name>
# teach-me | keep-me-posted | trust | coach
involvement: teach-me
# Files where this system's invariants live. Glob patterns, matched against changed paths (* also
# matches /). List those files, not whole folders, unless every file in the folder is in scope.
# A plain path must exist (scripts/doc-refs-check.py fails if it doesn't); a glob may match nothing yet.
owns:
  - '<path/or/glob>'
# Tripwires: patterns in a change's ADDED lines that pull it up to teach-me, wherever they appear.
# Match the code that CREATES the risky thing (the call that takes a lock, a new secret-key client),
# never a mention of it (the word "locked" in a message). Each pattern is tested at setup on one line
# that must trip it and one that must not. Write each in single quotes, so backslashes are literal.
watch:
  - '<regex>'
---

# <Plain name>

**Involvement:** <setting>, and why.
**The question this card asks of every change:** <one sentence>

## Invariants (always true)
- <something that must hold whatever the change>

## Tripwires (changes that pull you in, even from a trusted area)
- <a change that escalates to Teach me, in words; the `watch` patterns are the checkable part>

## How it breaks
Real failure modes, from past bugs where there are any. Keep the story short; the fix is in the code.
- <what went wrong, and how it showed>

## Checks
- **Programs:** <guard tests, lint rules, hook checks that enforce the invariants>
- **Reviewer:** <what a person or agent has to judge, as questions>

## Briefing
What the owner gets before merge (Teach me) or in the summary (Keep me posted).
Deep dive: <link to the architecture doc for this system>
