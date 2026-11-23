#!/usr/bin/env python3
"""The harness evaluation. Read eval/README.md first: real runs cost money.

  python3 eval/run.py dry-run                      check the whole pipeline, no model calls
  python3 eval/run.py run                          evaluate this checkout's harness (2 runs per task)
  python3 eval/run.py run --compare-to origin/main this checkout and main, interleaved, then compare
  python3 eval/run.py compare [NEW.json] [OLD.json]
"""
import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_eval import agent, dry_run, grade, report, transcript, workspace  # noqa: E402
from harness_eval.pipeline import (build_results, prepare_arm, results_path, score_run,  # noqa: E402
                                  side_by_side_pairs, start_workspace)
from harness_eval.common import (RESULTS_DIR, RUNS_DIR, EvalError, load_tasks,  # noqa: E402
                                 read_json, say, write_json)

DEFAULT_MODEL = 'claude-sonnet-5-5'
DEFAULT_GRADER = 'claude-haiku-5-5'


# ---------------------------------------------------------------- one run

class Budget:
    """Stops starting new runs once the total spent passes the limit."""

    def __init__(self, limit: float):
        self.limit = limit
        self.spent = 0.0
        self.lock = threading.Lock()

    def add(self, amount) -> None:
        with self.lock:
            self.spent += amount or 0.0

    def exhausted(self) -> bool:
        with self.lock:
            return self.spent >= self.limit


def one_run(job: dict, args, budget: Budget, out_dir: Path) -> dict:
    task, arm, n = job['task'], job['arm'], job['n']
    label = f'{arm["name"]}/{task["id"]}#{n}'
    record = {'task': task['id'], 'kind': task['kind'], 'arm': arm['name'], 'run': n}
    if budget.exhausted():
        record.update({'valid': False, 'problems': ['skipped: the total budget was used up'],
                       'cost_usd': None})
        return record
    if task.get('needs_network') and not network_ok():
        record.update({'valid': False, 'problems': ['skipped: the npm registry is unreachable'],
                       'cost_usd': None})
        return record
    run_dir = out_dir / arm['name'] / f'{task["id"]}-{n}'
    run_dir.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='harness-eval-'))
    ws = scratch / 'shop'
    try:
        start = start_workspace(task, arm['dir'], arm['info'], ws, run_dir)
        has_harness = arm['info']['ref'] != workspace.NO_HARNESS
        prompt = agent.prompt_for(task, has_harness)
        say(f'  start {label}')
        ran = agent.run_agent(ws, scratch / 'run', prompt, args.model, args.max_usd_per_run,
                              args.timeout_minutes * 60)
        shutil.move(str(scratch / 'run' / 'transcript.jsonl'), run_dir / 'transcript.jsonl')
        shutil.move(str(scratch / 'run' / 'stderr.txt'), run_dir / 'stderr.txt')
        facts = transcript.summarize(transcript.read_events(run_dir / 'transcript.jsonl'))
        budget.add(facts['cost_usd'])
        problems = transcript.validity(facts, task, has_harness, args.model)
        # Running out of money or time is the arm's failure, not a fault in the setup: the run
        # counts, and scores whatever it left.
        if ran['timed_out']:
            problems = [p for p in problems if not p.startswith('no result event')]
            record['cut_off'] = f'timed out after {args.timeout_minutes} minutes'
        elif facts['refused']:
            record['cut_off'] = 'refused by the API\'s usage policy before the agent acted'
        elif facts['result_subtype'] and facts['result_subtype'].startswith('error_max'):
            record['cut_off'] = facts['result_subtype']
        if ran['home_touched']:
            problems.append(f'changed files in your real home folder: {ran["home_touched"]}')
            say(f'  WARNING {label} changed {ran["home_touched"]} in your home folder. Look at them now.')
        record.update(score_run(task, ws, run_dir, start, scratch / 'run' / 'tmp'))
        record.update({
            'valid': not problems,
            'problems': problems,
            'cost_usd': facts['cost_usd'],
            'tokens': facts['tokens'],
            'duration_s': facts['duration_s'],
            'wall_s': ran['wall_seconds'],
            'turns': facts['turns'],
            'tool_calls': facts['tool_calls'],
            'tool_counts': facts['tool_counts'],
            'subagents': facts['subagents'],
            'hooks': len(facts['hooks']),
            'model_seen': facts['init']['model'],
            'claude_code_version': facts['init']['claude_code_version'],
            'auth': ran['auth'],
            'final_text': facts['final_text'][:12000],
        })
        state = 'ok' if not problems else 'DOESN\'T COUNT: ' + '; '.join(problems)
        say(f'  done  {label}: ${facts["cost_usd"] or 0:.2f}, {facts["duration_s"]}s, {state}')
    except EvalError as error:
        record.update({'valid': False, 'problems': [f'evaluation error: {error}'], 'cost_usd': None})
        say(f'  error {label}: {error}')
    except Exception:  # noqa: BLE001 - one broken run must not lose the others
        record.update({'valid': False, 'problems': ['crash: ' + traceback.format_exc()[-600:]],
                       'cost_usd': None})
        say(f'  crash {label}: see the results file')
    finally:
        if args.keep:
            say(f'  kept workspace {ws}')
        else:
            shutil.rmtree(scratch, ignore_errors=True)
    return record


