"""Account verification, recovery, durable rate limits and audit records.

This module never sends passwords or tokens to logs in production. SMTP is mandatory
for public deployment. Local console delivery is for loopback development only.
"""
import hashlib
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from email.message import EmailMessage
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api/auth', tags=['accounts'])
EMAIL_RE = re.compile(r'^[^\s@]{1,64}@[^\s@]{1,190}\.[A-Za-z]{2,}$')

def database():
    import workspace
    return workspace.connection()


def init():
    with database() as con:
        columns={r['name'] for r in con.execute('PRAGMA table_info(users)')}
        if 'email' not in columns:
            con.execute('ALTER TABLE users ADD COLUMN email TEXT')
        if 'email_verified' not in columns:
            con.execute('ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0')
        con.executescript('''
            CREATE UNIQUE INDEX IF NOT EXISTS users_email_index ON users(email COLLATE NOCASE) WHERE email IS NOT NULL;
            CREATE TABLE IF NOT EXISTS account_tokens (
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, purpose TEXT NOT NULL,
                expires_at INTEGER NOT NULL, used_at INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS rate_limits (
                bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, since INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT NOT NULL,
                created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS api_usage (
                user_id TEXT NOT NULL, action TEXT NOT NULL, day TEXT NOT NULL,
                count INTEGER NOT NULL, PRIMARY KEY(user_id,action,day));
            ''')
        con.commit()


def audit(action: str, user_id=None):
    with database() as con:
        con.execute('INSERT INTO security_events(user_id,action,created_at) VALUES (?,?,?)',
                    (user_id, action[:60], int(time.time())))
        con.commit()


def rate_limit(key: str, max_requests: int, period: int):
    """Single-instance SQLite rate limiter. A distributed deployment requires Redis/WAF."""
    hashed=hashlib.sha256(key.encode()).hexdigest()
    now=int(time.time())
    with database() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT count,since FROM rate_limits WHERE bucket=?',(hashed,)).fetchone()
        if row and now-row['since'] < period:
            if row['count']>=max_requests:
                raise HTTPException(429, 'Too many requests. Please try again later.', headers={'Retry-After':str(period-(now-row['since']))})
            con.execute('UPDATE rate_limits SET count=count+1 WHERE bucket=?',(hashed,))
        else:
            con.execute('INSERT INTO rate_limits(bucket,count,since) VALUES (?,?,?) ON CONFLICT(bucket) DO UPDATE SET count=1,since=excluded.since',(hashed,1,now))
        con.commit()


def request_ip(request: Request):
    # Untrusted X-Forwarded-For is deliberately ignored. Configure trusted reverse proxies externally.
    return request.client.host if request.client else 'unknown'


def quota(user_id, action, limit):
    day=time.strftime('%Y-%m-%d',time.gmtime())
    with database() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT count FROM api_usage WHERE user_id=? AND action=? AND day=?',(user_id,action,day)).fetchone()
        if row and row['count']>=limit:
            raise HTTPException(429,'Daily usage cap reached for this feature.')
        con.execute('INSERT INTO api_usage VALUES (?,?,?,1) ON CONFLICT(user_id,action,day) DO UPDATE SET count=count+1',(user_id,action,day))
        con.commit()


def issue_token(user_id, purpose, expires):
    value=secrets.token_urlsafe(36)
    digest=hashlib.sha256(value.encode()).hexdigest()
    with database() as con:
        con.execute('DELETE FROM account_tokens WHERE user_id=? AND purpose=?',(user_id,purpose))
        con.execute('INSERT INTO account_tokens(token_hash,user_id,purpose,expires_at) VALUES (?,?,?,?)',
                    (digest,user_id,purpose,int(time.time())+expires))
        con.commit()
    return value


def consume_token(value, purpose):
    digest=hashlib.sha256(value.encode()).hexdigest()
    now=int(time.time())
    with database() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT user_id FROM account_tokens WHERE token_hash=? AND purpose=? AND used_at IS NULL AND expires_at>?',
                        (digest,purpose,now)).fetchone()
        if not row:
            raise HTTPException(400,'This link has expired or has already been used.')
        con.execute('UPDATE account_tokens SET used_at=? WHERE token_hash=?',(now,digest))
        con.commit()
    return row['user_id']


