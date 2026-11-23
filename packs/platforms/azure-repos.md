# Azure Repos: the approval lock

**What it does:** changes to harness files can't merge without the owner's approval.

**Cost:** branch policies are included with Azure DevOps Basic. Check the current docs.

## Steps
1. **Project settings → Repositories → the repo → Policies → Branch policies** for `main` (and
   `develop`): require a pull request.
2. **Automatically included reviewers → Add:** the owner, **Required**, with a path filter:
   `/AGENTS.md; /CLAUDE.md; /.claude/*; /.gemini/*; /.harness-version; /docs/systems/*`
3. **Check it worked:** a pull request editing `AGENTS.md` lists the owner as a required reviewer.

## Watching dependencies weekly
Azure's built-in dependency scanning is part of a paid add-on (GitHub Advanced Security for Azure
DevOps). Otherwise, a scheduled pipeline (a `schedules:` cron trigger, weekly) runs
`osv-scanner scan source --recursive .` and fails when it finds a vulnerability.
