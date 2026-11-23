"""Builds the practice app for one run: the app, the harness version under test, and the task's
starting state, in a fresh git repository outside this one."""
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from .common import (APP_DIR, CACHE_DIR, REGRESSION_DIR, REPO_ROOT, EvalError, clone_tree, copy_tree,
                     read_json, run, say)

# Files the scorer puts back from the starting state before it runs any test: the test setup the
# hidden tests rely on. The app's own tests stay as the run left them, since a change can rightly
# update a test; the hidden regression suite, which the run never sees, is the anchor, and the
# scorer reports every test file the run changed.
TEST_INFRA = ['vitest.config.ts']
EVAL_TEST_DIR = 'test/__eval__'
NO_HARNESS = 'none'
GIT_IDENTITY = ['-c', 'user.name=Eval', '-c', 'user.email=eval@example.invalid', '-c', 'commit.gpgsign=false']


# What a harness version may put in the practice app: the files setup writes. Anything else (the
# app's code, its tests, package.json, test config) would let a harness change the test itself.
HARNESS_PATHS = ('AGENTS.md', 'CLAUDE.md', '.npmrc', '.claude/', 'docs/', 'scripts/')


def hidden_test_id(rel: str) -> str:
    """Where a hidden test file goes in the workspace, which is also how its test ids start."""
    return f'{EVAL_TEST_DIR}/hidden-{Path(rel).name}'


def check_harness_paths(overlay: Path, mapping: dict) -> None:
    bad = []
    for path in sorted(overlay.rglob('*')):
        rel = str(path.relative_to(overlay))
        if path.is_file() and rel != 'from-templates.json' and not rel.startswith(HARNESS_PATHS):
            bad.append(rel)
    for entry in mapping['files']:
        if not entry['dest'].startswith(HARNESS_PATHS):
            bad.append(entry['dest'])
    if bad:
        raise EvalError(f'the harness under test writes outside the harness files: {bad[:5]}. '
                        f'A harness may only add {", ".join(HARNESS_PATHS)}.')


def harness_source(ref: str, dest: Path) -> dict:
    """Puts the harness to evaluate in dest and describes it.

    ref is "worktree" (this checkout as it is, uncommitted edits included), a git ref, or "none"
    (no harness at all: the floor the harness should beat)."""
    if ref == NO_HARNESS:
        return {'ref': NO_HARNESS, 'version': 'none', 'commit': None, 'dirty': False}
    dest.mkdir(parents=True, exist_ok=True)
    if ref == 'worktree':
        for part in ('templates', 'eval/harness', 'VERSION'):
            source = REPO_ROOT / part
            if source.is_dir():
                copy_tree(source, dest / part)
            else:
                (dest / part).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest / part)
        commit = run(['git', 'rev-parse', 'HEAD'], cwd=REPO_ROOT).stdout.strip()
        dirty = run(['git', 'status', '--porcelain', '--', 'templates', 'eval/harness', 'VERSION'],
                    cwd=REPO_ROOT).stdout.strip() != ''
    else:
        commit = run(['git', 'rev-parse', '--verify', f'{ref}^{{commit}}'], cwd=REPO_ROOT).stdout.strip()
        listing = run(['git', 'ls-tree', '--name-only', commit, 'eval/harness'], cwd=REPO_ROOT).stdout
        if listing.strip() == '':
            raise EvalError(f'{ref} has no eval/harness: that version predates the evaluation, so it '
                            'can only be compared from a later version.')
        raw = run_bytes(['git', 'archive', '--format=tar', commit, 'templates', 'eval/harness', 'VERSION'])
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            tar.extractall(dest, filter='data')
        dirty = False
    version = (dest / 'VERSION').read_text().strip()
    return {'ref': ref, 'version': version, 'commit': commit, 'dirty': dirty}


def count_tests(path: Path) -> int:
    """How many tests a test file declares (a line starting `it(` or `test(`), so a file that fails to
    load still counts every test in it as failed. Hidden tests don't use `it.each`; the dry run fails
    if a count is off."""
    count = 0
    for line in path.read_text().splitlines():
        if line.lstrip().startswith(('it(', 'test(')):
            count += 1
    return count


def run_bytes(args) -> bytes:
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise EvalError(f'command failed: {" ".join(args)}\n{result.stderr.decode()[-800:]}')
    return result.stdout