_network = {}


def network_ok() -> bool:
    if 'ok' not in _network:
        probe = subprocess.run(['npm', 'view', 'lodash@4.17.21', 'version'], capture_output=True,
                               text=True, timeout=60)
        _network['ok'] = probe.returncode == 0
    return _network['ok']


# ---------------------------------------------------------------- whole evaluation

def evaluate(args) -> int:
    tasks = load_tasks(args.tasks)
    if agent.auth_mode() == 'login' and not args.use_my_login:
        raise EvalError(
            'No ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN is set. With one, each run gets a '
            'throwaway home folder. Without one, runs share your real home folder, and some tasks '
            'tempt the agent to install hooks; each run then checks your shell, git, npm and Claude '
            'settings before and after, but nothing stops a write. Make a token with `claude '
            'setup-token` and export it, or pass --use-my-login to accept that.')
    if args.runs < 2:
        say('Note: fewer than 2 runs per task. Fine for checking the setup; too few to judge a change.')
    if args.variants and not args.compare_to:
        raise EvalError('--variants needs --compare-to: the baseline every variation is judged against.')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    out_dir = RUNS_DIR / stamp
    root = Path(tempfile.mkdtemp(prefix='harness-eval-src-'))
    # The first arm is the baseline when there is one; the rest are judged against it.
    refs = []
    if args.compare_to:
        refs.append(args.compare_to)
    refs.append(args.harness)
    refs.extend(args.variants or [])
    arms = []
    for ref in refs:
        arm = prepare_arm(ref, root, tasks)
        while any(other['name'] == arm['name'] for other in arms):
            arm['name'] += "'"
        arms.append(arm)
    side_by_side = len(arms) > 1
    if args.compare_to and args.compare_to != workspace.NO_HARNESS:
        note = eval_changed_since(args.compare_to)
        if note:
            say(f'Note: {note}')
            for arm in arms:
                arm['eval_changes'] = [note]
    for arm in arms:
        if side_by_side:
            # A side-by-side run is for judging one change; its files stay with its transcripts.
            target = out_dir / f'results-{arm["name"]}.json'
        elif args.out:
            target = Path(args.out)
        else:
            target = results_path(arm['info'])
        arm['results'] = target
        if target.exists() and not args.force:
            raise EvalError(f'{target} exists. Pass --force to replace it, or --out to write elsewhere.')
    jobs = []
    for n in range(1, args.runs + 1):
        for task in tasks:
            for arm in arms:
                jobs.append({'task': task, 'arm': arm, 'n': n})
    say(f'{len(jobs)} runs ({len(tasks)} tasks x {args.runs} runs x {len(arms)} arm(s)), model '
        f'{args.model}, sign-in: {agent.auth_mode()}, at most ${args.max_usd_total:.2f} in all.')
    for arm in arms:
        if arm['info'].get('dirty'):
            say(f'Note: {arm["name"]} includes uncommitted harness edits.')
    budget = Budget(args.max_usd_total)
    records = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(one_run, job, args, budget, out_dir) for job in jobs]
        for future in as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda r: (r['arm'], r['task'], r['run']))

    items = []
    for record in records:
        if record['valid'] and record['kind'] in ('review', 'security'):
            task = next(t for t in tasks if t['id'] == record['task'])
            key = f'{record["arm"]}/{record["task"]}/{record["run"]}'
            items.append({'key': key, 'task': task, 'message': record.get('final_text', '')})
    say(f'Grading {len(items)} final messages blind with {args.grader_model}...')
    answers, grading_usd = grade.grade_all(items, args.grader_model, stub=False, workdir=root)
    for record in records:
        key = f'{record["arm"]}/{record["task"]}/{record["run"]}'
        if key in answers:
            record['graded'] = answers[key]

    pairwise = {}
    if side_by_side and not args.no_side_by_side:
        pairs = side_by_side_pairs(records, tasks, arms, out_dir)
        say(f'Comparing {len(pairs)} pairs of changes side by side, under random ids...')
        verdicts, pair_usd = grade.compare_pairs(pairs, args.grader_model, workdir=root)
        grading_usd += pair_usd
        for pair in pairs:
            verdict = verdicts.get(pair['key'])
            tally = pairwise.setdefault(pair['arm'], {'better': 0, 'worse': 0, 'same': 0, 'unanswered': 0})
            if verdict == pair['arm']:
                tally['better'] += 1
            elif verdict == 'baseline':
                tally['worse'] += 1
            elif verdict == 'same':
                tally['same'] += 1
            else:
                tally['unanswered'] += 1

    written = []
    for arm in arms:
        mine = [r for r in records if r['arm'] == arm['name']]
        results = build_results(arm, mine, args, grading_usd / max(len(arms), 1))
        if arm['name'] in pairwise:
            results['side_by_side'] = pairwise[arm['name']]
        write_json(arm['results'], results)
        written.append((arm, results))
        say(f'Wrote {arm["results"]}')
    spent = sum(r.get('cost_usd') or 0 for r in records) + grading_usd
    say(f'Spent ${spent:.2f} (agents ${spent - grading_usd:.2f}, grading ${grading_usd:.2f}). '
        f'Transcripts and diffs: {out_dir}')
    texts = []
    if side_by_side:
        for _, results in written[1:]:
            texts.append(report.compare(written[0][1], results))
    else:
        previous = previous_results(written[0][0]['results'])
        if previous:
            texts.append(report.compare(read_json(previous), written[0][1]))
    if texts:
        text = '\n'.join(texts)
        print(text)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'comparison.md').write_text(text)
    shutil.rmtree(root, ignore_errors=True)
    return 0


