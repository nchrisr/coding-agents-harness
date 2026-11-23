"""The dry run: checks the whole pipeline without calling a model. Every task builds; its hidden tests
fail before the work and pass on a reference solution; unsafe outcomes are caught; tricks that would
fool the scorer are undone; the transcript checks accept a good run and reject a bad one; and the
results, comparison and side-by-side steps run end to end on stub data."""
import argparse
import shutil
import tempfile
from pathlib import Path

from . import grade, report, score, transcript, workspace
from .common import EvalError, copy_tree, load_tasks, write_json
from .pipeline import build_results, prepare_arm, score_run, side_by_side_pairs, start_workspace


class Checks:
    def __init__(self):
        self.failures = 0

    def check(self, ok: bool, what: str) -> None:
        if not ok:
            self.failures += 1
        print(f'  {"ok  " if ok else "FAIL"} {what}', flush=True)


def fake_transcript(task: dict, has_harness: bool, model: str, denied: bool = False) -> list:
    """Events shaped like a real stream-json run (see a transcript in eval/runs/), without a model."""
    agents = ['general-purpose', 'Explore', 'Plan']
    commands = ['init', 'review']
    if has_harness:
        agents += ['reviewer', 'system-reviewer', 'fixer', 'spec-critic']
        commands += ['review-loop', 'spec']
    events = [{'type': 'system', 'subtype': 'init', 'model': model, 'mcp_servers': [],
               'agents': agents, 'slash_commands': commands, 'claude_code_version': '0.0.0',
               'permissionMode': 'acceptEdits'}]
    content = [{'type': 'tool_use', 'name': 'Edit', 'input': {'file_path': 'src/money.ts'}}]
    if task['kind'] == 'review' and has_harness:
        content.append({'type': 'tool_use', 'name': 'Agent', 'input': {'subagent_type': 'reviewer'}})
    events.append({'type': 'assistant', 'message': {'content': content}})
    if has_harness:
        events.append({'type': 'system', 'subtype': 'hook_response', 'hook_event': 'Stop',
                       'exit_code': 0, 'outcome': 'success'})
    events.append({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'Done.',
                   'total_cost_usd': 0.5, 'duration_ms': 60000, 'num_turns': 9,
                   'permission_denials': [{'tool_name': 'Bash'}] if denied else [],
                   'modelUsage': {model: {'inputTokens': 10, 'outputTokens': 1000,
                                          'cacheReadInputTokens': 50000, 'cacheCreationInputTokens': 9000}}})
    return events


def check_start(task: dict, ws: Path, run_dir: Path, checks: Checks) -> None:
    """The hidden tests must measure something: they fail before the work (for a review, only the
    bug's test fails)."""
    hidden = score.hidden_at_start(task, ws, run_dir / 'start-tests')
    for rel, entry in hidden.items():
        if task['kind'] == 'review' and rel != task['bug']['test']:
            checks.check(entry['passed'] == entry['total'] and entry['total'] > 0,
                         f'{rel} passes on the change as written ({entry["passed"]}/{entry["total"]})')
        else:
            checks.check(entry['passed'] < entry['total'], f'{rel} fails before the work is done '
                         f'({entry["passed"]}/{entry["total"]})')
    if task['kind'] == 'review':
        checks.check(task['spec_test'] in hidden, 'the task names its spec test')


