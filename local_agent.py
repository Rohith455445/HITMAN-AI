"""Opt-in LOCAL Docker test/repair agent. NEVER enable on public services.

Tests are run only in pre-existing container images with no network, read-only
source mounts, non-root user and resource limits. Docker reduces risk but is not
an absolute security boundary. Uploaded content is not trusted instructions.
"""
from __future__ import annotations

import ast
import base64
import difflib
import io
import json
import os
import re
import subprocess
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Callable

from studio_engine import CREDENTIAL_RE, static_inspection, safe_path

MAX_FILES = 20
MAX_PROJECT_BYTES = 180_000
MAX_ROUNDS = 2
MAX_OUTPUT = 12_000
TIMEOUT_SECONDS = 25


class AgentError(ValueError):
    pass


REPORT_NAMES = {'HITMAN_BUILD_MANIFEST.json','HITMAN_BUILD_REVIEW.md',
                'HITMAN_AGENT_MANIFEST.json','HITMAN_AGENT_REPORT.md',
                'HITMAN_REVIEW_PATCH.txt'}


def read_agent_zip(encoded: str) -> dict[str, str]:
    """Local-only ZIP reader: also accepts complete Builder Studio-generated ZIPs."""
    if not isinstance(encoded, str) or len(encoded) > 370_000:
        raise AgentError('Source ZIP must be under 250 KB compressed')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise AgentError('Invalid ZIP base64 encoding')
    if len(raw) > 250_000:
        raise AgentError('Source ZIP exceeds 250 KB')
    result = {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries = z.infolist()
            if len(entries) > 30:
                raise AgentError('ZIP contains too many entries')
            for entry in entries:
                if entry.is_dir():
                    continue
                name = entry.filename
                if (entry.flag_bits & 1 or
                    ((entry.external_attr >> 16) & 0o170000) == 0o120000):
                    raise AgentError('Encrypted files and symlinks are not allowed')
                if name in REPORT_NAMES:
                    continue
                if not safe_path(name):
                    raise AgentError('Unsupported or unsafe source path: ' + name[:80])
                if name in result or len(result) >= MAX_FILES:
                    raise AgentError('Duplicate source path or too many files')
                if entry.file_size > 40_000 or (entry.compress_size and
                   entry.file_size > 100 * entry.compress_size):
                    raise AgentError('ZIP contains an oversized or highly compressed file')
                total += entry.file_size
                if total > MAX_PROJECT_BYTES:
                    raise AgentError('Source archive exceeds expanded size limit')
                with z.open(entry) as fp:
                    content = fp.read(40_001)
                if len(content) != entry.file_size or b'\x00' in content:
                    raise AgentError('Source file has invalid size or binary contents')
                try:
                    result[name] = content.decode('utf-8', errors='strict')
                except UnicodeDecodeError:
                    raise AgentError('Only UTF-8 source files are supported')
    except (zipfile.BadZipFile, EOFError):
        raise AgentError('Invalid ZIP archive')
    validate_files(result)
    return result


def validate_files(files: dict[str, str], *, allow_invalid_syntax: bool = True) -> None:
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise AgentError('Expected 1–20 text source files')
    total = 0
    for path, content in files.items():
        if not safe_path(path) or not isinstance(content, str):
            raise AgentError('Project contains an unsafe source path or non-text data')
        size = len(content.encode('utf-8'))
        total += size
        if size > 40_000 or total > MAX_PROJECT_BYTES:
            raise AgentError('Project exceeds the 180 KB / 40 KB-per-file limits')
        if CREDENTIAL_RE.search(content):
            raise AgentError('Possible credential in source: remove secrets before using the agent')
        if not allow_invalid_syntax and path.endswith('.py'):
            ast.parse(content, filename=path)


def get_test_plan(files: dict[str, str]) -> dict:
    """Select only fixed recipes; never run commands supplied by a ZIP or model."""
    python_files = [name for name in files if name.endswith('.py')]
    js_files = [name for name in files if name.endswith(('.js', '.mjs', '.cjs'))]
    if python_files:
        tests = {name: content for name, content in files.items()
                 if name.endswith('.py') and (Path(name).name.startswith('test_') or Path(name).name.endswith('_test.py'))}
        if not tests:
            recipe = 'python_syntax'
        elif any(re.search(r'\b(?:import pytest|from pytest|@pytest\.)', c) or
                 re.search(r'^def test_\w+', c, re.M) for c in tests.values()):
            recipe = 'pytest'
        else:
            recipe = 'unittest'
        return {'language': 'python', 'recipe': recipe,
                'tests_discovered': bool(tests), 'test_file_names': sorted(tests),
                'source_names':sorted(python_files)}
    if js_files:
        has_tests = any(Path(x).name.startswith('test_') or '.test.js' in x or x.startswith('tests/')
                        for x in js_files)
        return {'language': 'javascript', 'recipe': 'node_test' if has_tests else 'node_syntax',
                'tests_discovered': has_tests, 'test_file_names': [x for x in js_files if 'test' in x],
                'source_names':sorted(js_files)}
    return {'language': 'none', 'recipe': 'static_only', 'tests_discovered': False, 'test_file_names': [],
            'source_names':[]}


# Kept as constants, not generated from user source. The test containers have
# no network and no dependency installation. Users preload dependencies in a
# separate image they explicitly trust (see docs).
PY_SYNTAX_SCRIPT = (
    "import ast,pathlib,sys\n"
    "paths=sorted(pathlib.Path('/work').rglob('*.py'))\n"
    "for path in paths:\n"
    " try: ast.parse(path.read_text(encoding='utf-8'),filename=str(path))\n"
    " except (SyntaxError,UnicodeError) as e: print(str(e));sys.exit(1)\n"
    "print('Python syntax OK:',len(paths),'files')\n"
)



def docker_commands(plan: dict) -> list[list[str]]:
    recipe = plan['recipe']
    if recipe == 'static_only':
        return []
    if plan['language'] == 'python':
        commands = [['python', '-B', '-c', PY_SYNTAX_SCRIPT]]
        if recipe == 'pytest':
            commands.append(['python', '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '/work'])
        elif recipe == 'unittest':
            commands.append(['python', '-B', '-m', 'unittest', 'discover', '-s', '/work', '-p', 'test*.py', '-v'])
        return commands
    # Node --check handles ESM import syntax more faithfully than vm.Script.
    commands = [['node', '--check', '/work/' + name] for name in plan['source_names']]
    if recipe == 'node_test':
        commands.append(['node', '--test'])
    return commands


def _docker_image(plan: dict) -> str:
    key = 'HITMAN_AGENT_PYTHON_IMAGE' if plan['language'] == 'python' else 'HITMAN_AGENT_NODE_IMAGE'
    default = 'python:3.12-slim' if plan['language'] == 'python' else 'node:22-alpine'
    image = os.getenv(key, default)
    if not re.fullmatch(r'[a-zA-Z0-9_./:@-]{1,150}', image) or image.startswith('-'):
        raise AgentError('Unsafe Docker image reference')
    return image


def docker_run(source_folder: Path, plan: dict, args: list[str], *, timeout: int = TIMEOUT_SECONDS) -> dict:
    """Run a hard-coded validation recipe, never a model/user shell command."""
    image = _docker_image(plan)
    with tempfile.TemporaryDirectory(prefix='hitman-cid-') as td:
        cid_path = Path(td) / 'cid'
        command = [
            'docker', 'run', '--rm', '--pull=never', '--cidfile', str(cid_path),
            '--network=none', '--read-only', '--cap-drop=ALL',
            '--security-opt=no-new-privileges:true', '--pids-limit=64',
            '--memory=512m', '--cpus=1', '--user=65534:65534',
            '--tmpfs=/tmp:rw,nosuid,noexec,size=32m',
            '--mount', f'type=bind,src={source_folder.resolve()},dst=/work,readonly',
            '--workdir=/work', '--env=HOME=/tmp', '--env=PYTHONPATH=/work',
            '--env=PYTHONDONTWRITEBYTECODE=1', '--env=PYTEST_ADDOPTS=-p no:cacheprovider',
            image, *args,
        ]
        try:
            # Drain output into a bounded tail buffer. A malicious test can spam
            # stdout; never buffer the entire stream in the server process.
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            tail = bytearray()
            def drain_output():
                try:
                    while True:
                        chunk = process.stdout.read(8192)
                        if not chunk:
                            break
                        if len(chunk) >= MAX_OUTPUT:
                            tail[:] = chunk[-MAX_OUTPUT:]
                        else:
                            tail.extend(chunk)
                            if len(tail) > MAX_OUTPUT:
                                del tail[:-MAX_OUTPUT]
                finally:
                    process.stdout.close()
            reader = threading.Thread(target=drain_output, daemon=True)
            reader.start()
            timed_out = False
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                # Docker CLI termination may leave a running container.
                if cid_path.exists():
                    cid = cid_path.read_text(encoding='utf-8').strip()
                    if re.fullmatch(r'[a-f0-9]{12,64}', cid):
                        try:
                            subprocess.run(['docker','rm','--force',cid], stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, timeout=5, check=False)
                        except (OSError, subprocess.TimeoutExpired):
                            pass
                return_code = None
            reader.join(timeout=3)
            output = bytes(tail).decode('utf-8', errors='replace')
            if timed_out:
                return {'status':'FAIL','exit_code':None,
                        'output':(output+'\nTest timed out after '+str(timeout)+'s')[-MAX_OUTPUT:],
                        'recipe':' '.join(args[:4]),'timeout':True}
            unavailable = (return_code in {125, 126, 127} or
                           'Cannot connect to the Docker daemon' in output or
                           'No such image' in output)
            return {'status': 'UNAVAILABLE' if unavailable else 'PASS' if return_code == 0 else 'FAIL',
                    'exit_code':return_code,'output':output,
                    'recipe':' '.join(args[:4]), 'timeout':False}
        except FileNotFoundError:
            return {'status':'UNAVAILABLE','exit_code':None,
                    'output':'Docker CLI is missing. Install and start Docker Desktop first.',
                    'recipe':' '.join(args[:4]),'timeout':False}
        except OSError as exc:
            return {'status':'UNAVAILABLE','exit_code':None,'output':f'Docker failed: {type(exc).__name__}',
                    'recipe':' '.join(args[:4]),'timeout':False}


def test_files(files: dict[str, str], *, execute: Callable = docker_run) -> dict:
    validate_files(files)
    scan = static_inspection(files)
    plan = get_test_plan(files)
    if plan['recipe'] == 'static_only':
        return {'status':'FAIL' if scan['syntax_failures'] else 'NOT_RUN',
                'static_report':scan,'plan':plan, 'steps':[],
                'tests_executed':False,'tests_passed':False,
                'reason':'Static Python/JSON validation only; no supported executable tests'}
    with tempfile.TemporaryDirectory(prefix='hitman-agent-source-') as td:
        source = Path(td)
        for name, content in files.items():
            dst = source.joinpath(*name.split('/'))
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, encoding='utf-8')
        steps = []
        for command in docker_commands(plan):
            step = execute(source, plan, command)
            steps.append(step)
            if step['status'] != 'PASS':
                break
    test_step = steps[-1] if steps and (
        (plan['recipe'] in {'pytest','unittest'} and len(steps) >= 2) or
        (plan['recipe'] == 'node_test' and len(steps) > len(plan['source_names']))
    ) else None
    tests_seen = False
    if test_step and test_step['status'] != 'UNAVAILABLE':
        out = test_step['output']
        if plan['recipe'] == 'unittest':
            count = re.search(r'Ran\s+(\d+)\s+tests?', out)
            tests_seen = bool(count and int(count.group(1)) > 0)
        elif plan['recipe'] == 'pytest':
            tests_seen = bool(re.search(r'\b[1-9]\d*\s+(?:passed|failed|error|errors)\b',out))
        else:
            tests_seen = bool(re.search(r'\b(?:pass|fail|tests)\b',out,re.I))
    ran_tests = plan['tests_discovered'] and bool(tests_seen)
    overall = steps[-1]['status'] if steps else 'NOT_RUN'
    # An invalid JSON/notebook is a real static failure even when Python tests pass.
    if overall == 'PASS' and scan['syntax_failures']:
        overall = 'FAIL'
    if overall == 'PASS' and plan['tests_discovered'] and not ran_tests:
        overall = 'NOT_VERIFIED'
    return {'status': overall, 'static_report':scan,'plan':plan,'steps':steps,
            'tests_executed':bool(ran_tests),
            'tests_passed':bool(ran_tests and overall == 'PASS'),
            'reason': ('Docker container commands executed' if overall in {'PASS','FAIL','NOT_VERIFIED'}
                       else 'Docker runtime or image not available; no code was executed')}


def apply_changes(original: dict[str, str], payload: dict) -> tuple[dict[str, str], list[str]]:
    """Reviewable existing-file edits only; no shell commands/new files/secrets."""
    edits = payload.get('changes') if isinstance(payload, dict) else None
    if not isinstance(edits, list) or not 1 <= len(edits) <= 5:
        raise AgentError('Gemini must propose 1–5 existing-file replacements')
    updated = dict(original)
    changed = []
    for edit in edits:
        if not isinstance(edit, dict):
            raise AgentError('Invalid AI edit')
        name, content = edit.get('path'), edit.get('content')
        if not isinstance(name, str) or name not in updated or name in changed:
            raise AgentError('AI attempted to edit a missing or duplicate file')
        if not isinstance(content, str) or len(content.encode('utf-8')) > 25_000:
            raise AgentError('AI replacement exceeds file limit')
        if CREDENTIAL_RE.search(content):
            raise AgentError('AI-generated replacement contains possible credentials')
        if content != updated[name]:
            updated[name] = content
            changed.append(name)
    validate_files(updated)
    if not changed:
        raise AgentError('Gemini proposed no changes')
    return updated, changed


def package_result(before: dict[str, str], after: dict[str, str], run_history: list[dict],
                   edits: list[dict], messages: list[str]) -> tuple[bytes, dict]:
    final = run_history[-1]
    changed = sorted(p for p in after if after[p] != before[p])
    manifest = {
        'workflow': 'HITMAN AI local Docker agent', 'status':final['status'],
        'tests_executed':final['tests_executed'], 'tests_passed':final['tests_passed'],
        'tests_discovered':final['plan']['tests_discovered'],
        'changed_files':changed, 'test_plan':final['plan'], 'rounds':len(run_history)-1,
        'history':[{k:v for k,v in run.items() if k != 'static_report'} for run in run_history],
        'notes':messages,
        'limits': 'Local-only; Docker is not a guarantee of perfect isolation; no network/dependency install'
    }
    diff = []
    for name in changed:
        diff.extend(difflib.unified_diff(before[name].splitlines(keepends=True),
                                        after[name].splitlines(keepends=True),
                                        fromfile='before/'+name,tofile='after/'+name))
    report = [
        '# HITMAN AI — Local Code Agent Report', '',
        f"**Final Docker check:** {final['status']}",
        f"**Unit tests actually executed:** {final['tests_executed']}",
        f"**Unit tests passed:** {final['tests_passed']}",
        f"**Test recipe:** {final['plan']['recipe']}",
        f"**AI repair rounds:** {len(run_history)-1}",
        '', 'This does not prove production security, correctness or ML model accuracy.',
        'No dependencies were installed and no network access was granted to containers.',
        'Check model-generated changes yourself before deploying.', '',
    ]
    for i, run in enumerate(run_history):
        report.extend([f"## Test round {i}: {run['status']}", ''])
        for step in run['steps']:
            report.extend([f"### {step['recipe']} — {step['status']}", '```text', step['output'][:MAX_OUTPUT], '```', ''])
    if messages:
        report.extend(['## Notes', *['- '+x for x in messages], ''])
    if edits:
        report.extend(['## Changes', *['- '+e['summary'] for e in edits], ''])
    if diff:
        report.extend(['## Unified diff', '```diff', ''.join(diff)[:50000], '```'])
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in after.items():
            archive.writestr(name,content)
        archive.writestr('HITMAN_AGENT_REPORT.md','\n'.join(report))
        archive.writestr('HITMAN_AGENT_MANIFEST.json',json.dumps(manifest, indent=2))
    return stream.getvalue(), manifest


def run_agent(files: dict[str, str], *, rounds: int = 0,
              fixer: Callable[[dict[str,str], dict, str], dict] | None = None,
              goal: str = '', executor: Callable = docker_run) -> tuple[bytes, dict]:
    """Execute fixed Docker recipes, optionally repair with Gemini, retest, report."""
    validate_files(files)
    if rounds < 0 or rounds > MAX_ROUNDS:
        raise AgentError(f'Maximum {MAX_ROUNDS} AI repair rounds')
    if rounds and fixer is None:
        raise AgentError('AI repair requested without a configured model')
    original = dict(files)
    current = dict(files)
    history = [test_files(current, execute=executor)]
    edits = []
    messages = []
    for _ in range(rounds):
        previous = history[-1]
        if previous['status'] != 'FAIL':
            break
        # A failed sandbox command might reflect an uninstalled dependency;
        # the model should explain rather than falsely claiming a fix.
        try:
            proposal = fixer(current, previous, goal)
            current, changed = apply_changes(current, proposal)
            edits.append({'summary':str(proposal.get('summary','Proposed edits'))[:350],
                          'files':changed})
        except Exception as exc:
            messages.append(f'Repair stopped: {type(exc).__name__}: {str(exc)[:180]}')
            break
        history.append(test_files(current, execute=executor))
    if history[-1]['status'] == 'UNAVAILABLE':
        messages.append('No Docker execution was performed. Install Docker Desktop and preload your chosen image.')
    if history[-1]['status'] in {'PASS','NOT_VERIFIED'} and not history[-1]['tests_executed']:
        messages.append('No verified test count was found. This is not evidence of passing unit tests.')
    return package_result(original, current, history, edits, messages)
