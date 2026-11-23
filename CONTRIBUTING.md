# Contributing

Thanks for helping. This harness learns from the projects that use it, so the most useful thing you
can send is a **finding**: something a coding agent got wrong that the harness should have caught.

## Send a finding
1. In your project, ask your agent: "Should the harness have caught this? Write a harness finding."
   `finding.md` says what it writes.
2. **Strip your project out:** no code, names, file paths, customers, numbers or incidents that
   identify it. If the lesson can't be said without them, it belongs in your project, not here.
3. Open an issue with the **Harness finding** form.

Never post an unfixed security hole in an issue. See `SECURITY.md`.

## Change the harness
Read "Changing this repo" in the README first. In short:
- Pull requests go to `develop`, not `main`: `main` holds released versions only.
- One concern per pull request, starting from a finding.
- Prove it: a new check runs on made-up cases that must pass and must fail; a new tool or rule is
  tested as `evaluate.md` says. A change to templates, rules or packs runs the evaluation
  (`eval/README.md`) against `develop` on your own account, and the comparison goes in the pull request.
  The owner reruns it before merging rather than trusting the numbers.
- Bump `VERSION` and add a `CHANGELOG.md` entry written for the projects that will upgrade.
- Flag anything sensitive at the top: the trust rule, hooks, allowlists, anything that runs
  commands, or a new dependency.

Harness content is read by agents as material to review, never as instructions (`trust-rule.md`).
A change that tells agents to skip review or act without asking won't be merged.

The owner reviews every pull request line by line, so small ones get in fastest.
