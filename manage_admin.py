"""Server-operator CLI: create or promote an administrator (never web-exposed).
Run only from the trusted server shell; requires direct database file access.
"""
from getpass import getpass
import sqlite3
import sys
import time
import uuid

import main  # creates database tables/migrations
import workspace


def main_cli():
    print('HITMAN AI administrator setup — local trusted terminal only')
    username=input('Username (existing account to promote, or new account to create): ').strip()
    if not username or len(username)<3 or not all(ch.isascii() and (ch.isalnum() or ch in '_-') for ch in username):
        raise SystemExit('Invalid username')
    with workspace.connection() as con:
        row=con.execute('SELECT id,role FROM users WHERE username=?',(username,)).fetchone()
    if row:
        if row['role']=='admin': raise SystemExit('This user is already an administrator')
        confirm=input(f'Type PROMOTE {username} to grant this account full administrator rights: ')
        if confirm != 'PROMOTE '+username: raise SystemExit('No changes made')
        with workspace.connection() as con:
            con.execute("UPDATE users SET role='admin' WHERE id=?",(row['id'],))
            con.commit()
        print('Role upgraded. Sign out and sign back in to refresh session permissions.')
        return
    password=getpass('New admin password (12+ characters): ')
    verify=getpass('Repeat password: ')
    if len(password)<12 or password!=verify: raise SystemExit('Password mismatch or too short')
    confirm=input(f'Type CREATE {username} to create an administrator: ')
    if confirm!='CREATE '+username: raise SystemExit('No changes made')
    with workspace.connection() as con:
        con.execute('INSERT INTO users(id,username,password_hash,role,created_at,email,email_verified) VALUES (?,?,?,?,?,?,?)',
                    (str(uuid.uuid4()),username,workspace.pw_hash(password),'admin',int(time.time()),None,1))
        con.commit()
    print('Administrator created.')

if __name__=='__main__': main_cli()
