---
name: state-and-timing
title: State and timing
involvement: keep-me-posted
owns:
  - 'src/orders.ts'
  - 'src/payments.ts'
watch:
  - '\bset(Timeout|Interval)\('
  - 'new (Mutex|Semaphore)\b|\.acquire\('
---

# State and timing

**Involvement:** Keep me posted; a tripwire raises it.
**The question:** what else can happen while this is waiting on the gateway?

## Invariants (always true)
- Two calls at once (a double click, a retry, two staff members) leave the same state as one after
  the other. A limit checked before an `await` still holds after it.
- A failed gateway call leaves no half-made change: stock, charges and refunds all agree.

## Tripwires (changes that pull you in, even from a trusted area)
- A new timer, lock or queue.

## How it breaks
- No incidents yet.

## Checks
- **Programs:** a test that starts two overlapping calls with the fake gateway's `delayMs`, and one
  with `failNext`.
- **Reviewer:** for each `await`: what can another call change meanwhile, and is every check made
  before it still true after?

## Briefing
Keep me posted: which actions changed, and what happens on overlap or failure.
