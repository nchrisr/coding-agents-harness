# GitLab: the approval lock

**What it does:** changes to harness files can't merge without the owner's approval.

**Cost:** Code Owners approval rules need **GitLab Premium** or higher. Check the current docs.

## Steps
1. Commit `CODEOWNERS` (root, `docs/` or `.gitlab/`), using the same paths as the GitHub pack, with
   the owner's GitLab username.
2. **Settings → Repository → Protected branches:** protect `main` (and `develop`), allow merge only
   through merge requests, and turn on **Code owner approval**.
3. **Check it worked:** a merge request editing `AGENTS.md` shows the owner as a required approver.
