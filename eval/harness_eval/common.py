"""Paths and small helpers shared by the evaluation's modules."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EVAL_DIR.parent
APP_DIR = EVAL_DIR / 'app'
TASKS_DIR = EVAL_DIR / 'tasks'
REGRESSION_DIR = EVAL_DIR / 'regression'
RESULTS_DIR = EVAL_DIR / 'results'
CACHE_DIR = EVAL_DIR / '.cache'
RUNS_DIR = EVAL_DIR / 'runs'


class EvalError(Exception):
    """A problem that stops the evaluation, with a message saying what to do."""


def say(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def run(args, cwd=None, env=None, timeout=600, check=True, input_text=None):
    """Runs a command and returns it finished. Raises EvalError when check is set and it fails."""
    result = subprocess.run(args, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True,
                            input=input_text)
    if check and result.returncode != 0:
        tail = (result.stdout + result.stderr).strip()[-1500:]
        raise EvalError(f'command failed ({result.returncode}): {" ".join(map(str, args))}\n{tail}')
    return result


def read_json(path: Path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write('\n')


def copy_tree(source: Path, dest: Path, ignore=None) -> None:
    """Copies a folder's contents into dest, merging with what's there."""
    shutil.copytree(source, dest, dirs_exist_ok=True, ignore=ignore, symlinks=True)


def clone_tree(source: Path, dest: Path) -> None:
    """A fast copy for big folders (node_modules): a copy-on-write clone where the disk allows it."""
    if sys.platform == 'darwin':
        attempt = subprocess.run(['cp', '-cR', str(source), str(dest)], capture_output=True)
    else:
        attempt = subprocess.run(['cp', '-R', '--reflink=auto', str(source), str(dest)], capture_output=True)
    if attempt.returncode != 0:
        shutil.copytree(source, dest, symlinks=True)


def which_dirs(names) -> list:
    """The folders holding each named program, for a clean PATH."""
    dirs = []
    for name in names:
        found = shutil.which(name)
        if found is None:
            raise EvalError(f'`{name}` is not on the PATH; install it first.')
        folder = str(Path(found).parent)
        if folder not in dirs:
            dirs.append(folder)
    return dirs


def load_tasks(only=None) -> list:
    """Every task's task.json, with its folder, sorted by id. `only` limits to ids or kinds."""
    tasks = []
    for path in sorted(TASKS_DIR.glob('*/task.json')):
        task = read_json(path)
        task['dir'] = path.parent
        if task['id'] != path.parent.name:
            raise EvalError(f'{path}: id {task["id"]!r} must match its folder name')
        if only and task['id'] not in only and task['kind'] not in only:
            continue
        tasks.append(task)
    if not tasks:
        raise EvalError(f'no tasks matched {only}')
    return tasks


def env_flag(name: str) -> bool:
    """Whether an environment variable is set, without reading its value into anything printed."""
    return os.environ.get(name, '') != ''
