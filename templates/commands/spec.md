---
description: Write a decision-based spec for a tier 2 or 3 change and wait for approval
argument-hint: <what to build>
---

Write a spec for: $ARGUMENTS

Don't edit code. Use plan mode if it's available.

1. **Understand it.** Read the relevant docs, settled decisions and code. Check assumptions against the
   real system, not just the files.
2. **Pick the tier** using `AGENTS.md`, and say why. A tier 1 change doesn't need a spec: say so and stop.
3. **Name the systems.** Which cards in `docs/systems/` does this touch, and what is each set to? A
   change that trips a tripwire counts as teach-me for that card.
4. **Write the spec** in this shape, kept short:

   ```markdown
   # <Title>

   **Tier:** 2 or 3, and why
   **Systems:** <card> (<setting>), …
   **Why:** the problem and who it affects, stated in full

   ## Decisions
   ### <Decision>
   - **Options:** what was considered
   - **Chosen:** which, and why
   - **Still uncertain:** what we don't know yet

   ## How it could go wrong
   For each teach-me system: the two or three realistic failures, and what catches each.

   ## Changes
   Each file, and what changes in it.

   ## Testing
   What proves it works, including each card's program checks, and what can't be checked here.

   ## Owner steps
   Anything the owner has to do, in order. Include migration and deploy order.
   ```

5. **Tier 3 only:** run the `spec-critic` subagent. Check its findings, fix the spec for the ones that
   hold up, and report which you rejected and why.
6. **Save it** as `docs/specs/YYYY-MM-DD-short-name.md`. If it describes an unfixed security hole, keep
   it in chat instead.
7. **Stop and walk the owner through it.** Teach-me decisions one at a time; everything else as one
   question sheet with a recommendation for each. Wait for approval before writing code.
