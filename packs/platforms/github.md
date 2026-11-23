# GitHub: the approval lock

**What it does:** changes to harness files can't merge without the owner's approval.

**Cost:** on a **private** repository this needs **GitHub Pro** (personal) or **Team** (organization).
On GitHub Free it works only on public repositories. Rulesets are the newer alternative to branch
protection; check which your plan allows before relying on either. Check the current docs, since plans
change.

## Steps
1. The project must live under the owner's account or organization.
2. Commit `.github/CODEOWNERS`:
   ```
   AGENTS.md            @<owner>
   CLAUDE.md            @<owner>
   .claude/             @<owner>
   .gemini/             @<owner>
   .harness-version     @<owner>
   docs/systems/        @<owner>
   .github/             @<owner>
   ```
3. GitHub → the repo → **Settings** → **Branches** (or **Rules → Rulesets**) → add a rule for each
   long-lived branch (`main`, and `develop` if used): require a pull request, require approval, and
   tick **Require review from Code Owners**.
4. **Check it worked:** open a pull request that edits `AGENTS.md` from another account; the merge
   button should say a code owner's review is required.

**Narrow keys:** the `gh` tool signs in with a fine-grained token limited to one repository.

## Watching dependencies weekly (free, also on private repositories)
**Settings → Code security** (or "Security & analysis") → turn on **Dependabot alerts** and
**Dependabot security updates**. GitHub then emails you when a dependency turns vulnerable and opens a
pull request that upgrades it. Those pull requests go through review like any other change; the
dependencies card wakes for them.