def send_email(email, subject, text):
    transport=os.getenv('EMAIL_TRANSPORT','console').lower()
    if transport=='console':
        if os.getenv('APP_ENV','development') != 'development':
            raise RuntimeError('Console email transport disabled outside local development')
        # Only show tokens on local developer console; never enable on hosted machines.
        print('\n[LOCAL-DEV EMAIL] To:',email,'Subject:',subject,'\n',text,'\n')
        return
    if transport!='smtp':
        raise RuntimeError('EMAIL_TRANSPORT must be smtp or local-only console')
    host=os.getenv('SMTP_HOST','')
    sender=os.getenv('SMTP_FROM','')
    if not host or not sender: raise RuntimeError('SMTP_HOST and SMTP_FROM required')
    message=EmailMessage()
    message['From']=sender
    message['To']=email
    message['Subject']=subject
    message.set_content(text)
    port=int(os.getenv('SMTP_PORT','587'))
    timeout=12
    if port==465:
        with smtplib.SMTP_SSL(host,port,timeout=timeout,context=ssl.create_default_context()) as smtp:
            if os.getenv('SMTP_USERNAME'): smtp.login(os.environ['SMTP_USERNAME'],os.environ.get('SMTP_PASSWORD',''))
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host,port,timeout=timeout) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if os.getenv('SMTP_USERNAME'): smtp.login(os.environ['SMTP_USERNAME'],os.environ.get('SMTP_PASSWORD',''))
            smtp.send_message(message)


def send_account_link(email, user_id, purpose):
    base=os.getenv('PUBLIC_BASE_URL','http://127.0.0.1:8000').rstrip('/')
    if os.getenv('APP_ENV')=='production' and not base.startswith('https://'):
        raise RuntimeError('Production links require HTTPS')
    value=issue_token(user_id,purpose,86400 if purpose=='verify' else 1800)
    page='verify-email' if purpose=='verify' else 'reset-password'
    link=f'{base}/{page}?token={quote(value)}'
    send_email(email,'Verify your HITMAN AI email' if purpose=='verify' else 'Reset your HITMAN AI password',
               f'Use this one-time link to {"verify your email" if purpose=="verify" else "reset your password"}:\n{link}\nIf you did not request this, ignore this message.')


class TokenBody(BaseModel):
    token: str = Field(min_length=15,max_length=300)

class EmailBody(BaseModel):
    email: str = Field(min_length=6,max_length=254)

class ResetBody(TokenBody):
    new_password: str = Field(min_length=12,max_length=200)

@router.post('/verify-email')
def verify_email(body: TokenBody, request: Request):
    rate_limit('verify:'+request_ip(request),20,900)
    ident=consume_token(body.token,'verify')
    with database() as con:
        con.execute('UPDATE users SET email_verified=1 WHERE id=?',(ident,))
        con.commit()
    audit('email_verified',ident)
    return {'ok':True,'message':'Email verified. You can now sign in.'}

@router.post('/resend-verification')
def resend_verification(body: EmailBody, request: Request):
    rate_limit('resend:'+request_ip(request),5,3600)
    with database() as con:
        row=con.execute('SELECT id,email_verified FROM users WHERE email=? COLLATE NOCASE',(body.email.strip().lower(),)).fetchone()
    if row and not row['email_verified']:
        try: send_account_link(body.email.strip().lower(),row['id'],'verify')
        except Exception: raise HTTPException(503,'Email delivery is currently unavailable.')
    return {'message':'If an unverified account exists, a verification email has been sent.'}

@router.post('/forgot-password')
def forgot_password(body: EmailBody, request: Request):
    rate_limit('forgot:'+request_ip(request),5,3600)
    with database() as con:
        row=con.execute('SELECT id FROM users WHERE email=? COLLATE NOCASE',(body.email.strip().lower(),)).fetchone()
    if row:
        try: send_account_link(body.email.strip().lower(),row['id'],'reset')
        except Exception: raise HTTPException(503,'Email delivery is currently unavailable.')
    return {'message':'If an account exists, a password reset email has been sent.'}

@router.post('/reset-password')
def reset_password(body: ResetBody, request: Request):
    rate_limit('reset:'+request_ip(request),10,900)
    import workspace
    ident=consume_token(body.token,'reset')
    with database() as con:
        con.execute('UPDATE users SET password_hash=? WHERE id=?',(workspace.pw_hash(body.new_password),ident))
        con.execute('DELETE FROM sessions WHERE user_id=?',(ident,))
        con.execute('DELETE FROM account_tokens WHERE user_id=?',(ident,))
        con.commit()
    audit('password_reset',ident)
    return {'ok':True,'message':'Password updated. Sign in with your new password.'}
