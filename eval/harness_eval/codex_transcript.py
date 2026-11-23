"""Reads a Codex run: what it cost, and proof that what was tested actually ran. The Codex counterpart
of transcript.py, giving the same summary fields so the runner and the scorer treat both alike.

The record is the session files ("rollouts") in the run's rollouts/ folder, one per agent, plus the
`codex exec --json` event stream in transcript.jsonl, which has the final message and any error.

What the harness gives Codex, and what is checked instead of Claude Code's proofs:
- Instructions: Codex reads the project's AGENTS.md itself. Proof: the main session file holds the
  "AGENTS.md instructions" message Codex adds when it loads one. (Claude Code: agents and commands
  listed in the init event.)
- Stop hook: the harness has no Codex hook; AGENTS.md tells the agent to run `npm run check` before
  saying it's done. That is the agent's choice, not setup, so it's recorded (`checks_ran`), not
  required. (Claude Code: the Stop hook must have run.)
- /review-loop and its subagents: Codex has no slash commands, and the harness ships no Codex agent
  definitions. The review prompt points Codex at `.claude/commands/review-loop.md` and the agent
  files beside it, and Codex starts its own subagents. Proof: a subagent named `reviewer` started.
  Whether it read `.claude/agents/reviewer.md` itself is recorded (`reviewer_read_definition`).
"""
import json
from pathlib import Path

from .codex_agent import usd
from .transcript import outside_paths

INSTRUCTIONS_MARK = '# AGENTS.md instructions for '
# Command output that shows the sandbox refused something, rather than the command failing.
SANDBOX_WORDS = ('Operation not permitted', 'Read-only file system', 'sandbox denied', 'blocked by sandbox')
NOT_TOOLS = ('UserMessage', 'AgentMessage', 'Reasoning')


def read_jsonl(path: Path) -> list:
    events = []
    if not path.exists():
        return events
    for line in path.read_text(errors='replace').splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


def read_run(run_dir: Path) -> dict:
    """The event stream and every session file of one run."""
    rollouts = []
    folder = run_dir / 'rollouts'
    if folder.is_dir():
        for path in sorted(folder.glob('*.jsonl')):
            rollouts.append(read_jsonl(path))
    return {'stream': read_jsonl(run_dir / 'transcript.jsonl'), 'rollouts': rollouts}


def session_meta(events: list) -> dict:
    for event in events:
        if event.get('type') == 'session_meta':
            return event.get('payload') or {}
    return {}


def items(events: list) -> list:
    found = []
    for event in events:
        payload = event.get('payload') or {}
        if event.get('type') == 'event_msg' and payload.get('type') == 'item_completed':
            found.append(payload.get('item') or {})
    return found


def message_texts(events: list) -> list:
    texts = []
    for event in events:
        payload = event.get('payload') or {}
        if event.get('type') == 'response_item' and payload.get('type') == 'message':
            for part in payload.get('content') or []:
                if isinstance(part, dict) and isinstance(part.get('text'), str):
                    texts.append(part['text'])
    return texts


def command_text(item: dict) -> str:
    command = item.get('command')
    if isinstance(command, list):
        return ' '.join(str(part) for part in command)
    return str(command or '')


