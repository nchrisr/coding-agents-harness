# Azure Repos: the approval lock

**What it does:** changes to harness files can't merge without the owner's approval.

**Cost:** branch policies are included with Azure DevOps Basic. Check the current docs.

## Steps
1. **Project settings → Repositories → the repo → Policies → Branch policies** for `main` (and
   `develop`): require a pull request.
2. **Automatically included reviewers → Add:** the owner, **Required**, with a path filter:
   `/AGENTS.md; /CLAUDE.md; /.claude/*; /.harness-version; /docs/systems/*`
3. **Check it worked:** a pull request editing `AGENTS.md` lists the owner as a required reviewer.