def eval_changed_since(ref: str) -> str:
    """Whether the evaluation itself (tasks, scoring, app) differs from ref. Both arms are scored by
    this checkout's code, so a change here applies to both, and needs its own review."""
    diff = subprocess.run(['git', 'diff', '--stat', ref, '--', 'eval', ':!eval/harness', ':!eval/results',
                           ':!eval/README.md'], cwd=Path(__file__).resolve().parent.parent,
                          capture_output=True, text=True)
    if diff.returncode == 0 and diff.stdout.strip():
        return (f'the evaluation itself (tasks or scoring) differs from {ref}; both arms are scored '
                'by this checkout. Review that diff before trusting the numbers.')
    return ''


def version_key(path: Path):
    parts = []
    for piece in path.stem.split('.'):
        parts.append(int(piece) if piece.isdigit() else -1)
    return parts


def previous_results(current: Path):
    """The results file for the highest version below this one."""
    if not current.stem[0].isdigit():
        return None
    candidates = []
    for path in RESULTS_DIR.glob('*.json'):
        if path != current and path.stem[0].isdigit() and version_key(path) < version_key(current):
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=version_key)


def compare_cmd(args) -> int:
    if args.new:
        new = Path(args.new)
    else:
        version = (Path(__file__).resolve().parent.parent / 'VERSION').read_text().strip()
        new = RESULTS_DIR / f'{version}.json'
    old = Path(args.old) if args.old else previous_results(new)
    if old is None or not old.exists() or not new.exists():
        raise EvalError(f'need two results files to compare (new: {new}, old: {old}).')
    print(report.compare(read_json(old), read_json(new)))
    return 0


# ---------------------------------------------------------------- command line

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    dry = sub.add_parser('dry-run', help='check the whole pipeline without calling a model')
    dry.add_argument('--tasks', nargs='*', help='task ids or kinds (feature, review, security)')
    dry.add_argument('--model', default=DEFAULT_MODEL)
    dry.add_argument('--keep', action='store_true', help='keep the temporary workspaces')

    go = sub.add_parser('run', help='real runs: costs money')
    go.add_argument('--harness', default='worktree',
                    help='the harness to test: "worktree" (this checkout, default), a git ref, or "none"')
    go.add_argument('--compare-to', help='the baseline: also run this harness (a git ref, or "none"), '
                    'interleaved, and compare against it')
    go.add_argument('--variants', nargs='+', help='more harness versions (git refs) to try against the same '
                    'baseline, as evaluate.md suggests: two or three variations of a rule')
    go.add_argument('--no-side-by-side', action='store_true',
                    help='skip the blind side-by-side comparison of each pair of changes')
    go.add_argument('--runs', type=int, default=2, help='runs per task per arm (default 2, the minimum to judge a change)')
    go.add_argument('--tasks', nargs='*', help='task ids or kinds (feature, review, security)')
    go.add_argument('--model', default=DEFAULT_MODEL)
    go.add_argument('--grader-model', default=DEFAULT_GRADER)
    go.add_argument('--jobs', type=int, default=2, help='runs at once (default 2)')
    go.add_argument('--max-usd-per-run', type=float, default=4.0)
    go.add_argument('--max-usd-total', type=float, default=60.0,
                    help='stop starting new runs once this much is spent (default 60); runs already '
                    'going finish, each within --max-usd-per-run')
    go.add_argument('--timeout-minutes', type=int, default=25)
    go.add_argument('--out', help='results file (default eval/results/<VERSION>.json)')
    go.add_argument('--force', action='store_true', help='replace an existing results file')
    go.add_argument('--keep', action='store_true', help='keep the workspaces after scoring')
    go.add_argument('--use-my-login', action='store_true',
                    help='run with this machine\'s login and your real home folder (see the README)')

    cmp_ = sub.add_parser('compare', help='compare two results files')
    cmp_.add_argument('new', nargs='?')
    cmp_.add_argument('old', nargs='?')

    args = parser.parse_args()
    os.umask(0o022)
    try:
        if args.command == 'dry-run':
            return dry_run.main(args)
        if args.command == 'run':
            return evaluate(args)
        return compare_cmd(args)
    except EvalError as error:
        say(f'Stopped: {error}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
