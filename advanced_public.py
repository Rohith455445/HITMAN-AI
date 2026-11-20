"""Small opt-in tools for HITMAN AI's anonymous public demo.

Never executes uploaded source code. All paid/quota-consuming tools are disabled
by default. Responses are temporary: no uploaded files or images are persisted.
"""
from __future__ import annotations

import ast
import base64
import difflib
import io
import json
import re
import zipfile
from pathlib import Path

from fastapi import HTTPException


EDIT_EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.json', '.md', '.txt', '.yaml', '.yml', '.toml', '.sql', '.ipynb', '.csv', '.java', '.go', '.rs'}
DENIED_NAMES = {'.env', '.npmrc', '.pypirc', 'id_rsa', 'credentials.json', 'secrets.json'}


def read_guest_zip(encoded: str) -> dict[str, str]:
    if not isinstance(encoded, str) or len(encoded) > 370_000:
        raise HTTPException(413, 'Project ZIP exceeds public demo limit (250 KB)')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise HTTPException(400, 'Invalid ZIP encoding')
    if len(raw) > 250_000:
        raise HTTPException(413, 'Project ZIP exceeds public demo limit (250 KB)')
    files: dict[str, str] = {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if len(archive.infolist()) > 35:
                raise HTTPException(413, 'Too many archive entries')
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                name = entry.filename
                path = Path(name)
                if (not name or '\\' in name or name.startswith('/') or
                    bool(re.match(r'^[A-Za-z]:', name)) or any(ord(c)<32 for c in name) or
                    '..' in path.parts or len(path.parts) > 7 or len(name) > 140 or
                    path.name.lower() in DENIED_NAMES or path.suffix.lower() not in EDIT_EXTENSIONS or
                    path.parts[0] in ('.git', '.venv', 'node_modules') or
                    entry.flag_bits & 1 or ((entry.external_attr >> 16) & 0o170000) == 0o120000):
                    raise HTTPException(400, 'Unsupported or unsafe project file in ZIP')
                if entry.file_size > 25_000 or (entry.compress_size and entry.file_size > entry.compress_size * 100):
                    raise HTTPException(413, 'Individual source file exceeds limit')
                total += entry.file_size
                if total > 95_000 or len(files) >= 12:
                    raise HTTPException(413, 'Source context exceeds public demo limit')
                data = archive.read(entry)
                if b'\x00' in data:
                    raise HTTPException(400, 'Binary project files are not supported')
                if name in files:
                    raise HTTPException(400, 'Duplicate ZIP entry')
                files[name] = data.decode('utf-8', 'replace')
    except zipfile.BadZipFile:
        raise HTTPException(400, 'Invalid ZIP file')
    if not files:
        raise HTTPException(400, 'ZIP has no supported source files')
    return files


def build_reviewed_patch(original: dict[str, str], result: dict) -> tuple[bytes, dict]:
    """Bundle proposed edits with human-readable diffs; reject unexpected writes.

    Existing files only; no secrets, generated binaries, shell scripts or new files.
    This is a reviewable proposal, not an executed or validated application.
    """
    if not isinstance(result, dict) or not isinstance(result.get('changes'), list):
        raise ValueError('AI response missing changes list')
    edits = result['changes']
    if len(edits) > 5:
        raise ValueError('Too many proposed edits')
    updated = dict(original)
    names = set()
    changes = []
    for item in edits:
        if not isinstance(item, dict):
            raise ValueError('Malformed edit')
        name = item.get('path')
        content = item.get('content')
        if not isinstance(name, str) or name not in original or name in names:
            raise ValueError('Edit targets must be unique existing files')
        if not isinstance(content, str) or len(content.encode('utf8')) > 25_000:
            raise ValueError('Replacement file is too large')
        names.add(name)
        updated[name] = content
        if original[name] != content:
            changes.append(name)
    validation = []
    for name, content in updated.items():
        if name.endswith('.py'):
            try:
                ast.parse(content, filename=name)
                validation.append('PASS Python syntax: ' + name)
            except SyntaxError as error:
                validation.append(f'FAIL Python syntax: {name}:{error.lineno} {error.msg}')
        if name.endswith('.json'):
            try:
                json.loads(content)
                validation.append('PASS JSON parse: ' + name)
            except json.JSONDecodeError as error:
                validation.append(f'FAIL JSON parse: {name}:{error.lineno} {error.msg}')
    diff = []
    for name in changes:
        diff.extend(difflib.unified_diff(original[name].splitlines(keepends=True),
            updated[name].splitlines(keepends=True), fromfile='before/' + name,
            tofile='after/' + name))
    report = (
        'HITMAN AI — REVIEWABLE PATCH (UNEXECUTED)\n'
        'No shell commands or application tests were run.\n'
        'Only static Python/JSON parsing was performed.\n\n'
        'AI summary: ' + str(result.get('summary', ''))[:1500] + '\n'
        'Changed files: ' + (', '.join(changes) or 'None') + '\n\n'
        'Checks:\n' + '\n'.join(validation) + '\n\n'
        'Diff:\n' + ''.join(diff)[:70000]
    )
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for name, content in updated.items():
            output.writestr(name, content)
        output.writestr('HITMAN_REVIEW_PATCH.txt', report)
    return memory.getvalue(), {'changed': changes, 'validation': validation}


def detect_image(encoded: str | None, name: str | None) -> tuple[bytes, str] | None:
    if not encoded:
        return None
    if not name or Path(name).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
        raise HTTPException(400, 'Image edit accepts PNG, JPG or WEBP')
    if len(encoded) > 1_650_000:
        raise HTTPException(413, 'Image exceeds the 1.2 MB limit')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise HTTPException(400, 'Invalid base64 image')
    if len(data) > 1_200_000:
        raise HTTPException(413, 'Image exceeds the 1.2 MB limit')
    extension = Path(name).suffix.lower()
    mime = 'image/png' if extension == '.png' else 'image/webp' if extension == '.webp' else 'image/jpeg'
    valid = (data.startswith(b'\x89PNG\r\n\x1a\n') if mime == 'image/png' else
             data.startswith(b'RIFF') and data[8:12] == b'WEBP' if mime == 'image/webp' else
             data.startswith(b'\xff\xd8\xff'))
    if not valid:
        raise HTTPException(400, 'File bytes do not match the image format')
    return data, mime