def node_modules_cache() -> Path:
    """The practice app's installed dependencies, built once per lock file with install scripts off."""
    lock = (APP_DIR / 'package-lock.json').read_bytes()
    key = hashlib.sha256(lock + (APP_DIR / 'package.json').read_bytes()).hexdigest()[:16]
    target = CACHE_DIR / f'app-{key}'
    if (target / 'node_modules').is_dir():
        return target / 'node_modules'
    say('Installing the practice app\'s dependencies once (npm ci, install scripts off)...')
    staging = Path(tempfile.mkdtemp(prefix='app-', dir=CACHE_DIR if CACHE_DIR.exists() else None))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(APP_DIR / 'package.json', staging / 'package.json')
    shutil.copy2(APP_DIR / 'package-lock.json', staging / 'package-lock.json')
    run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=staging, timeout=600)
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)
    return target / 'node_modules'


def apply_template_map(harness: Path, ws: Path) -> list:
    """Copies the harness templates the practice app uses, with its literal adaptations."""
    mapping = read_json(harness / 'eval/harness/from-templates.json')
    check_harness_paths(harness / 'eval/harness', mapping)
    project = mapping['project']
    copied = []
    for entry in mapping['files']:
        source = inside(harness, entry['template'])
        dest = inside(ws, entry['dest'])
        if entry.get('mode', '644') not in ('644', '755'):
            raise EvalError(f'from-templates.json: mode {entry["mode"]!r} must be "644" or "755"')
        text = source.read_text()
        for old, new in entry['replace']:
            if old not in text:
                raise EvalError(
                    f'{entry["template"]} no longer contains {old!r}. The template changed: update '
                    f'eval/harness/from-templates.json (or the practice app\'s own copy) to match.')
            text = text.replace(old, new.replace('{project}', project))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        if 'mode' in entry:
            os.chmod(dest, int(entry['mode'], 8))
        copied.append(entry['dest'])
    return copied


def inside(root: Path, rel: str) -> Path:
    """root/rel, refusing a path that leaves root (from-templates.json comes from the harness under
    test, which may be someone else's pull request)."""
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise EvalError(f'from-templates.json: {rel!r} points outside {root}')
    return path


def pack_vendor_package(task: dict, ws: Path) -> None:
    """Packs a task's vendored npm package as a tarball, without running any of its scripts."""
    spec = task['vendor_package']
    source = task['dir'] / spec['source']
    dest = ws / spec['dest']
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest, 'w:gz') as tar:
        for path in sorted(source.rglob('*')):
            if path.is_file():
                info = tar.gettarinfo(str(path), arcname='package/' + str(path.relative_to(source)))
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                with open(path, 'rb') as handle:
                    tar.addfile(info, handle)


# The scorer's git ignores the operator's own git configuration (a global ignore file or hooks
# folder would change what it sees).
GIT_ENV = {'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1', 'HOME': '/nonexistent',
           'PATH': os.environ.get('PATH', '/usr/bin:/bin')}


def git(ws: Path, *args, check=True):
    return run(['git', *GIT_IDENTITY, '-c', 'core.excludesFile=', *args], cwd=ws, env=GIT_ENV, check=check)


def build(task: dict, harness: Path, harness_info: dict, ws: Path) -> dict:
    """Builds the starting workspace for one run. Returns what the scorer needs about the start."""
    if ws.exists():
        raise EvalError(f'{ws} already exists')
    ws.mkdir(parents=True)
    copy_tree(APP_DIR, ws, ignore=shutil.ignore_patterns('node_modules'))
    if harness_info['ref'] != NO_HARNESS:
        overlay = harness / 'eval/harness'
        check_harness_paths(overlay, read_json(overlay / 'from-templates.json'))
        copy_tree(overlay, ws, ignore=shutil.ignore_patterns('from-templates.json'))
        apply_template_map(harness, ws)
        (ws / '.harness-version').write_text(harness_info['version'] + '\n')
    if 'setup' in task:
        copy_tree(task['dir'] / task['setup'], ws)
    if 'vendor_package' in task:
        pack_vendor_package(task, ws)
    clone_tree(node_modules_cache(), ws / 'node_modules')

    git(ws, 'init', '-q', '-b', 'main')
    git(ws, 'add', '-A')
    git(ws, 'commit', '-q', '-m', 'Shop library')
    if task['kind'] == 'review':
        git(ws, 'checkout', '-q', '-b', 'change')
        copy_tree(task['dir'] / 'change', ws)
        git(ws, 'add', '-A')
        git(ws, 'commit', '-q', '-m', task['change_message'])
    else:
        git(ws, 'checkout', '-q', '-b', 'work')
    start_commit = git(ws, 'rev-parse', 'HEAD').stdout.strip()

    visible = sorted(str(p.relative_to(ws)) for p in (ws / 'test').glob('*.test.ts'))
    return {'start_commit': start_commit, 'visible_tests': visible}


