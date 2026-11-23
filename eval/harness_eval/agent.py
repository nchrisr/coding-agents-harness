"""Runs one headless agent in a clean environment, as evaluate.md asks."""
import os
import subprocess
import time
from pathlib import Path

from .common import env_flag, which_dirs

# The tools every arm may use. Passed on the command line because permission lists in a project's
# .claude/settings.json are ignored in a folder the agent hasn't been told to trust.
ALLOWED_TOOLS = ['Bash', 'Read', 'Edit', 'Write', 'MultiEdit', 'Glob', 'Grep', 'Agent', 'Task',
                 'TodoWrite', 'Skill', 'SlashCommand']
# No web access: runs stay comparable, and nothing a task contains can reach out through them.
DISALLOWED_TOOLS = ['WebFetch', 'WebSearch']
PROGRAMS = ['claude', 'node', 'npm', 'npx', 'git', 'python3', 'jq']
# Each run's first line. The owner is never there during a run, so every arm is told the same thing.
PREAMBLE_BUILD = (
    'The owner is away while you work. They have approved this task as written, including any spec '
    'your process asks for, so carry on without waiting for replies. If part of it needs the owner\'s '
    'decision, don\'t do that part: explain it in your final message. Don\'t commit or push.')
PREAMBLE_REVIEW = (
    'The owner is away while you work, so carry on without waiting for replies, and put every question '
    'for the owner in your final message. Don\'t commit or push.')
BARE_REVIEW = (
    'Review the change on this branch (everything since `main`) against its spec, `{spec}`. Fix each '
    'real bug you find, with a test that shows it, and leave alone anything the spec asks for. '
    'Finish with what you found, fixed and left alone.')


def prompt_for(task: dict, has_harness: bool) -> str:
    if task['kind'] == 'review':
        if has_harness:
            return f'/review-loop {task["spec"]}\n\n{PREAMBLE_REVIEW}'
        return f'{BARE_REVIEW.format(spec=task["spec"])}\n\n{PREAMBLE_REVIEW}'
    return f'{task["prompt"]}\n\n{PREAMBLE_BUILD}'


def auth_mode() -> str:
    """How the runs sign in. A key or token in the environment gives each run a fresh, empty home
    folder; otherwise runs use this machine's login and the real home folder, with user settings,
    user instructions and user MCP servers all switched off."""
    if env_flag('ANTHROPIC_API_KEY'):
        return 'api-key'
    if env_flag('CLAUDE_CODE_OAUTH_TOKEN'):
        return 'oauth-token'
    return 'login'


# Files in the real home folder a run must never change. In login mode (the real home folder), each
# run checks them before and after, and a run that changed one doesn't count.
HOME_WATCH = ['.claude/settings.json', '.claude/settings.local.json', '.claude/CLAUDE.md', '.claude/agents',
              '.claude/commands', '.claude/hooks', '.zshrc', '.zprofile', '.bashrc', '.bash_profile',
              '.profile', '.gitconfig', '.npmrc', '.ssh', '.config/gh', '.aws']


def home_state() -> dict:
    """Size and change time of each watched file in the real home folder (folders: newest inside)."""
    home = Path(os.environ['HOME'])
    state = {}
    for rel in HOME_WATCH:
        path = home / rel
        if path.is_dir():
            newest = 0.0
            for child in path.rglob('*'):
                try:
                    newest = max(newest, child.lstat().st_mtime)
                except OSError:
                    continue
            state[rel] = ('dir', newest)
        elif path.exists():
            info = path.lstat()
            state[rel] = ('file', info.st_mtime, info.st_size)
    return state


def home_changes(before: dict, after: dict) -> list:
    changed = []
    for rel in sorted(set(before) | set(after)):
        if before.get(rel) != after.get(rel):
            changed.append(f'~/{rel}')
    return changed


def scoring_env(run_dir: Path) -> dict:
    """The environment for the scorer's own type check and tests, which run code the agent wrote:
    clean, with a throwaway home folder and no sign-in secret."""
    env = clean_env(run_dir, sign_in=False)
    return env


def clean_env(run_dir: Path, sign_in: bool = True) -> dict:
    """HOME, PATH, USER and TMPDIR only, plus the sign-in secret when there is one, and two settings
    that keep the user's own git and npm configuration out of the run."""
    run_dir.mkdir(parents=True, exist_ok=True)
    mode = auth_mode()
    home = Path(os.environ['HOME'])
    if mode != 'login' or not sign_in:
        home = run_dir / 'home'
        home.mkdir(exist_ok=True)
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
    }
    if not sign_in:
        return env
    if mode == 'api-key':
        env['ANTHROPIC_API_KEY'] = os.environ['ANTHROPIC_API_KEY']
    elif mode == 'oauth-token':
        env['CLAUDE_CODE_OAUTH_TOKEN'] = os.environ['CLAUDE_CODE_OAUTH_TOKEN']
    return env


def command(prompt: str, model: str, max_usd: float) -> list:
    return [
        'claude', '-p', prompt,
        '--output-format', 'stream-json', '--verbose', '--include-hook-events',
        '--model', model,
        '--setting-sources', 'project',
        '--strict-mcp-config',
        '--no-session-persistence',
        '--permission-mode', 'acceptEdits',
        '--allowedTools', *ALLOWED_TOOLS,
        '--disallowedTools', *DISALLOWED_TOOLS,
        '--max-budget-usd', f'{max_usd:.2f}',
    ]


def run_agent(ws: Path, run_dir: Path, prompt: str, model: str, max_usd: float,
              timeout_s: int) -> dict:
    """Runs the agent in ws, writing its transcript to run_dir/transcript.jsonl."""
    transcript = run_dir / 'transcript.jsonl'
    stderr_path = run_dir / 'stderr.txt'
    env = clean_env(run_dir)
    watched_before = home_state() if auth_mode() == 'login' else None
    started = time.time()
    timed_out = False
    with open(transcript, 'w') as out, open(stderr_path, 'w') as err:
        process = subprocess.Popen(command(prompt, model, max_usd), cwd=ws, env=env, stdout=out,
                                   stderr=err, stdin=subprocess.DEVNULL)
        try:
            process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
    home_touched = []
    if watched_before is not None:
        home_touched = home_changes(watched_before, home_state())
    return {
        'home_touched': home_touched,
        'exit_code': process.returncode,
        'timed_out': timed_out,
        'wall_seconds': round(time.time() - started, 1),
        'auth': auth_mode(),
    }
