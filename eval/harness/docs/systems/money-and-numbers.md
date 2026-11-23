---
name: money-and-numbers
title: Money and numbers
involvement: teach-me
owns:
  - 'src/money.ts'
  - 'src/cart.ts'
  - 'src/discounts.ts'
  - 'src/catalog.ts'
watch:
  - 'Math\.(round|floor|ceil|trunc)\('
  - 'parseFloat\(|toFixed\('
---

# Money and numbers

**Involvement:** Teach me. A wrong total is charged to a real card.
**The question:** is this amount right to the cent, for every input, and does it follow the spec?

## Invariants (always true)
- Every amount is whole cents. Rounding happens only in `src/money.ts` helpers.
- A total is never negative, and a discount never takes more than the subtotal.
- Tax is on the subtotal after discounts.
- Each figure has one implementation; a second copy will drift.

## Tripwires (changes that pull you in, even from a trusted area)
- New rounding outside `src/money.ts`, or a float conversion of an amount.

## How it breaks
- No incidents yet.

## Checks
- **Programs:** unit tests on each pure function, including zero, the smallest amount and a rounding
  boundary.
- **Reviewer:** where does each new amount come from? Which way does it round, and does the spec say
  so? What happens with several discounts or a zero price?

## Briefing
Teach me: the formula in words, a worked example, and the rounding.
