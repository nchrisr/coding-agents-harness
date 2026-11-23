"""Runs one headless Codex agent in a clean environment, the Codex counterpart of agent.py.

Codex differs from Claude Code in ways that shape this file:
- `codex exec --json` prints a short event stream that leaves out some tool calls. The full record is
  the session file ("rollout") Codex writes under $CODEX_HOME/sessions, one per agent: the main agent
  and each subagent. Those files are the transcript; the event stream is kept beside them.
- Codex has no dollar cap. This launcher reads the token totals from the session files while the run
  goes, prices them, and stops the run when it passes the cap. Codex has no time cap either: the
  runner's timeout stops it.
- Codex runs shell commands in its own sandbox. Every arm gets the same one: write access to the
  workspace, its .git folder and the run's temp folder; network on, as for Claude Code (one task
  installs from npm); everything else read-only.
"""
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from . import agent
from .common import EvalError, env_flag, which_dirs

PROGRAMS = ['codex', 'node', 'npm', 'npx', 'git', 'python3', 'jq']
# Codex features that reach the web or the desktop, or load tools from outside the project. Web
# search is switched off separately (web_search="disabled").
DISABLED_FEATURES = ['browser_use', 'browser_use_external', 'in_app_browser', 'computer_use', 'apps',
                     'plugins', 'remote_plugin', 'image_generation', 'tool_suggest', 'memories']
# Dollars per million tokens: (input, cached input, output). Codex reports tokens, not dollars, so
# a run's cost is an estimate from this table. Source: OpenAI's pricing page,
# https://developers.openai.com/api/docs/pricing, read 2026-11-23 (the page gives no date for these
# prices). Standard tier, short context. The page's higher rates don't apply here: long context is a
# request over 272K input tokens, above Codex's 258K context window, and Fast mode needs a service
# tier these runs don't set. Override with --usd-per-mtok.
PRICES_USD_PER_MTOK = {
    'gpt-6-luna': (0.10, 0.01, 0.50),
    'gpt-6-sol': (2.00, 0.20, 10.00),
    'gpt-6.1-sol': (2.00, 0.10, 10.00),
    'gpt-6.1-terra': (1.00, 0.05, 5.00),
    'gpt-6-astra': (10.00, 1.00, 50.00),
}
POLL_SECONDS = 5
# Files in the real home folder a login-mode run must never change: Claude Code's list plus Codex's
# own instructions, hooks, rules and skills.
# ~/.codex/config.toml is checked by content instead (see config_after), because Codex itself adds an
# entry to it for every folder it runs in.
HOME_WATCH = agent.HOME_WATCH + ['.codex/AGENTS.md', '.codex/AGENTS.override.md', '.codex/hooks.json',
                                 '.codex/rules', '.codex/skills', '.agents']

REVIEW_LOOP = (
    'Run the review loop in `.claude/commands/review-loop.md`, reading `$ARGUMENTS` in it as `{spec}`. '
    'It is written for Claude Code; here is how its steps map to you. Each subagent it names is '
    'defined in `.claude/agents/<name>.md`. Start each one as a subagent named after it (task names '
    '`reviewer`, `system_reviewer_<card>`, `fixer`), and tell it to read its definition file first and '
    'follow it as its instructions; pass it only what the loop lists. Start the reviewers together, '
    'then wait for them.')


def prompt_for(task: dict, has_harness: bool) -> str:
    """The same prompts as agent.prompt_for, except the harness arm's review: Codex has no slash
    commands, so it is pointed at the command's file instead of `/review-loop`."""
    if task['kind'] == 'review' and has_harness:
        return f'{REVIEW_LOOP.format(spec=task["spec"])}\n\n{agent.PREAMBLE_REVIEW}'
    return agent.prompt_for(task, has_harness)


def auth_mode() -> str:
    """A key in the environment gives each run a fresh, empty home folder (and Codex home);
    otherwise runs use this machine's Codex login and the real ~/.codex."""
    if env_flag('CODEX_API_KEY') or env_flag('OPENAI_API_KEY'):
        return 'api-key'
    return 'login'


