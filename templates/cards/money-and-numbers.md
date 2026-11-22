---
name: money-and-numbers
title: Money and numbers
involvement: teach-me
owns:
  - '<valuation, pricing, totals, formatting of amounts>'
watch:
  - 'avg_cost|price|amount|total|balance'
---

# Money and numbers

**Involvement:** Teach me. A wrong figure is trusted; a leaked one can't be taken back.
**The question:** is this number right, is it honest about what's unknown, and who can see it?

## Invariants (always true)
- Unknown is `null`, never `0` and never a stand-in value. Unknowns are left out of totals and shown
  as unknown.
- Each figure has one implementation. A second copy will drift.
- Who sees which figure is decided on the server, by building a different data shape, not by hiding
  it in the view.
- Rounding happens at the edges, with named helpers.

## Tripwires (changes that pull you in, even from a trusted area)
- A new figure shown to a new audience.
- A new prop or response field carrying an amount to a browser.

## How it breaks
- <the project's own incidents>

## Checks
- **Programs:** unit tests on the pure functions, including the unknown case; guard tests that the one
  implementation is the only one.
- **Reviewer:** where does each new number come from, what happens when an input is unknown, and
  which browsers receive it?

## Briefing
Teach me: the formula in words, the unknown case, and who can see it.
