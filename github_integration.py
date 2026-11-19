"""Private per-user GitHub integration: import small repositories and publish reviewable PRs.

Uses fine-grained user tokens encrypted at rest; never places a token in a Git URL,
subprocess, redirect, browser response, logs, or workspace source code.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from workspace import connection, current_user, owned_workspace, get_files
from account_security import quota, audit

router = APIRouter(prefix='/api',tags=['GitHub'])
REPO_NAME=re.compile(r'^[A-Za-z0-9_.-]{1,100}$')
BRANCH=re.compile(r'^[A-Za-z0-9_./-]{1,120}$')
SAFE_EXT={'.py','.js','.jsx','.ts','.tsx','.json','.md','.txt','.html','.css','.sql','.yaml','.yml','.toml','.ini','.java','.go','.rs','.sh','.xml','.properties'}
MAX_FILES=55
MAX_TOTAL=350_000

def init():
    with connection() as con:
        con.executescript('''
            CREATE TABLE IF NOT EXISTS github_tokens (
                user_id TEXT PRIMARY KEY, token_encrypted BLOB NOT NULL,
                login TEXT NOT NULL, connected_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS workspace_github (
                workspace_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
                repo_owner TEXT NOT NULL, repo_name TEXT NOT NULL,
                base_branch TEXT NOT NULL, base_sha TEXT NOT NULL,
                initial_hashes TEXT NOT NULL);
        ''')
        con.commit()

def encryptor():
    key=os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')
    if not key:
        raise HTTPException(503,'Set GITHUB_TOKEN_ENCRYPTION_KEY to enable private GitHub connections')
    try: return Fernet(key.encode())
    except Exception: raise HTTPException(503,'Invalid GitHub encryption key configuration')

def github_token(user):
    with connection() as con:
        row=con.execute('SELECT token_encrypted FROM github_tokens WHERE user_id=?',(user['id'],)).fetchone()
    if not row: raise HTTPException(409,'Connect GitHub first')
    try: return encryptor().decrypt(row['token_encrypted']).decode()
    except InvalidToken: raise HTTPException(503,'Could not decrypt GitHub credentials. Reconnect your account')

def api(token, method, endpoint, data=None):
    """Fixed API host: endpoint must be a server-constructed relative path."""
    if not endpoint.startswith('/') or '://' in endpoint or '\\' in endpoint or '..' in endpoint:
        raise HTTPException(400,'Invalid GitHub API path')
    url='https://api.github.com'+endpoint
    try:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response=client.request(method,url,headers={
                'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                'X-GitHub-Api-Version':'2026-03-10','User-Agent':'HITMAN-AI-Workspace'},json=data)
        if response.status_code >= 400:
            if response.status_code in (401,403):
                raise HTTPException(403,'GitHub token permission denied or API rate limit reached')
            if response.status_code == 404: raise HTTPException(404,'GitHub resource not found')
            if response.status_code == 409: raise HTTPException(409,'GitHub branch or repository conflict')
            if response.status_code == 422: raise HTTPException(422,'GitHub rejected the change; check permissions and branch state')
            raise HTTPException(502,'GitHub API request failed')
        if len(response.content)>3_000_000:
            raise HTTPException(413,'GitHub API response too large')
        return response.json() if response.content else {}
    except HTTPException: raise
    except (httpx.TimeoutException,httpx.RequestError,ValueError):
        raise HTTPException(502,'Unable to reach GitHub API')

def names(owner,repo):
    if not REPO_NAME.fullmatch(owner) or not REPO_NAME.fullmatch(repo):
        raise HTTPException(422,'Invalid GitHub owner/repository name')

def path_is_safe(path):
    from main import valid_project_path
    return (valid_project_path(path) and Path(path).suffix.lower() in SAFE_EXT
            and not any(s.lower() in ('secret','secrets','credentials','node_modules') for s in path.split('/'))
            and not any(x.lower().startswith(('.env','id_rsa')) for x in path.split('/')))

class TokenConnect(BaseModel):
    token: str = Field(min_length=20,max_length=500)

@router.post('/github/connect')
def connect(body:TokenConnect,user=Depends(current_user)):
    cipher=encryptor()
    profile=api(body.token,'GET','/user')
    login=profile.get('login','')
    if not REPO_NAME.fullmatch(login): raise HTTPException(502,'Unexpected GitHub profile')
    with connection() as con:
        con.execute('INSERT INTO github_tokens VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET token_encrypted=excluded.token_encrypted,login=excluded.login,connected_at=excluded.connected_at',
                    (user['id'],cipher.encrypt(body.token.encode()),login,int(time.time())))
        con.commit()
    audit('github_connected',user['id'])
    return {'connected':True,'login':login}

@router.get('/github/status')
def status(user=Depends(current_user)):
    with connection() as con:
        row=con.execute('SELECT login,connected_at FROM github_tokens WHERE user_id=?',(user['id'],)).fetchone()
    return {'connected':bool(row),'login':row['login'] if row else None}

@router.delete('/github/disconnect')
def disconnect(user=Depends(current_user)):
    with connection() as con:
        con.execute('DELETE FROM github_tokens WHERE user_id=?',(user['id'],))
        con.commit()
    audit('github_disconnected',user['id'])
    return {'connected':False}

@router.get('/github/repos')
def repos(user=Depends(current_user)):
    quota(user['id'],'github_list',100)
    data=api(github_token(user),'GET','/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member')
    return [{'name':r['name'],'full_name':r['full_name'],'private':r['private'],
             'default_branch':r.get('default_branch','main'), 'html_url':r.get('html_url'),
             'can_push':bool(r.get('permissions',{}).get('push'))} for r in data if r.get('name') and r.get('full_name')][:100]

class ImportRepo(BaseModel):
    owner: str=Field(min_length=1,max_length=100)
    repo: str=Field(min_length=1,max_length=100)

@router.post('/github/import')
def import_repo(body:ImportRepo,user=Depends(current_user)):
    from main import valid_project_path
    import uuid
    names(body.owner,body.repo)
    quota(user['id'],'github_import',30)
    token=github_token(user)
    prefix=f'/repos/{body.owner}/{body.repo}'
    repo=api(token,'GET',prefix)
    branch=repo.get('default_branch','main')
    if not BRANCH.fullmatch(branch): raise HTTPException(422,'Invalid default branch')
    branch_data=api(token,'GET',prefix+'/branches/'+quote(branch,safe=''))
    sha=branch_data['commit']['sha']
    commit_obj=api(token,'GET',prefix+'/git/commits/'+quote(sha,safe=''))
    tree=api(token,'GET',prefix+'/git/trees/'+commit_obj['tree']['sha']+'?recursive=1')
    if tree.get('truncated'): raise HTTPException(413,'GitHub tree was truncated; use a smaller repository')
    entries=[r for r in tree.get('tree',[]) if r.get('type')=='blob' and isinstance(r.get('path'),str) and path_is_safe(r['path']) and r.get('size',0)<=80000]
    if len(entries)>MAX_FILES: raise HTTPException(413,f'Repository exceeds {MAX_FILES} supported source files')
    if sum(r.get('size',0) for r in entries)>MAX_TOTAL: raise HTTPException(413,'Repository has too much source code for one workspace')
    files={}
    for r in entries:
        blob=api(token,'GET',prefix+'/git/blobs/'+quote(r['sha'],safe=''))
        if blob.get('encoding')!='base64': continue
        try: data=base64.b64decode(blob['content'])
        except Exception: raise HTTPException(502,'Invalid GitHub blob')
        if b'\x00' in data: continue
        try: files[r['path']]=data.decode('utf-8')
        except UnicodeDecodeError: continue
    if not files: raise HTTPException(422,'Repository has no supported UTF-8 source files')
    wid=str(uuid.uuid4())
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute('INSERT INTO workspaces VALUES (?,?,?,?)',(wid,user['id'],repo['full_name'],int(time.time())))
        con.executemany('INSERT INTO workspace_files VALUES (?,?,?)',[(wid,p,c) for p,c in files.items()])
        con.execute('INSERT INTO workspace_github VALUES (?,?,?,?,?,?,?)',
                    (wid,user['id'],body.owner,body.repo,branch,sha,
                     json.dumps({p:hashlib.sha256(c.encode()).hexdigest() for p,c in files.items()})))
        con.commit()
    audit('github_import',user['id'])
    return {'id':wid,'name':repo['full_name'],'files':len(files),'default_branch':branch}

@router.get('/workspaces/{workspace_id}/github')
def workspace_link(workspace_id:str,user=Depends(current_user)):
    owned_workspace(workspace_id,user)
    with connection() as con:
        row=con.execute('SELECT repo_owner,repo_name,base_branch,base_sha FROM workspace_github WHERE workspace_id=? AND owner_id=?',(workspace_id,user['id'])).fetchone()
    return {'linked':bool(row),**(dict(row) if row else {})}

class PublishRequest(BaseModel):
    confirmation: str
    title: str=Field(min_length=5,max_length=200)
    description: str=Field(default='',max_length=3000)

@router.post('/workspaces/{workspace_id}/github/pull-request')
def publish_pr(workspace_id:str,body:PublishRequest,user=Depends(current_user)):
    if body.confirmation != 'CREATE_PULL_REQUEST':
        raise HTTPException(400,'Explicit confirmation required')
    owned_workspace(workspace_id,user)
    quota(user['id'],'github_publish',20)
    with connection() as con:
        link=con.execute('SELECT * FROM workspace_github WHERE workspace_id=? AND owner_id=?',(workspace_id,user['id'])).fetchone()
    if not link: raise HTTPException(409,'This workspace was not imported from GitHub')
    token=github_token(user)
    files=get_files(workspace_id)
    hashes=json.loads(link['initial_hashes'])
    changed={p:c for p,c in files.items() if hashlib.sha256(c.encode()).hexdigest()!=hashes.get(p)}
    if not changed: raise HTTPException(409,'No changed files to publish')
    if len(changed)>16 or sum(len(c.encode()) for c in changed.values())>300_000:
        raise HTTPException(413,'Patch exceeds safe publishing limits')
    if not all(path_is_safe(p) for p in changed): raise HTTPException(400,'Patch contains a forbidden path')
    prefix=f"/repos/{link['repo_owner']}/{link['repo_name']}"
    branch=link['base_branch']
    remote=api(token,'GET',prefix+'/branches/'+quote(branch,safe=''))
    sha=remote['commit']['sha']
    if sha!=link['base_sha']:
        raise HTTPException(409,'Remote base branch advanced; re-import before publishing to avoid conflicts')
    parent=api(token,'GET',prefix+'/git/commits/'+sha)
    base_tree=parent['tree']['sha']
    newtree=api(token,'POST',prefix+'/git/trees',{
        'base_tree':base_tree,
        'tree':[{'path':p,'mode':'100644','type':'blob','content':content} for p,content in changed.items()]})
    commit=api(token,'POST',prefix+'/git/commits',{
        'message':'HITMAN AI: '+body.title,
        'tree':newtree['sha'],'parents':[sha]})
    head='hitman-ai/'+str(int(time.time()))+'-'+secrets.token_hex(3)
    api(token,'POST',prefix+'/git/refs',{'ref':'refs/heads/'+head,'sha':commit['sha']})
    pr=api(token,'POST',prefix+'/pulls',{
        'title':body.title,'body':body.description+'\n\nCreated from a user-approved HITMAN AI workspace. Review and run CI before merging.',
        'head':head,'base':branch,'draft':True})
    audit('github_pr_created',user['id'])
    return {'pull_request_url':pr['html_url'],'number':pr['number'],'branch':head,'files_changed':sorted(changed),'draft':True}
