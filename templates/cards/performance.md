---
name: performance
title: Performance
involvement: keep-me-posted
owns:
  - "<data loading, list pages, jobs>"
watch:
  - "for .* await"
  - "\.map\(async"
---

# Performance

**Involvement:** Keep me posted. Slow pages and jobs creep in as data grows.
**The question:** what happens to this when the data is a hundred times bigger?

## Invariants (always true)
- No query inside a loop over rows (N+1).
- Lists are paged or bounded.
- Slow work runs off the request path.

## Tripwires (changes that pull you in, even from a trusted area)
- <adapt to the project>

## How it breaks
- <the project's own incidents>

## Checks
- **Programs:** <tests, lint rules, guard tests>
- **Reviewer:** what happens to this when the data is a hundred times bigger?

## Briefing
<what the owner gets>
