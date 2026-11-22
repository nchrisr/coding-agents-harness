---
name: data-and-schema
title: Data and schema
involvement: teach-me
owns:
  - '<migrations folder>'
watch:
  - 'DROP (COLUMN|TABLE|POLICY|FUNCTION)'
  - '(CREATE|ALTER) POLICY|DISABLE ROW LEVEL SECURITY'
  - 'DELETE FROM|TRUNCATE'
---

# Data and schema

**Involvement:** Teach me. Lost data, or code and schema that disagree during a deploy.
**The question:** can the running code and the database disagree, and can anything be lost?

## Invariants (always true)
- Never drop or rename a column in the same change that adds its replacement: expand, ship the code, then contract.
- Migrations are append-only once run.
- Every write's result is checked; a write that silently does nothing is an error where it matters.

## Tripwires (changes that pull you in, even from a trusted area)
- <adapt to the project>

## How it breaks
- <the project's own incidents>

## Checks
- **Programs:** <tests, lint rules, guard tests>
- **Reviewer:** can the running code and the database disagree, and can anything be lost?

## Briefing
<what the owner gets>