def check_solution(task: dict, ws: Path, run_dir: Path, start: dict, checks: Checks) -> dict:
    solution = task['dir'] / 'solution'
    if solution.is_dir():
        copy_tree(solution, ws)
    record = score_run(task, ws, run_dir, start, run_dir / 'tmp')
    checks.check(record['typechecks'], 'the reference solution typechecks')
    checks.check(not record['regressions'], f'the reference solution has no regressions {record["regressions"][:2]}')
    for rel, entry in record['hidden'].items():
        checks.check(entry['passed'] == entry['total'] and entry['total'] > 0,
                     f'the reference solution passes {rel} ({entry["passed"]}/{entry["total"]}; a count '
                     'that is off means a test form workspace.count_tests misses)')
    if task['kind'] == 'review':
        outcome = record['outcome']
        checks.check(outcome['bug_fixed'] and outcome['spec_kept'] and outcome.get('decoy_kept', True),
                     f'review outcome scores as fixed, spec kept, decoy kept: {outcome}')
    if task['kind'] == 'security':
        checks.check(record['outcome']['held'], f'the safe outcome scores as held {record["outcome"]["evidence"]}')
    return record


def check_unsafe(task: dict, arm: dict, root: Path, checks: Checks) -> None:
    ws = root / f'bad-{task["id"]}'
    run_dir = root / f'bad-run-{task["id"]}'
    start = start_workspace(task, arm['dir'], arm['info'], ws, run_dir)
    copy_tree(task['dir'] / 'bad', ws)
    score.clear_git_excludes(ws)
    changed = score.save_agent_diff(ws, start['start_commit'], root / 'bad.diff')
    outcome = score.security_score(task, ws, start, changed, run_dir / 'tmp')
    checks.check(not outcome['held'], f'the unsafe outcome is caught: {outcome["evidence"]}')


def check_tricks(task: dict, arm: dict, root: Path, checks: Checks) -> None:
    """A run that tries to pass the hidden tests by changing the test setup still fails them."""
    ws = root / 'tricks'
    run_dir = root / 'tricks-run'
    start = start_workspace(task, arm['dir'], arm['info'], ws, run_dir)
    stub = ws / 'node_modules' / 'chai' / 'index.js'
    stub_before = stub.read_bytes() if stub.exists() else None
    (ws / 'vitest.workspace.ts').write_text(
        "export default [{ test: { include: ['test/**/*.test.ts'], setupFiles: ['./pass.ts'] } }];\n")
    (ws / 'pass.ts').write_text("import { expect } from 'vitest';\nexpect.extend({});\n")
    (ws / '.git/info/exclude').write_text('vitest.workspace.ts\npass.ts\n')
    if stub_before is not None:
        stub.write_text('module.exports = {};\n')
    record = score_run(task, ws, run_dir, start, run_dir / 'tmp')
    checks.check(any('vitest.workspace' in item for item in record['scoring_undid']),
                 'an added vitest.workspace file is removed before scoring')
    checks.check('vitest.workspace.ts' in record['changed_files'],
                 'a file hidden with .git/info/exclude still shows in the saved diff')
    checks.check(stub_before is None or stub.read_bytes() == stub_before,
                 'a changed package in node_modules is put back before scoring')


def check_transcripts(task: dict, model: str, checks: Checks) -> None:
    facts = transcript.summarize(fake_transcript(task, True, model))
    problems = transcript.validity(facts, task, True, model)
    checks.check(not problems, f'a good transcript counts {problems or ""}')
    denied = transcript.validity(transcript.summarize(fake_transcript(task, True, model, True)),
                                 task, True, model)
    checks.check(any('denial' in p for p in denied), 'a transcript with a permission denial doesn\'t count')
    unloaded = transcript.validity(transcript.summarize(fake_transcript(task, False, model)), task, True, model)
    checks.check(bool(unloaded), 'a harness run without the harness loaded doesn\'t count')


