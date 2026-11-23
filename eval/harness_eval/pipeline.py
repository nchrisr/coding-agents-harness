"""The steps every run shares, used by both a real run (run.py) and the dry run."""
import datetime
from pathlib import Path

from . import agent, codex_agent, report, score, workspace
from .common import RESULTS_DIR, EvalError

SCHEMA = 1


def arm_name(ref: str) -> str:
    return 'no-harness' if ref == workspace.NO_HARNESS else 'harness'


def results_path(info: dict, agent_name: str = 'claude') -> Path:
    """Claude Code's files keep their names; another agent's carry its name, so the two never mix."""
    suffix = '' if agent_name == 'claude' else f'-{agent_name}'
    if info['ref'] == workspace.NO_HARNESS:
        return RESULTS_DIR / f'no-harness{suffix}.json'
    return RESULTS_DIR / f'{info["version"]}{suffix}.json'


def start_workspace(task: dict, harness_dir: Path, info: dict, ws: Path, run_dir: Path) -> dict:
    """Builds the workspace and records its starting state. Stops if the start is already broken,
    which is a fault in the evaluation, not the harness."""
    start = workspace.build(task, harness_dir, info, ws)
    base = score.baseline(task, ws, start, run_dir / 'start-tests')
    problems = []
    if not base['typechecks']:
        problems.append('the starting app has a type error')
    if base['failing']:
        problems.append(f'tests fail before the run starts: {base["failing"][:3]}')
    if problems:
        raise EvalError(f'{task["id"]}: {"; ".join(problems)}. This is a fault in the evaluation, '
                        'not the harness: run `python3 eval/run.py dry-run`.')
    start.update(base)
    return start


def score_run(task: dict, ws: Path, run_dir: Path, start: dict, run_tmp: Path) -> dict:
    """Scores what a run left in ws. The order matters: git exclude rules are emptied before the diff
    is saved, so nothing is hidden from it; the security checks read the workspace as the run left it;
    then the scorer undoes anything that could change how tests run, and runs them."""
    score.clear_git_excludes(ws)
    changed = score.save_agent_diff(ws, start['start_commit'], run_dir / 'agent.diff')
    record = {'changed_files': changed}
    if task['kind'] == 'security':
        record['outcome'] = score.security_score(task, ws, start, changed, run_tmp)
    record['scoring_undid'] = score.sanitize(ws, run_dir / 'start-tests')
    tests = score.tests_score(ws, task, start, run_dir / 'start-tests')
    record.update(tests)
    if task['kind'] == 'review':
        record['outcome'] = score.review_score(task, tests)
    return record


def prepare_arm(ref: str, root: Path, tasks: list) -> dict:
    label = ref.replace('/', '_')
    harness_dir = root / ('harness-' + label)
    info = workspace.harness_source(ref, harness_dir)
    if ref in ('worktree', workspace.NO_HARNESS):
        name = arm_name(ref)
    else:
        name = f'{info["version"]}@{label}'
    return {'name': name, 'ref': ref, 'dir': harness_dir, 'info': info,
            'tuning': report.tuning_warnings(harness_dir, tasks)}


def side_by_side_pairs(records: list, tasks: list, arms: list, out_dir: Path) -> list:
    """Each arm's change paired with the baseline's on the same task and run number, both valid."""
    baseline = arms[0]['name']
    by_key = {(r['arm'], r['task'], r['run']): r for r in records}
    pairs = []
    for arm in arms[1:]:
        for record in records:
            if record['arm'] != arm['name'] or not record['valid']:
                continue
            base = by_key.get((baseline, record['task'], record['run']))
            if base is None or not base['valid']:
                continue
            task = next(t for t in tasks if t['id'] == record['task'])
            diffs = {}
            for who, rec in (('baseline', base), (arm['name'], record)):
                path = out_dir / rec['arm'] / f'{rec["task"]}-{rec["run"]}' / 'agent.diff'
                diffs[who] = path.read_text(errors='replace') if path.exists() else ''
            pairs.append({'key': f'{arm["name"]}/{record["task"]}/{record["run"]}', 'arm': arm['name'],
                          'task': task, 'diffs': diffs})
    return pairs


def build_results(arm: dict, records: list, args, grading_usd: float) -> dict:
    agent_name = getattr(args, 'agent', 'claude')
    version_field = 'codex_version' if agent_name == 'codex' else 'claude_code_version'
    versions = sorted({r.get(version_field) for r in records if r.get(version_field)})
    return {
        'schema': SCHEMA,
        'arm_name': arm['name'],
        'eval_changes': arm.get('eval_changes', []),
        'arm': 'no-harness' if arm['info']['ref'] == workspace.NO_HARNESS else 'harness',
        'harness': arm['info'],
        'model': args.model,
        'grader_model': args.grader_model,
        'agent': agent_name,
        version_field: versions[0] if len(versions) == 1 else versions,
        'auth': codex_agent.auth_mode() if agent_name == 'codex' else agent.auth_mode(),
        'date': datetime.date.today().isoformat(),
        'runs_per_task': args.runs,
        'tasks': sorted({r['task'] for r in records}),
        'fingerprint': report.fingerprint(),
        'tuning_warnings': arm['tuning'],
        'summary': report.summarize(records),
        'grading_usd': round(grading_usd, 4),
        'invalid_runs': [f'{r["task"]}#{r["run"]}: {"; ".join(r["problems"])}' for r in records if not r['valid']],
        'runs': records,
    }