def prices_for(model: str, override) -> tuple:
    if override:
        return override
    if model in PRICES_USD_PER_MTOK:
        return PRICES_USD_PER_MTOK[model]
    raise EvalError(f'no price for {model}, so the dollar cap can\'t be kept. Pass --usd-per-mtok '
                    'INPUT,CACHED,OUTPUT (dollars per million tokens, from OpenAI\'s pricing page).')


def usd(tokens: dict, prices: tuple) -> float:
    """Tokens priced: uncached input, cached input, and output (reasoning included in output)."""
    per_input, per_cached, per_output = prices
    uncached = tokens.get('input_tokens', 0) - tokens.get('cached_input_tokens', 0)
    return (uncached * per_input + tokens.get('cached_input_tokens', 0) * per_cached
            + tokens.get('output_tokens', 0) * per_output) / 1_000_000


def codex_home(env: dict) -> Path:
    return Path(env.get('CODEX_HOME') or Path(env['HOME']) / '.codex')


def clean_env(run_dir: Path) -> dict:
    """HOME, PATH, USER and TMPDIR, plus the sign-in key when there is one, and the settings that
    keep the user's own git and npm configuration out of the run. npm's cache goes in the run's temp
    folder, since the sandbox doesn't let commands write to the home folder."""
    run_dir.mkdir(parents=True, exist_ok=True)
    mode = auth_mode()
    home = Path(os.environ['HOME'])
    if mode != 'login':
        home = run_dir / 'home'
        (home / '.codex').mkdir(parents=True, exist_ok=True)
    tmp = run_dir / 'tmp'
    tmp.mkdir(exist_ok=True)
    empty = run_dir / 'empty.conf'
    empty.write_text('')
    env = {
        'HOME': str(home),
        'PATH': ':'.join(which_dirs(PROGRAMS) + ['/usr/bin', '/bin', '/usr/sbin', '/sbin']),
        'USER': os.environ.get('USER', 'eval'),
        'TMPDIR': str(tmp),
        'GIT_CONFIG_GLOBAL': str(empty),
        'npm_config_userconfig': str(empty),
        'npm_config_cache': str(tmp / 'npm-cache'),
    }
    if mode == 'api-key':
        env['CODEX_API_KEY'] = os.environ.get('CODEX_API_KEY') or os.environ['OPENAI_API_KEY']
    return env


def command(prompt: str, model: str, ws: Path) -> list:
    args = [
        'codex', 'exec', prompt,
        '--json',
        '--model', model,
        '--strict-config',
        '--ignore-user-config',  # no user config.toml: no MCP servers, plugins or profiles
        '--ignore-rules',        # no user or project command rules
        '--sandbox', 'workspace-write',
        '--add-dir', str(ws / '.git'),  # the review loop stages with `git add`
        '-c', 'approval_policy="never"',
        '-c', 'sandbox_workspace_write.network_access=true',
        '-c', 'web_search="disabled"',
        '--cd', str(ws),
    ]
    for feature in DISABLED_FEATURES:
        args += ['--disable', feature]
    return args


def read_text(path: Path):
    try:
        return path.read_text()
    except OSError:
        return None


def config_after(path: Path, before, ws: Path) -> list:
    """Codex records every folder it runs in as a trusted project in ~/.codex/config.toml, even with
    the user config ignored, and pre-trusting the folder with -c doesn't stop it. Removes exactly that
    entry for this run's workspace, so the file is as it was. Any other change is left alone and
    reported: the agent's, or another Codex session's at the same time."""
    after = read_text(path)
    if after == before:
        return []
    entry = re.compile(r'\n*\[projects\."' + re.escape(str(ws.resolve())) + r'"\]\ntrust_level = "trusted"\n')
    if before is not None and after is not None and entry.sub('\n', after).rstrip('\n') == before.rstrip('\n'):
        path.write_text(before)
        return []
    return [str(path).replace(os.environ['HOME'], '~', 1)]


