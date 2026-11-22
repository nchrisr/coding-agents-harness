---
name: sign-in-and-access
title: Sign-in and access
involvement: teach-me
owns:
  - '<auth routes, session middleware, permission helpers, role checks>'
watch:
  - 'service_role|secret.?key|admin.?client'
  - 'SECURITY DEFINER'
  - 'role ?=== ?''admin''|isAdmin'
---

# Sign-in and access

**Involvement:** Teach me. A mistake here lets someone do or see what they shouldn't.
**The question:** who can reach this, by which door, and what checks them at that door?

## Invariants (always true)
- Every action checks access itself, on the server. A check only in the page doesn't protect an
  action a browser can call directly.
- Being signed in proves who someone is, not what they may do here.
- Access fails closed: an error or missing answer means no.
- Secrets that bypass access rules are used in as few, named places as possible.

## Tripwires (changes that pull you in, even from a trusted area)
- A new use of a key or function that bypasses access rules.
- A new route or entry point that skips the usual middleware.
- Anything deciding identity or ownership from a value the browser sends.

## How it breaks
- <the project's own incidents>

## Checks
- **Programs:** guard tests that fail if a forbidden pattern appears outside its allowed files.
- **Reviewer:** for each new entry point — who can call it directly? What does a signed-in stranger
  get? What does an error path return?

## Briefing
Teach me: what changed in who can do what, the request's path through the checks, and 2–3 ways it
could fail.
