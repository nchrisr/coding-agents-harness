# Working rules

Copied into a project's `AGENTS.md` at setup, adapted to its words.

## Talking to the owner
- **Explain in small chunks,** one idea at a time, in plain language, with an analogy where one helps.
- **One question sheet, not a drip.** Collect every question a step raises and ask them together,
  each with a recommendation, so one visit clears them.
- **Outside *Teach me*, decide and log.** Make the call, write it down (the spec, the PR summary or the
  decisions doc), and keep going to the next checkpoint: something the owner can look at.
- **Ask the owner only what is theirs:** product, money, cost, risk appetite, and anything on a
  *Teach me* card. Settle technical details with the reviewers.

## Several sessions at once (an event loop, not interrupts)
- **The inbox is the session list.** A session that needs the owner ends its turn with its question;
  the app marks it as waiting. It doesn't chase.
- **Only the session the owner is talking to uses voice.** A background session never speaks unless
  the owner spoke to it first in that session.
- **One task, one session, one worktree.** Only one session at a time changes the database schema.

## Changes
- Changes reach the main branch the way the project chose at setup: branches and pull requests, or
  straight to `main` for a solo learning project.
- Run the same checks as CI before claiming anything is done.
- After restarting a server, prove it restarted before asking for a retest.
- Never run git commands that move or discard uncommitted work without saying so first.
- When a change needs someone else to act, end with numbered steps: exact commands and buttons,
  where they are, what to wait for, how to check it worked, and side effects.

## Security
- Flag security risks as you notice them: what an attacker would need, whether it's exposed today
  (check, don't guess), and what would fix it. Explain any jargon.
- Never write an unfixed security hole into a committed file, a spec or a PR comment. Report it in
  chat. Write it up once fixed.

## When something slips through
Ask: should the harness have caught this? If yes, write a harness finding (`finding.md`).