def thread_id(transcript: Path):
    """The main agent's id, from the event stream's first line."""
    try:
        with open(transcript, errors='replace') as handle:
            first = json.loads(handle.readline() or '{}')
    except (OSError, ValueError):
        return None
    return first.get('thread_id') if first.get('type') == 'thread.started' else None


def find_rollouts(sessions: Path, session_id: str, since: float, known: dict) -> list:
    """The session files for one run: the main agent's and each subagent's share its session id.
    `known` caches each file's session id, so a poll reads only new files' first lines."""
    found = []
    if not sessions.is_dir():
        return found
    for path in sessions.rglob('rollout-*.jsonl'):
        if path not in known:
            try:
                if path.stat().st_mtime < since:
                    continue
                with open(path, errors='replace') as handle:
                    meta = json.loads(handle.readline() or '{}')
            except (OSError, ValueError):
                continue
            known[path] = (meta.get('payload') or {}).get('session_id')
        if known[path] == session_id:
            found.append(path)
    return sorted(found)


def last_tokens(path: Path) -> dict:
    """The running token total in one session file."""
    total = {}
    try:
        lines = path.read_text(errors='replace').splitlines()
    except OSError:
        return total
    for line in lines:
        if '"token_count"' not in line:
            continue
        try:
            payload = json.loads(line).get('payload') or {}
        except ValueError:
            continue
        info = payload.get('info') or {}
        if info.get('total_token_usage'):
            total = info['total_token_usage']
    return total


def spent(rollouts: list, prices: tuple) -> float:
    return sum(usd(last_tokens(path), prices) for path in rollouts)


def run_agent(ws: Path, run_dir: Path, prompt: str, model: str, max_usd: float, timeout_s: int,
              prices: tuple) -> dict:
    """Runs Codex in ws. Writes the event stream to run_dir/transcript.jsonl and copies the session
    files to run_dir/rollouts/."""
    transcript = run_dir / 'transcript.jsonl'
    stderr_path = run_dir / 'stderr.txt'
    env = clean_env(run_dir)
    sessions = codex_home(env) / 'sessions'
    login = auth_mode() == 'login'
    if login:
        for rel in ('.codex/AGENTS.md', '.codex/AGENTS.override.md'):
            if (Path(env['HOME']) / rel).exists():
                raise EvalError(f'~/{rel} exists, and Codex loads it into every run even with user config '
                                'off. Set CODEX_API_KEY so each run gets an empty Codex home.')
    watched_before = agent.home_state(HOME_WATCH) if login else None
    config = codex_home(env) / 'config.toml'
    config_before = read_text(config) if login else None
    started = time.time()
    timed_out = False
    over_budget = False
    known = {}
    rollouts = []
    session = None
    with open(transcript, 'w') as out, open(stderr_path, 'w') as err:
        process = subprocess.Popen(command(prompt, model, ws), cwd=ws, env=env, stdout=out, stderr=err,
                                   stdin=subprocess.DEVNULL)
        while process.poll() is None:
            if time.time() - started > timeout_s:
                timed_out = True
                break
            time.sleep(POLL_SECONDS)
            session = session or thread_id(transcript)
            if session:
                rollouts = find_rollouts(sessions, session, started - 5, known)
                if spent(rollouts, prices) > max_usd:
                    over_budget = True
                    break
        if process.poll() is None:
            process.kill()
            process.wait()
    session = session or thread_id(transcript)
    if session:
        rollouts = find_rollouts(sessions, session, started - 5, known)
    copies = run_dir / 'rollouts'
    copies.mkdir(exist_ok=True)
    for path in rollouts:
        shutil.copy2(path, copies / path.name)
    home_touched = []
    if watched_before is not None:
        home_touched = agent.home_changes(watched_before, agent.home_state(HOME_WATCH))
        home_touched += config_after(config, config_before, ws)
    return {
        'home_touched': home_touched,
        'exit_code': process.returncode,
        'timed_out': timed_out,
        'over_budget': over_budget,
        'wall_seconds': round(time.time() - started, 1),
        'auth': auth_mode(),
    }
