---
name: sign-in-and-access
title: Sign-in and access
involvement: teach-me
owns:
  - 'src/access.ts'
  - 'src/users.ts'
watch:
  - '\.role ?[!=]==? ?.(admin|staff).'
  - 'canViewOrder\(|canRefund\('
---

# Sign-in and access

**Involvement:** Teach me. A mistake here lets someone see or refund what they shouldn't.
**The question:** who can do this, and what checks them?

## Invariants (always true)
- Every action that reads or changes an order checks access through `src/access.ts`.
- Access fails closed: unknown user, unknown order or an error means no.
- Seeing an order never implies the right to change it.

## Tripwires (changes that pull you in, even from a trusted area)
- A new role check outside `src/access.ts`, or a new caller of an access check.

## How it breaks
- No incidents yet.

## Checks
- **Programs:** a test per role (customer, other customer, staff, admin) for each new action.
- **Reviewer:** for each new action: who can call it, what does another customer get, and what does an
  error path return?

## Briefing
Teach me: what changed in who can do what, and two or three ways it could fail.
