# Where agents get the harness from

Every setup and upgrade reads the harness from one **source**, set in a small file you keep in the
glass case next to the trust rule:

- macOS and Linux: `~/.config/coding-agents-harness/source`
- Windows: `%USERPROFILE%\.config\coding-agents-harness\source`

It's locked with the rule because whoever controls it controls what every project's upgrade brings
in. An agent that could edit it could point your upgrades at a tampered copy.

## The file

```
# Where agents get the coding agents harness from. Locked with the trust rule.
# mode: remote | local-commit | local-working
mode = remote
# remote: the repository to fetch from, and its branch. A fork works.
url = https://github.com/<you>/coding-agents-harness.git
branch = main
# The local folder agents use to read the harness (a clone of it). Needed for every mode.
path = ~/My-Projects/coding-agents-harness
```

## The three modes

| Mode | Reads | Use it when | Reviewed? |
|---|---|---|---|
| `remote` (recommended) | The latest commit of `branch` at `url`, fetched fresh | Normal use, including from a fork | Yes, through that repository's pull requests |
| `local-commit` | The latest commit of `branch` in the `path` folder | Offline, or trying a harness branch before pushing it | Only as far as you reviewed your own commits |
| `local-working` | The files in `path` as they are now, uncommitted edits included | You're editing the harness itself and want to try it at once | **No.** The agent says so loudly before anything else |

## How an agent reads a harness file

Read the source file first. Then, for a harness file such as `CHANGELOG.md`:

| Mode | Command |
|---|---|
| `remote` | `git -C <path> fetch --quiet <url> <branch>`, then `git -C <path> show FETCH_HEAD:CHANGELOG.md` |
| `local-commit` | `git -C <path> show <branch>:CHANGELOG.md` |
| `local-working` | Read `<path>/CHANGELOG.md` directly |

In `remote` and `local-commit` modes, never read the folder's files directly: they may hold edits
nobody reviewed. If the source file is missing or unreadable, stop and walk the owner through
creating it (the steps are in `trust-rule.md`). Never create or edit it yourself.
