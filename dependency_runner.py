"""Bounded dependency-aware test runner using an opt-in Docker sandbox.

IMPORTANT: Docker is not a hardened multi-tenant adversarial-code boundary.
For an untrusted public service replace it with disposable microVMs and egress policy.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ALLOWED_IMAGE=re.compile(r'^[a-zA-Z0-9._/-]+(?::[a-zA-Z0-9._-]+)?$')
PACKAGE_LINE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9][A-Za-z0-9.!+_-]*$')


def run(files, install=False):
    if os.getenv('ENABLE_DOCKER_TESTS')!='1':
        return 'Docker test execution is disabled by default. Set ENABLE_DOCKER_TESTS=1.',None
    if not shutil.which('docker'):
        return 'Docker is not installed or not on PATH; tests were not executed.',None
    python=any(p.endswith('.py') and ('test_' in p or p.endswith('_test.py')) for p in files)
    node='package.json' in files and not python
    if not python and not node:
        return 'No Python tests or Node package.json found; static checks only.',None
    image=os.getenv('HITMAN_PYTHON_TEST_IMAGE' if python else 'HITMAN_NODE_TEST_IMAGE',
                    'python:3.12-slim' if python else 'node:22-alpine')
    if not ALLOWED_IMAGE.fullmatch(image) or image.startswith('-'):
        return 'Invalid sandbox image',None
    with tempfile.TemporaryDirectory(prefix='hitman-build-') as td:
        base=Path(td)
        root=base/'source';deps=base/'dependencies'
        root.mkdir(mode=0o777);deps.mkdir(mode=0o777)
        os.chmod(root,0o777);os.chmod(deps,0o777)
        for name,content in files.items():
            target=root/name
            target.parent.mkdir(parents=True,exist_ok=True)
            os.chmod(target.parent,0o755)
            target.write_text(content,encoding='utf-8')
            os.chmod(target,0o644)
        security=['--rm','--pull=never','--cap-drop','ALL',
                  '--security-opt','no-new-privileges','--pids-limit','90',
                  '--memory','768m','--cpus','1','--user','65534:65534',
                  '--tmpfs','/tmp:rw,nosuid,size=128m',
                  '--env','HOME=/tmp','--env','PIP_DISABLE_PIP_VERSION_CHECK=1',
                  '--env','PIP_NO_CACHE_DIR=1']
        source_mount=['--mount',f'type=bind,src={root},dst=/workspace,readonly']
        deps_mount=['--mount',f'type=bind,src={deps},dst=/deps']
        logs=[]
        def invoke(command,minutes):
            try:
                result=subprocess.run(command,text=True,capture_output=True,timeout=minutes,check=False)
                return result.returncode,(result.stdout+'\n'+result.stderr)[-10000:]
            except subprocess.TimeoutExpired:
                return 124,'Sandbox timed out.'
            except (OSError,subprocess.SubprocessError) as exc:
                return 125,'Sandbox failed: '+type(exc).__name__
        can_install=install and os.getenv('ENABLE_DEP_INSTALL')=='1'
        if python:
            requirements=files.get('requirements.txt','')
            if requirements:
                stripped=[line.strip() for line in requirements.splitlines() if line.strip() and not line.lstrip().startswith('#')]
                if any(not PACKAGE_LINE.fullmatch(x) for x in stripped):
                    return 'Dependency installation declined: requirements.txt must contain pinned package==version entries only.',None
            if can_install:
                cmd=['docker','run',*security,'--network','bridge','--read-only',*source_mount,*deps_mount,
                     '--workdir','/workspace',image,'python','-m','pip','install','--only-binary=:all:',
                     '--disable-pip-version-check','--retries','1','--timeout','12',
                     '--target','/deps','-r','/workspace/requirements.txt','pytest'] if requirements else [
                     'docker','run',*security,'--network','bridge','--read-only',*source_mount,*deps_mount,
                     '--workdir','/workspace',image,'python','-m','pip','install','--only-binary=:all:',
                     '--target','/deps','pytest']
                code,log=invoke(cmd,95);logs.append('Dependency stage:\n'+log)
                if code!=0: return '\n'.join(logs),False
            else:
                logs.append('Dependency install skipped (ENABLE_DEP_INSTALL must be 1 and install requested).')
            tests=['python','-m','pytest','-q']
            security += ['--env','PYTHONPATH=/deps:/workspace','--env','PYTHONDONTWRITEBYTECODE=1']
        else:
            if can_install:
                if 'package-lock.json' not in files:
                    return 'Dependency installation requires package-lock.json; upload a locked project.',None
                # npm ci requires a writable project; this is a temporary copy, not the original repo.
                cmd=['docker','run',*security,'--network','bridge',
                     '--mount',f'type=bind,src={root},dst=/workspace',
                     '--workdir','/workspace',image,'npm','ci','--ignore-scripts','--no-audit','--no-fund','--prefer-offline']
                code,log=invoke(cmd,100);logs.append('Dependency stage:\n'+log)
                if code!=0: return '\n'.join(logs),False
            else: logs.append('Dependency install skipped; test may fail if node_modules is absent.')
            tests=['npm','test','--','--runInBand'] if 'jest' in files.get('package.json','').lower() else ['npm','test']
        cmd=['docker','run',*security,'--network','none','--read-only',*source_mount,
             '--mount',f'type=bind,src={deps},dst=/deps,readonly',
             '--workdir','/workspace',image,*tests]
        code,log=invoke(cmd,90)
        logs.append('Offline test stage:\n'+log)
        return '\n'.join(logs)[-16000:],code==0