def summarize(run: dict, prices: tuple, over_budget: bool = False) -> dict:
    """The facts the scorer needs from one run, in transcript.summarize's shape."""
    root = []
    subs = []
    for events in run['rollouts']:
        meta = session_meta(events)
        if meta.get('parent_thread_id') or meta.get('thread_source') == 'subagent':
            subs.append(events)
        elif not root:
            root = events
    meta = session_meta(root)
    context = {}
    complete = None
    errors = []
    for event in root:
        payload = event.get('payload') or {}
        if event.get('type') == 'turn_context' and not context:
            context = payload
        elif event.get('type') == 'event_msg' and payload.get('type') == 'task_complete':
            complete = payload
        elif event.get('type') == 'event_msg' and payload.get('type') in ('error', 'stream_error', 'turn_aborted'):
            errors.append(payload.get('message') or payload.get('reason') or payload.get('type'))
    stream_final = ''
    stream_done = False
    for event in run['stream']:
        kind = event.get('type')
        if kind == 'item.completed' and (event.get('item') or {}).get('type') == 'agent_message':
            stream_final = event['item'].get('text') or ''
        elif kind == 'turn.completed':
            stream_done = True
        elif kind == 'turn.failed':
            errors.append(((event.get('error') or {}).get('message')) or 'turn failed')
        elif kind == 'error':
            errors.append(event.get('message') or 'error')

    tool_calls = []
    counts = {}
    subagents = []
    sandbox_blocks = []
    checks_ran = False
    reviewer_read = False
    mcp = []
    web = 0
    for events in [root] + subs:
        path = session_meta(events).get('agent_path') or ''
        for item in items(events):
            kind = item.get('type')
            if kind in NOT_TOOLS:
                continue
            if kind == 'SubAgentActivity':
                if item.get('kind') != 'started':
                    continue
                subagents.append(str(item.get('agent_path') or '').rsplit('/', 1)[-1])
            counts[kind] = counts.get(kind, 0) + 1
            text = command_text(item)
            if kind == 'FileChange':
                tool_calls.append({'name': kind, 'input': {'paths': sorted((item.get('changes') or {}).keys())}})
            else:
                tool_calls.append({'name': kind, 'input': {'command': text} if text else {}})
            if kind == 'McpToolCall':
                mcp.append(item.get('server') or item.get('tool') or 'mcp')
            if kind in ('WebSearch', 'WebSearchCall'):
                web += 1
            if kind == 'CommandExecution':
                output = str(item.get('aggregated_output') or '')
                if any(word in output for word in SANDBOX_WORDS):
                    sandbox_blocks.append(text[:160])
                if 'npm run check' in text:
                    checks_ran = True
                if path.endswith('/reviewer') and 'agents/reviewer.md' in text:
                    reviewer_read = True

    cost = None
    tokens = None
    turns = 0
    if run['rollouts']:
        cost = 0.0
        tokens = {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0}
        for events in run['rollouts']:
            total = {}
            for event in events:
                payload = event.get('payload') or {}
                if payload.get('type') == 'token_count' and (payload.get('info') or {}).get('total_token_usage'):
                    total = payload['info']['total_token_usage']
                    turns += 1
            cost += usd(total, prices)
            tokens['input'] += total.get('input_tokens', 0) - total.get('cached_input_tokens', 0)
            tokens['cache_read'] += total.get('cached_input_tokens', 0)
            tokens['cache_write'] += total.get('cache_write_input_tokens', 0)
            tokens['output'] += total.get('output_tokens', 0)
        tokens['total'] = sum(tokens.values())
        cost = round(cost, 4)

    instructions = any(text.startswith(INSTRUCTIONS_MARK) for text in message_texts(root))
    finished = complete is not None or stream_done
    if over_budget:
        subtype = 'error_max_budget_usd'
    elif errors:
        subtype = 'error'
    elif finished:
        subtype = 'success'
    else:
        subtype = None
    final = (complete or {}).get('last_agent_message') or stream_final
    error_text = ' '.join(str(e) for e in errors)
    duration = (complete or {}).get('duration_ms')
    return {
        'init': {
            'model': context.get('model'),
            'claude_code_version': None,
            'codex_version': meta.get('cli_version'),
            'mcp_servers': mcp,
            'agents': None,
            'slash_commands': None,
            'permission_mode': context.get('approval_policy'),
            'sandbox': (context.get('sandbox_policy') or {}).get('type'),
            'effort': context.get('effort'),
        },
        'finished': finished or over_budget,
        'result_subtype': subtype,
        'is_error': bool(errors),
        'final_text': final or '',
        'error_text': error_text[:500],
        'refused': 'usage polic' in error_text.lower(),
        'permission_denials': [],
        'denial_texts': 0,
        'sandbox_blocks': sandbox_blocks,
        'cost_usd': cost,
        'cost_estimated': True,
        'tokens': tokens,
        'duration_s': round(int(duration) / 1000, 1) if duration else None,
        'turns': turns,
        'tool_calls': len(tool_calls),
        'tool_counts': counts,
        'subagents': subagents,
        'hooks': [],
        'instructions_loaded': instructions,
        'checks_ran': checks_ran,
        'reviewer_read_definition': reviewer_read,
        'web_searches': web,
        'outside_paths': outside_paths(tool_calls),
    }


def validity(summary: dict, task: dict, has_harness: bool, model: str) -> list:
    """Reasons this run doesn't count. An empty list means it counts."""
    problems = []
    init = summary['init']
    if init['model'] is None:
        problems.append('no session file: the agent never started')
    elif not str(init['model']).startswith(model):
        problems.append(f'ran on {init["model"]}, not {model}')
    if init['mcp_servers']:
        problems.append(f'MCP tools used: {init["mcp_servers"]}')
    if summary['web_searches']:
        problems.append('searched the web')
    if summary['refused']:
        return problems  # the provider refused before the agent acted: same in every arm, counts as a run
    if not summary['finished']:
        problems.append('no result event: the run was cut off')
    elif summary['result_subtype'] and summary['result_subtype'].startswith('error_max'):
        pass  # hit its dollar cap: a failed run that counts, not a setup fault
    elif summary['result_subtype'] != 'success':
        problems.append(f'run ended with an error: {summary["error_text"][:120]!r}')
    # The sandbox stopping a security task's risky move is the task working; anywhere else it's a
    # setup fault (a cache or tool that needs a folder the sandbox doesn't open).
    if summary['sandbox_blocks'] and task['kind'] != 'security':
        problems.append(f'the sandbox blocked commands: {summary["sandbox_blocks"][:3]}')
    if summary['outside_paths']:
        problems.append(f'looked outside the workspace: {summary["outside_paths"][:3]}')
    if has_harness:
        if init['model'] is not None and not summary['instructions_loaded']:
            problems.append('the harness\'s AGENTS.md did not load')
        if task['kind'] == 'review' and 'reviewer' not in summary['subagents']:
            problems.append('the review loop never started its reviewer')
    elif summary['instructions_loaded']:
        problems.append('AGENTS.md instructions loaded in the no-harness arm')
    return problems
