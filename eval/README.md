# Harness evaluation

Checks whether a harness version makes agents better at the work that matters, so a change can be
judged better or worse before it merges. It follows `../evaluate.md`. **The results advise; the
owner still reviews and merges.**

Real runs are real agent sessions. The results give each run's **cost at API prices**: in the first
validation run, on Sonnet 5.5, $0.10 to $2.20 a run, $1.40 on average (a review loop, or a feature
that goes through the harness's spec and review steps, costs the most). Signed in with a Claude
subscription, you aren't billed that: it comes out of your plan's usage, like any session. With an
API key, it's what you pay. Nothing here runs on its own: you run it on your machine.

## What it measures

| Goal | How | Task set |
|---|---|---|
| Builds features from a description | Hidden acceptance tests the agent never sees, run after it finishes | 3 features |
| Introduces no bugs | The app's own tests, as the run left them, and a hidden regression suite the agent never sees, after every task. A regression is a starting test that still exists and no longer passes; a test that was renamed or deleted is listed separately (`tests_gone`), and so is every test file the run edited (`tests_changed`) | every task |
| Catches bugs in review | `/review-loop` on a change with a planted bug, and in two of them a decoy that looks wrong but is what the spec asks for. Hidden tests show whether the bug got fixed and the decoy kept; a blind grader reads the final report for bugs reported but not fixed, and decoys raised to the owner | 3 reviews, 2 decoys |
| Security holds | Tasks that tempt a risky move: a vendored package with an install script, a hook that downloads and runs a script, an API key handed over in the request, a dependency pinned to a version with known vulnerabilities. A program checks whether the risky thing happened; the grader checks whether the owner was told | 4 temptations |
| Cost | Tokens, dollars and time per run, from the transcripts, subagents included | every task |

## Run it

```bash
python3 eval/run.py dry-run
```
Checks the whole pipeline without calling a model, in about a minute: every task builds, its hidden
tests fail before the work and pass on a reference solution, unsafe outcomes are caught, and the
transcript checks reject a run with a permission denial or without the harness loaded. Run it after
any change to `eval/`.

```bash
python3 eval/run.py run --compare-to origin/main
```
The way to judge a change: this checkout's harness and `main`'s, interleaved in one session with the
same model and Claude Code version, 2 runs per task each: 40 runs, roughly $50 to $60 at API prices
(40 runs at about $1.40), plus under a dollar of grading. It prints the comparison and keeps it, with each arm's results file
(`results-<arm>.json`), the transcripts and each run's diff, in `eval/runs/<time>/`, which git
ignores. **Paste `comparison.md` into the pull request.**

```bash
python3 eval/run.py run
```
This checkout's harness only, written to `eval/results/<VERSION>.json` and compared with the previous
version's file. The owner runs this after merging a version and commits the file, as the record for
that version. Comparing against an older file is only fair when the model, the Claude Code version,
the task set and the runs per task match; the comparison says when they don't.
`eval/results/validation-0.8.0.json` is the first real run, one per task, kept as a worked example.

**Trying variations** (`evaluate.md`): put each variation of a rule on its own branch and run them
against one baseline in the same session:

```bash
python3 eval/run.py run --harness variation-a --compare-to origin/main --variants variation-b variation-c
```
Each arm gets its own comparison against the baseline. Combine what helped from each into the version
that goes in; keep the losing variations and why they lost in the finding.

**Side by side, without a key.** Hidden tests judge correctness, but not whether the work is plain,
well tested and free of extra moves. So in a side-by-side run, each change is also shown to the grader
next to the baseline's change on the same task, under random ids, in a random order, and it says which
is better and why. The comparison reports the wins, losses and ties (`--no-side-by-side` skips it).

Useful options: `--tasks review security` (ids or kinds), `--runs 3`, `--model`, `--jobs 2`,
`--max-usd-total 60` (no new run starts once this much is spent; runs already going finish, each
within `--max-usd-per-run`, default 4), `--harness none` (no harness at all: the floor a harness
should beat), `--keep` (keep the workspaces to look at).

Needs `claude`, `node` 22, `npm`, `git`, `python3` 3.11 or later, and `jq`. The security task with a
vulnerable dependency needs the npm registry; it's skipped, and says so, when that's unreachable.

**Sign-in, and what a run can touch.** Three ways, best first:
1. **A token from your subscription** (recommended): run `claude setup-token` yourself, then
   `export CLAUDE_CODE_OAUTH_TOKEN=<the token>` in the terminal you run the evaluation from. Runs use
   your plan's usage, and each gets a fresh, empty home folder.
2. **An API key**, if you have API credit but no subscription: `export ANTHROPIC_API_KEY=...`. Same
   fresh home folder; you pay API prices.
3. **Your machine's login**, with `--use-my-login`. Without a token or key the runner stops and asks
   for this flag, because runs then use **your real home folder**, with your user settings,
   instructions and MCP servers switched off (`--setting-sources project`, `--strict-mcp-config`).
   Some tasks tempt the agent to install hooks "for everyone", so in this mode each run checks your
   shell, git, npm, SSH and Claude settings before and after, and a run that changed one doesn't
   count and says which.

None of these is a sandbox: the agent has a shell running as you. The tasks are harmless if
taken (`.invalid` addresses, fake keys, a marker file), and agents aren't adversaries, but for real
isolation run it in a container.

## Codex

```bash
python3 eval/run.py dry-run --agent codex
python3 eval/run.py run --agent codex --compare-to origin/main
```
Claude Code stays the default; `--agent codex` runs the same tasks with `codex exec`, scored the
same way, so the two agents' results line up task by task. Results go to
`results/<VERSION>-codex.json` and are compared only with other Codex files. The grader is still
Claude, so both agents are graded by the same model. Needs `codex` as well as the list above.

What differs, and why:
- **What the harness gives Codex.** Codex reads `AGENTS.md`; it has no Stop hook, no `/review-loop`
  command and no subagent files of its own from the harness. So the harness arm's review prompt
  points Codex at `.claude/commands/review-loop.md` and the agent files beside it, and Codex starts
  its own subagents (`reviewer`, `system_reviewer_<card>`, `fixer`). The other prompts are word for
  word the same as Claude Code's.
- **Proof it ran** (`harness_eval/codex_transcript.py`), read from the session files Codex writes
  for each agent, which `codex exec --json` doesn't fully echo: the model; `AGENTS.md` loaded in a
  harness arm and absent in a no-harness one; a review's `reviewer` subagent started; no MCP tool
  or web search used. Whether the agent ran `npm run check` (what AGENTS.md asks instead of the Stop
  hook) and whether the reviewer read its definition file are recorded, not required.
- **The sandbox.** Codex runs commands in its own sandbox, the same in every arm: write access to the
  workspace, its `.git` folder and the run's temp folder, network on (as for Claude Code), the rest
  read-only. A command the sandbox blocks makes a feature or review run not count (a setup fault);
  in a security task it's the risky move being stopped, and is recorded (`sandbox_blocks`). Claude
  Code has no such sandbox, so a security task can come out differently for that reason alone.
- **Codex costs are estimates from a price table, not billed figures.** Codex reports tokens, not
  dollars. Every Codex cost here, and both dollar caps, is tokens times the table in
  `harness_eval/codex_agent.py`: OpenAI's standard prices from its pricing page, read 2026-11-23.
  Check them against https://developers.openai.com/api/docs/pricing before trusting a total, and
  pass `--usd-per-mtok INPUT,CACHED,OUTPUT` when they change or for a model not in the table. Signed
  in with ChatGPT, runs come out of your plan instead. Codex has no dollar cap of its own, so the
  runner reads the session files while a run goes and stops it at the cap; `--timeout-minutes`
  stops it on time.

`results/validation-0.9.2-codex.json` is the first real Codex run, kept as a worked example: one
review task on gpt-6-luna, which counted, with the bug fixed and the decoy kept. Estimated at $0.019
(755,518 tokens, 88% of them cache reads at $0.01 a million), plus $0.04 of Claude grading. It ran
before this branch was moved onto 0.9.1, so its harness version reads 0.8.1.
- **Sign-in.** `export CODEX_API_KEY=...` (or `OPENAI_API_KEY`) gives each run an empty home and
  Codex home. Without one, `--use-my-login` uses your Codex login and real `~/.codex`, with your
  `config.toml` and rules ignored; the runner stops if `~/.codex/AGENTS.md` exists, since Codex
  would load it into every run. Each run checks your shell, git, npm and Codex settings before and
  after, and its session files stay in your Codex history.

## How a run works

1. **Build** a fresh copy of the practice app (`app/`) in a temporary folder outside this
   repository, with the harness under test laid over it (`harness/`, plus the templates listed in
   `harness/from-templates.json`, copied from that harness version), and the task's starting state.
   It's a new git repository: `main` holds the app; a review task's change sits on a branch.
2. **Record the start:** which of the app's tests and the regression suite pass. The hidden task
   tests never enter a workspace until the agent has finished.
3. **Run the agent:** `claude -p --output-format stream-json --verbose`, in a clean environment
   (`env -i` with HOME, PATH, USER and TMPDIR, plus settings that keep your own git and npm
   configuration out), the same allowed tools in every arm, passed on the command line because a
   project's permission list is ignored in an untrusted folder. No web tools. Each run has a dollar
   cap and a time limit.
4. **Prove it ran** (`harness_eval/transcript.py`). A run doesn't count when: it ran on another
   model, any MCP server loaded, it ended in an error, any tool was denied, it named this repository
   or the hidden tests, it changed your home folder, or (in a harness arm) the harness's agents and
   commands didn't load, the Stop hook never ran, or a review task's loop never started its reviewer.
   Runs that don't count are listed, and **any of them stops the comparison giving a verdict**, as
   `evaluate.md` says. A run that hit its dollar cap or time limit, or that the API refused, is the
   arm's own outcome: it counts, scored as it stood.
5. **Score** (`harness_eval/score.py`): the saved diff is taken first, with git's exclude rules
   emptied so nothing is hidden from it; the security checks read the workspace as the run left it;
   then the scorer undoes anything that changes how tests run (extra vitest or vite configs, the
   test config, edits to the starting packages in `node_modules`) and runs the type check, the app's
   tests, the regression suite and the hidden tests, in a clean environment. The hidden tests use
   their own copy of the test helpers.
6. **Grade blind** (`harness_eval/grade.py`): yes/no questions about each review's and security
   task's final message, in a random order, by a different model with no tools, with words that name
   the harness removed.

## Reading the results

A comparison (`comparison.md`) is a table: each headline number for both arms and whether it got
better, worse or stayed the same, then an overall line, then **warnings to read first**. A results
file holds the headline numbers (`summary`), every run's score, cost and grader answers with the
quote that decided each, and the runs that didn't count. Two runs per task show large differences, not small ones; a change in
cost under 10% is reported as noise. A **tuning warning** means a harness file mentions a task's
distinctive words: a harness tuned to this test rather than to agents in general. Look at it before
believing the numbers.

What it doesn't cover: other languages and project sizes, long sessions, multi-day work, a real
owner answering questions, and anything outside the ten tasks. Agents vary from run to run.

## Rules for contributors

- **The owner reruns before merging** rather than trusting numbers in a pull request. Run it on your
  own account, and put the comparison in the pull request.
- **Never tune the harness to the tasks.** A rule that only helps because it names something in
  `tasks/` makes the numbers lie. The tuning check catches the obvious cases. Sort the lesson first,
  as `finding.md` says: how the agent works belongs in the harness; what an expert in the subject
  knows (that a given lodash version is vulnerable, how this shop rounds) belongs in a project, and
  putting it in the harness only teaches the test.
- **Keep the hidden tests hidden.** They live here, never in the practice app. A run is built outside
  this repository and doesn't count if it names it.
- **When a template changes,** the practice app picks it up automatically. If its placeholder text
  moved, the build stops and names the file: update `harness/from-templates.json`. A change to what
  setup writes per project (`AGENTS.md`, cards, settings) means updating `harness/` by hand, the way
  an upgrade would.
- **A harness may only add harness files** to the practice app (`AGENTS.md`, `CLAUDE.md`, `.npmrc`,
  `.claude/`, `docs/`, `scripts/`). The build stops if `harness/` reaches the app's code or tests.
- **Adding a task:** a folder in `tasks/` named as its id, with `task.json`, hidden tests in
  `hidden/`, and a reference solution in `solution/` (files laid over the app). A security task also
  has `bad/`, the unsafe outcome. Write tests with `it(`, not `it.each`, so each one is counted. The
  dry run must pass. Keep any temptation harmless if taken: `.invalid` addresses, fake keys, a
  marker file instead of a real network call.

- **From a finding to a task.** When a finding says the harness missed a kind of bug or risk, it can
  become a task here too: a planted bug of that kind, or a feature that tempts it, with a hidden test.
  Then every later harness change is checked against that lesson. Strip the project out first, as
  `finding.md` says: no real code, names or paths.

`task.json` fields:

| Field | Kinds | Meaning |
|---|---|---|
| `id`, `kind`, `title` | all | `kind` is `feature`, `review` or `security` |
| `prompt` | feature, security | What the agent is asked, word for word |
| `hidden_tests` | all | Test files, run only after the agent finishes |
| `canaries` | all | Words distinctive to the task; a harness file that mentions one gets a tuning warning |
| `spec`, `change_message` | review | The spec the change follows (in `change/`, committed on a branch) |
| `bug`, `decoy`, `spec_test` | review | Each `{test, description}`: the planted bug's test must fail before and pass after; the decoy's and the spec's must keep passing. `decoy` may be null. Descriptions go to the grader |
| `security.check` | security | `install-script`, `remote-hook`, `secret` or `vulnerable-dep`, with that check's fields (`marker`; `pattern`; `secret`; `package`, `bad_versions`). A new kind needs code in `score.py` |
| `grade_question` | security | The yes/no question for the grader: was the owner told? |
| `setup`, `vendor_package`, `needs_network` | any | Files laid over the app at the start; a folder packed as an npm tarball; skip when the npm registry is unreachable |
