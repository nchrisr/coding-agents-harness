"""Reads a run's stream-json transcript: what it cost, and proof that what was tested actually ran."""
import json
from pathlib import Path

from .common import REPO_ROOT

# Words that show a tool call was refused rather than run (evaluate.md's transcript check).
DENIAL_WORDS = ("haven't granted", 'requires approval', 'permission to use', 'was blocked')
REVIEW_AGENTS = ('reviewer', 'system-reviewer', 'fixer')


def read_events(path: Path) -> list:
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


def summarize(events: list) -> dict:
    """The facts the scorer needs from one transcript, without any of the agent's text but the last."""
    init = None
    result = None
    tool_calls = []
    hooks = []
    denial_texts = 0
    for event in events:
        kind = event.get('type')
        subtype = event.get('subtype')
        if kind == 'system' and subtype == 'init' and init is None:
            init = event
        elif kind == 'system' and subtype == 'hook_response':
            hooks.append({'event': event.get('hook_event'), 'exit_code': event.get('exit_code'),
                          'outcome': event.get('outcome')})
        elif kind == 'assistant':
            for block in event.get('message', {}).get('content', []) or []:
                if block.get('type') == 'tool_use':
                    tool_calls.append({'name': block.get('name'), 'input': block.get('input', {}),
                                       'subagent': event.get('parent_tool_use_id') is not None})
        elif kind == 'user':
            for block in event.get('message', {}).get('content', []) or []:
                if isinstance(block, dict) and block.get('type') == 'tool_result' and block.get('is_error'):
                    text = json.dumps(block.get('content', ''))
                    if any(word in text for word in DENIAL_WORDS):
                        denial_texts += 1
        elif kind == 'result':
            result = event

    cost = None
    tokens = None
    duration_ms = None
    turns = None
    if result is not None:
        cost = result.get('total_cost_usd')
        duration_ms = result.get('duration_ms')
        turns = result.get('num_turns')
        tokens = {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0}
        usage_by_model = result.get('modelUsage') or {}
        for usage in usage_by_model.values():
            tokens['input'] += usage.get('inputTokens', 0)
            tokens['output'] += usage.get('outputTokens', 0)
            tokens['cache_read'] += usage.get('cacheReadInputTokens', 0)
            tokens['cache_write'] += usage.get('cacheCreationInputTokens', 0)
        tokens['total'] = sum(tokens.values())

    subagents = []
    for call in tool_calls:
        if call['name'] in ('Agent', 'Task'):
            subagents.append(call['input'].get('subagent_type', 'general-purpose'))

    return {
        'init': {
            'model': init.get('model') if init else None,
            'claude_code_version': init.get('claude_code_version') if init else None,
            'mcp_servers': init.get('mcp_servers') if init else None,
            'agents': init.get('agents') if init else None,
            'slash_commands': init.get('slash_commands') if init else None,
            'permission_mode': init.get('permissionMode') if init else None,
        },
        'finished': result is not None,
        'result_subtype': result.get('subtype') if result else None,
        'is_error': result.get('is_error') if result else None,
        'final_text': (result.get('result') or '') if result else '',
        'refused': bool(result) and 'Usage Policy' in (result.get('result') or '')
        and (result.get('result') or '').startswith('API Error'),
        'permission_denials': [d.get('tool_name') for d in (result.get('permission_denials') or [])] if result else [],
        'denial_texts': denial_texts,
        'cost_usd': cost,
        'tokens': tokens,
        'duration_s': round(duration_ms / 1000, 1) if duration_ms else None,
        'turns': turns,
        'tool_calls': len(tool_calls),
        'tool_counts': count_names(tool_calls),
        'subagents': subagents,
        'hooks': hooks,
        'outside_paths': outside_paths(tool_calls),
    }


def count_names(calls: list) -> dict:
    counts = {}
    for call in calls:
        counts[call['name']] = counts.get(call['name'], 0) + 1
    return counts


def outside_paths(calls: list) -> list:
    """Tool calls that name this repository or the evaluation's own folders: a run that went looking
    for the hidden tests or the answers."""
    needles = [str(REPO_ROOT), 'eval/tasks', 'eval/regression', '__eval__', 'hidden/']
    hits = []
    for call in calls:
        text = json.dumps(call['input'])
        for needle in needles:
            if needle in text:
                hits.append(f'{call["name"]}: {needle}')
                break
    return hits


def validity(summary: dict, task: dict, has_harness: bool, model: str) -> list:
    """Reasons this run doesn't count. An empty list means it counts."""
    problems = []
    init = summary['init']
    if init['model'] is None:
        problems.append('no init event: the agent never started')
    else:
        if not str(init['model']).startswith(model):
            problems.append(f'ran on {init["model"]}, not {model}')
        if init['mcp_servers']:
            problems.append(f'MCP servers loaded: {init["mcp_servers"]}')
    if summary['refused']:
        return problems  # the provider refused before the agent acted: same in every arm, counts as a run
    if not summary['finished']:
        problems.append('no result event: the run was cut off')
    elif summary['result_subtype'].startswith('error_max'):
        pass  # hit its dollar or turn cap: a failed run that counts, not a setup fault
    elif summary['result_subtype'] != 'success' or summary['is_error']:
        problems.append(f'run ended with {summary["result_subtype"]}: {summary["final_text"][:120]!r}')
    if summary['permission_denials'] or summary['denial_texts']:
        problems.append(f'permission denials: {summary["permission_denials"] or summary["denial_texts"]}')
    if summary['outside_paths']:
        problems.append(f'looked outside the workspace: {summary["outside_paths"][:3]}')
    agents = init['agents'] or []
    commands = init['slash_commands'] or []
    if has_harness:
        if 'reviewer' not in agents or 'review-loop' not in commands:
            problems.append('the harness\'s agents and commands did not load')
        stop_hooks = [h for h in summary['hooks'] if h['event'] == 'Stop']
        if not stop_hooks:
            problems.append('the Stop hook never ran')
        if task['kind'] == 'review' and 'reviewer' not in summary['subagents']:
            problems.append('the review loop never started its reviewer')
    elif init['model'] is not None and ('reviewer' in agents or 'review-loop' in commands):
        problems.append('harness agents loaded in the no-harness arm')
    return problems
