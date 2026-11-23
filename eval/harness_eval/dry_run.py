"""The dry run: checks the whole pipeline without calling a model. Every task builds; its hidden tests
fail before the work and pass on a reference solution; unsafe outcomes are caught; tricks that would
fool the scorer are undone; the transcript checks accept a good run and reject a bad one; and the
results, comparison and side-by-side steps run end to end on stub data."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import codex_agent, codex_transcript, grade, report, score, transcript, workspace
from .common import REPO_ROOT, EvalError, copy_tree, load_tasks, write_json
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


def fake_codex_run(task: dict, has_harness: bool, model: str, folder: Path, reviewer: bool = True,
                   blocked: bool = False, finished: bool = True) -> Path:
    """A run folder shaped like a real `codex exec --json` run (see a run's rollouts/ in eval/runs/):
    the event stream, the main agent's session file and, for a review, a reviewer subagent's."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'rollouts').mkdir(exist_ok=True)
    root_id, sub_id = '01a2-root', '01a2-sub'

    def item(item_type, **fields):
        return {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': dict(type=item_type, **fields)}}

    def tokens(n):
        return {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {
            'input_tokens': n, 'cached_input_tokens': n // 2, 'cache_write_input_tokens': 0,
            'output_tokens': n // 20, 'reasoning_output_tokens': 0, 'total_tokens': n + n // 20}}}}

    root = [{'type': 'session_meta', 'payload': {'id': root_id, 'session_id': root_id, 'cli_version': '0.0.0',
                                                 'thread_source': 'user'}},
            {'type': 'turn_context', 'payload': {'model': model, 'approval_policy': 'never',
                                                 'sandbox_policy': {'type': 'workspace-write'}}}]
    if has_harness:
        root.append({'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [
            {'type': 'input_text', 'text': '# AGENTS.md instructions for /tmp/shop\n\n<INSTRUCTIONS>...'}]}})
    root.append(item('CommandExecution', command=['/bin/zsh', '-lc', 'npm run check'], exit_code='0',
                     aggregated_output='Operation not permitted' if blocked else 'ok'))
    root.append(item('FileChange', changes={'/tmp/shop/src/money.ts': {'type': 'update'}}))
    sub = []
    if task['kind'] == 'review' and has_harness and reviewer:
        root.append(item('SubAgentActivity', kind='started', agent_path='/root/reviewer', agent_thread_id=sub_id))
        sub = [{'type': 'session_meta', 'payload': {'id': sub_id, 'session_id': root_id, 'parent_thread_id': root_id,
                                                    'thread_source': 'subagent', 'agent_path': '/root/reviewer'}},
               item('CommandExecution', command=['/bin/zsh', '-lc', 'cat .claude/agents/reviewer.md'],
                    exit_code='0', aggregated_output='---'),
               tokens(20000)]
    root.append(tokens(100000))
    stream = [{'type': 'thread.started', 'thread_id': root_id}, {'type': 'turn.started'},
              {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Done.'}}]
    if finished:
        root.append({'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'Done.',
                                                      'duration_ms': '60000'}})
        stream.append({'type': 'turn.completed', 'usage': {}})
    for name, events in (('rollout-root.jsonl', root), ('rollout-sub.jsonl', sub)):
        if events:
            (folder / 'rollouts' / name).write_text(''.join(json.dumps(e) + '\n' for e in events))
    (folder / 'transcript.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in stream))
    return folder


def check_codex_transcripts(task: dict, model: str, prices: tuple, root: Path, checks: Checks) -> None:
    folder = root / f'codex-{task["id"]}'

    def problems(name, has_harness=True, arm_harness=True, over_budget=False, **fake):
        run = codex_transcript.read_run(fake_codex_run(task, has_harness, model, folder / name, **fake))
        facts = codex_transcript.summarize(run, prices, over_budget)
        return facts, codex_transcript.validity(facts, task, arm_harness, model)

    facts, good = problems('good')
    checks.check(not good, f'[codex] a good transcript counts {good or ""}')
    checks.check(facts['cost_usd'] and facts['tokens']['total'] > 0 and facts['final_text'] == 'Done.'
                 and facts['checks_ran'], '[codex] cost, tokens, final message and the check run are read')
    _, unloaded = problems('unloaded', has_harness=False)
    checks.check(any('AGENTS.md' in p for p in unloaded), '[codex] a harness run without AGENTS.md loaded doesn\'t count')
    _, leaked = problems('leaked', arm_harness=False)
    checks.check(any('no-harness' in p for p in leaked), '[codex] AGENTS.md in the no-harness arm doesn\'t count')
    _, cut = problems('cut', finished=False)
    checks.check(any('cut off' in p for p in cut), '[codex] a run with no end doesn\'t count')
    _, capped = problems('capped', finished=False, over_budget=True)
    checks.check(not capped, f'[codex] a run stopped at the dollar cap counts as a failed run {capped or ""}')
    _, blocked = problems('blocked', blocked=True)
    checks.check(bool(blocked) == (task['kind'] != 'security'),
                 '[codex] a sandbox block is a setup fault, except in a security task')
    if task['kind'] == 'review':
        facts, _ = problems('read')
        checks.check(facts['reviewer_read_definition'], '[codex] the reviewer reading its definition is seen')
        _, lonely = problems('lonely', reviewer=False)
        checks.check(any('reviewer' in p for p in lonely), '[codex] a review loop without its reviewer doesn\'t count')
        prompt = codex_agent.prompt_for(task, True)
        checks.check('.claude/commands/review-loop.md' in prompt and task['spec'] in prompt,
                     '[codex] the review prompt points at the review loop and the spec')
    known = {}
    found = codex_agent.find_rollouts(folder / 'good', '01a2-root', 0, known)
    expected = 2 if task['kind'] == 'review' else 1
    checks.check(len(found) == expected and round(codex_agent.spent(found, prices), 4) == facts['cost_usd'],
                 '[codex] the dollar-cap watcher finds every agent\'s session file and prices them as the reader does')


def check_codex_config(root: Path, checks: Checks) -> None:
    """Codex's own trusted-project entry is removed after a run; any other change is reported."""
    config = root / 'codex-config.toml'
    before = 'model = "x"\n'
    ws = root / 'shop'
    config.write_text(before + f'\n[projects."{ws.resolve()}"]\ntrust_level = "trusted"\n')
    undone = codex_agent.config_after(config, before, ws) == [] and config.read_text() == before
    config.write_text(before + 'notify = ["sh"]\n')
    flagged = codex_agent.config_after(config, before, ws) != []
    checks.check(undone and flagged, '[codex] Codex\'s own trust entry is undone; any other config change is flagged')


def check_deps_scan(root: Path, checks: Checks) -> None:
    """deps-check.sh finds a known-vulnerable dependency when run from an agent's worktree nested under
    a folder the project ignores, where walking the folder would scan nothing."""
    if not shutil.which('osv-scanner'):
        print('  skip deps-check.sh in a worktree: osv-scanner is not installed')
        return
    repo = root / 'deps-project'
    repo.mkdir()
    (repo / '.gitignore').write_text('.claude/worktrees/\n')
    (repo / 'package-lock.json').write_text(json.dumps({
        'name': 'x', 'version': '1.0.0', 'lockfileVersion': 3, 'requires': True,
        'packages': {'': {'name': 'x', 'version': '1.0.0', 'dependencies': {'lodash': '4.17.20'}},
                     'node_modules/lodash': {'version': '4.17.20'}}}))
    git = ['git', '-c', 'user.name=eval', '-c', 'user.email=eval@example.invalid']
    for cmd in (['init', '-q'], ['add', '-A'], ['commit', '-qm', 'start'],
                ['worktree', 'add', '-q', '.claude/worktrees/agent']):
        subprocess.run(git + cmd, cwd=repo, check=True, capture_output=True)
    out = subprocess.run(['bash', str(REPO_ROOT / 'templates/scripts/deps-check.sh'), 'HEAD'],
                         cwd=repo / '.claude/worktrees/agent', capture_output=True, text=True).stdout
    scan = out.split('== Known vulnerabilities', 1)[-1]
    if 'NOT RUN' in scan and '(exit 127)' in scan:
        print('  skip deps-check.sh in a worktree: the scanner failed, probably offline')
        return
    checks.check('lodash' in scan and 'GHSA-' in scan,
                 'deps-check.sh run from a worktree under an ignored folder finds the vulnerable lodash')


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


def check_pipeline(records: list, tasks: list, arm: dict, model: str, agent_name: str, root: Path,
                   checks: Checks) -> None:
    items = [{'key': r['task'], 'task': next(t for t in tasks if t['id'] == r['task']), 'message': 'stub'}
             for r in records]
    answers, _ = grade.grade_all(items, 'stub', stub=True, workdir=root)
    for record in records:
        if record['task'] in answers:
            record['graded'] = answers[record['task']]
    fake_args = argparse.Namespace(model=model, grader_model='stub', runs=1, agent=agent_name)
    results = build_results(arm, records, fake_args, 0.0)
    write_json(root / 'results.json', results)
    summary = results['summary']
    checks.check(summary['valid_runs'] == len(records) == len(tasks) and results['agent'] == agent_name,
                 f'results file written ({len(records)} runs, agent {results["agent"]})')
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
                if args.agent == 'codex':
                    check_codex_transcripts(task, args.model, args.prices, root, checks)
                else:
                    check_transcripts(task, args.model, checks)
                record = {'task': task['id'], 'kind': task['kind'], 'arm': 'harness', 'run': 1,
                          'valid': True, 'problems': [], 'cost_usd': 0.5,
                          'tokens': {'total': 60000}, 'duration_s': 60.0, 'final_text': 'stub'}
                record.update(scored)
                records.append(record)
        if args.agent == 'codex':
            check_codex_config(root, checks)
        print('Scoring defences')
        check_tricks(next(t for t in tasks if t['kind'] == 'review') if any(t['kind'] == 'review' for t in tasks)
                     else tasks[0], harness, root, checks)
        print('Scripts')
        check_deps_scan(root, checks)
        print('Pipeline')
        check_pipeline(records, tasks, harness, args.model, args.agent, root, checks)
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