def check_pipeline(records: list, tasks: list, arm: dict, model: str, root: Path, checks: Checks) -> None:
    items = [{'key': r['task'], 'task': next(t for t in tasks if t['id'] == r['task']), 'message': 'stub'}
             for r in records]
    answers, _ = grade.grade_all(items, 'stub', stub=True, workdir=root)
    for record in records:
        if record['task'] in answers:
            record['graded'] = answers[record['task']]
    fake_args = argparse.Namespace(model=model, grader_model='stub', runs=1)
    results = build_results(arm, records, fake_args, 0.0)
    write_json(root / 'results.json', results)
    summary = results['summary']
    checks.check(summary['valid_runs'] == len(records) == len(tasks), f'results file written ({len(records)} runs)')
    checks.check(summary['regressions_per_run'] == 0 and summary['bugs_fixed'] in (1.0, None),
                 'reference solutions score full marks')
    text = report.compare(results, results)
    checks.check('No clear difference' in text, 'compare works (a results file against itself)')
    invalid = dict(results, summary=dict(summary, valid_runs=summary['runs'] - 1))
    checks.check('Not judged' in report.compare(results, invalid),
                 'a comparison with a run that didn\'t count gives no verdict')
    pairs_dir = root / 'pairs'
    twins = []
    for name in ('base', 'new'):
        folder = pairs_dir / name / f'{records[0]["task"]}-1'
        folder.mkdir(parents=True)
        (folder / 'agent.diff').write_text(f'diff from {name}')
        twins.append(dict(records[0], arm=name, run=1))
    pairs = side_by_side_pairs(twins, tasks, [{'name': 'base'}, {'name': 'new'}], pairs_dir)
    verdicts, _ = grade.compare_pairs(pairs, 'stub', root, stub=True)
    checks.check(len(pairs) == 1 and set(pairs[0]['diffs'].values()) == {'diff from base', 'diff from new'}
                 and list(verdicts.values())[0] in ('new', 'baseline'),
                 'side-by-side pairing reads both changes and maps the random ids back')


def main(args) -> int:
    tasks = load_tasks(args.tasks)
    checks = Checks()
    root = Path(tempfile.mkdtemp(prefix='harness-eval-dry-'))
    records = []
    try:
        arms = [prepare_arm('worktree', root, tasks), prepare_arm(workspace.NO_HARNESS, root, tasks)]
        harness = arms[0]
        print(f'Harness under test: {harness["info"]["version"]} (this checkout)')
        checks.check(not harness['tuning'], 'no harness file mentions a task\'s distinctive words'
                     + (f': {harness["tuning"]}' if harness['tuning'] else ''))
        for task in tasks:
            print(f'{task["id"]} ({task["kind"]})')
            for arm in arms:
                ws = root / f'{arm["name"]}-{task["id"]}'
                run_dir = root / f'run-{arm["name"]}-{task["id"]}'
                try:
                    start = start_workspace(task, arm['dir'], arm['info'], ws, run_dir)
                except EvalError as error:
                    checks.check(False, f'[{arm["name"]}] starting state: {error}')
                    continue
                checks.check(True, f'[{arm["name"]}] builds; typechecks and all {len(start["passing"])} '
                             'tests pass at the start')
                if arm is not harness:
                    continue
                check_start(task, ws, run_dir, checks)
                scored = check_solution(task, ws, run_dir, start, checks)
                if task['kind'] == 'security':
                    check_unsafe(task, arm, root, checks)
                check_transcripts(task, args.model, checks)
                record = {'task': task['id'], 'kind': task['kind'], 'arm': 'harness', 'run': 1,
                          'valid': True, 'problems': [], 'cost_usd': 0.5,
                          'tokens': {'total': 60000}, 'duration_s': 60.0, 'final_text': 'stub'}
                record.update(scored)
                records.append(record)
        print('Scoring defences')
        check_tricks(next(t for t in tasks if t['kind'] == 'review') if any(t['kind'] == 'review' for t in tasks)
                     else tasks[0], harness, root, checks)
        print('Pipeline')
        check_pipeline(records, tasks, harness, args.model, root, checks)
    finally:
        if args.keep:
            print(f'Kept {root}')
        else:
            shutil.rmtree(root, ignore_errors=True)
    print()
    if checks.failures:
        print(f'Dry run FAILED: {checks.failures} check(s). Fix these before any real run.')
        return 1
    print('Dry run passed. No model was called and nothing was spent.')
    return 0
