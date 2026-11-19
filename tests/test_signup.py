"""Public signup, login, isolation and access control without any real AI API calls."""
import tempfile
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
import workspace


def test_public_signup_and_login():
    with tempfile.TemporaryDirectory() as d:
        workspace.configure(Path(d)/'users.db', lambda _: {'README.md':'hello'}, lambda _: [],
                            lambda _: ('disabled',None),lambda: None,lambda:'model',lambda:{})
        app=FastAPI()
        app.include_router(workspace.router)
        a,b,visitor=TestClient(app),TestClient(app),TestClient(app)
        import account_security
        sent=[]
        account_security.send_email=lambda to,subject,body:sent.append((to,subject,body))
        password='A-strong-password-123'
        r=a.post('/api/auth/signup',json={'username':'alice','password':password,'email':'alice@example.org'})
        assert r.status_code==201,r.text
        assert 'Check your email' in r.json()['message']
        assert 'set-cookie' not in r.headers
        assert a.get('/api/auth/me').status_code==401
        assert a.post('/api/auth/login',json={'username':'alice','password':password}).status_code==403
        token=sent[-1][2].split('token=')[1].split()[0]
        app.include_router(account_security.router)
        assert a.post('/api/auth/verify-email',json={'token':token}).status_code==200
        assert a.post('/api/auth/login',json={'username':'alice','password':password}).status_code==200
        assert a.get('/api/auth/me').json()['username']=='alice'
        assert a.post('/api/auth/signup',json={'username':'alice','password':password,'email':'alice@example.org'}).status_code==409
        assert a.post('/api/auth/signup',json={'username':'bob','password':'short','email':'bob@example.org'}).status_code==422
        assert visitor.get('/api/workspaces').status_code==401
        assert b.post('/api/auth/login',json={'username':'bob','password':password}).status_code==401
        assert b.post('/api/auth/signup',json={'username':'bob','password':password,'email':'bob@example.org'}).status_code==201
        token=sent[-1][2].split('token=')[1].split()[0]
        assert b.post('/api/auth/verify-email',json={'token':token}).status_code==200
        assert b.post('/api/auth/login',json={'username':'bob','password':password}).status_code==200
        assert b.post('/api/auth/users',json={'username':'evelyn','password':password}).status_code==403
        project=a.post('/api/workspaces',json={'name':'Private project'}).json()['id']
        assert b.get('/api/workspaces/'+project).status_code==404
        assert b.get('/api/workspaces/'+project+'/download').status_code==404
        assert a.post('/api/auth/logout').status_code==200
        assert a.get('/api/workspaces').status_code==401
        assert a.post('/api/auth/login',json={'username':'alice','password':password,'email':'alice@example.org'}).status_code==200
        assert a.get('/api/workspaces/'+project).status_code==200
        assert a.post('/api/auth/setup',json={'username':'admin','password':password}).status_code in (403,409)
