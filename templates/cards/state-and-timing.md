---
name: state-and-timing
title: State and timing
involvement: keep-me-posted
owns:
  - '<every file with a user action, e.g. **/actions.ts, **/handlers/*>'
  - '<background jobs, queues, cron routes, sync code>'
watch:
  - 'setTimeout|setInterval'
  - 'lock|mutex|semaphore|advisory'
---

# State and timing

**Involvement:** Keep me posted. Bugs here are visible and confusing rather than dangerous; a
tripwire raises it when locks or jobs change.
**The question:** what can the user, or the server, do while this is still running?
Like an elevator: the door button doesn't work while it moves, and two people pressing different
floors don't confuse it.

## Invariants (always true)
- Every action has visible states: idle · working · done · failed · busy, try again shortly.
- While a save is in flight, nothing else on the page that writes can be used. Disabling only the
  submit button isn't enough: cover the page, or disable every writing control.
- Two writers on the same thing (a job and a user, two tabs, a double click) are expected. The loser
  gets a calm message saying what to do, never a red error.
- An action that's retried or double-clicked applies once.

## Tripwires (changes that pull you in, even from a trusted area)
- A new lock, background job or queue, or a new action writing rows an existing one writes.
- Any "busy" outcome reported as an error.

## How it breaks
- Controls left live during a save; a second click raced the first and wrote stale data.
- A user's save overlapped a background sync; the expected "busy" answer was shown as a failure.

## Checks
- **Programs:** a UI test per new action: start it, use every other writing control while it's
  pending, assert nothing changed and the message is calm.
- **Reviewer:** for each action in the diff — what if it's clicked twice? What if a job is running?
  What does the user see in each state? Is "busy" told apart from "failed"?

## Briefing
Keep me posted: which actions were added or changed, their states, and what happens on overlap.