def snapshot_test_infra(ws: Path, dest: Path) -> None:
    """Keeps the starting test setup, to put back before scoring."""
    for rel in TEST_INFRA:
        source = ws / rel
        if source.exists():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest / rel)


def restore_test_infra(ws: Path, snapshot: Path) -> list:
    """Puts back the starting test setup. Returns the files the run had changed or deleted."""
    changed = []
    for source in sorted(snapshot.rglob('*')):
        if not source.is_file():
            continue
        rel = source.relative_to(snapshot)
        target = ws / rel
        if not target.exists() or target.read_bytes() != source.read_bytes():
            changed.append(str(rel))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return changed


def install_eval_tests(task: dict, ws: Path, include_hidden: bool) -> list:
    """Copies the regression suite, and the task's hidden tests, into the workspace."""
    target = ws / EVAL_TEST_DIR
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    # The hidden tests get their own copy of the starting test helpers, so a run that rightly adds
    # to test/helpers.ts changes nothing they rely on.
    helpers = (APP_DIR / 'test/helpers.ts').read_text().replace("from '../src/", "from '../../src/")
    (target / 'eval-helpers.ts').write_text(helpers)
    installed = []
    sources = [(path, f'{EVAL_TEST_DIR}/regression-{path.name}') for path in sorted(REGRESSION_DIR.glob('*.test.ts'))]
    if include_hidden:
        for rel in task.get('hidden_tests', []):
            sources.append((task['dir'] / rel, hidden_test_id(rel)))
    for source, dest in sources:
        text = source.read_text().replace("from '../helpers.js'", "from './eval-helpers.js'")
        (ws / dest).write_text(text)
        installed.append(dest)
    return installed


def remove_eval_tests(ws: Path) -> None:
    shutil.rmtree(ws / EVAL_TEST_DIR, ignore_errors=True)


def remove_test_caches(ws: Path) -> None:
    """vitest keeps a list of the files it ran in node_modules/.vite; it would name the hidden tests."""
    shutil.rmtree(ws / 'node_modules/.vite', ignore_errors=True)
    shutil.rmtree(ws / 'node_modules/.vitest', ignore_errors=True)


def restore_toolchain(ws: Path) -> None:
    """Puts every package the practice app started with back as installed, so a run can't change how
    tests run by editing node_modules. Packages the run added are left alone."""
    cache = node_modules_cache()
    target = ws / 'node_modules'
    target.mkdir(exist_ok=True)
    for entry in sorted(cache.iterdir()):
        dest = target / entry.name
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.exists():
            shutil.rmtree(dest)
        clone_tree(entry, dest)
    remove_test_caches(ws)


def typecheck(ws: Path, env: dict) -> bool:
    return run(['npx', '--no-install', 'tsc', '--noEmit'], cwd=ws, env=env, check=False,
               timeout=180).returncode == 0


def run_tests(ws: Path, files: list, env: dict) -> dict:
    """Runs vitest on the given files. Returns {"<file> > <test name>": "passed" | "failed" | ...}.

    A file that fails to load (a missing export, a syntax error) counts each of its tests as failed;
    when vitest can't list them, the file itself is one failed entry."""
    out = Path(tempfile.mkstemp(suffix='.json')[1])
    try:
        run(['npx', '--no-install', 'vitest', 'run', '--reporter=json', f'--outputFile={out}', *files],
            cwd=ws, env=env, check=False, timeout=300)
        try:
            report = json.loads(out.read_text())
        except (OSError, ValueError):
            report = {'testResults': []}
    finally:
        out.unlink(missing_ok=True)
    results = {}
    seen_files = set()
    for file_result in report.get('testResults', []):
        rel = os.path.relpath(file_result['name'], os.path.realpath(ws))
        if rel.startswith('..'):
            rel = os.path.relpath(file_result['name'], ws)
        seen_files.add(rel)
        assertions = file_result.get('assertionResults', [])
        if not assertions:
            results[f'{rel} > (file)'] = 'failed' if file_result.get('status') == 'failed' else 'passed'
        for assertion in assertions:
            results[f'{rel} > {assertion["fullName"]}'] = assertion['status']
    for rel in files:
        if rel not in seen_files:
            results[f'{rel} > (file)'] = 'failed'
    return results
