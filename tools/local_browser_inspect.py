"""Opt-in, read-only local browser inspection for HITMAN AI developers.

This is NOT autonomous computer use, does not run on Render, does not click,
submit forms or execute shell code. Requires Playwright and Chromium locally.
The user must explicitly specify allowed website hosts.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlparse


def validate_url(url: str, allowed_hosts: list[str]) -> str:
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only public HTTPS URLs without embedded credentials are allowed')
    host = parsed.hostname.lower().rstrip('.')
    if not allowed_hosts or host not in {h.lower().strip().rstrip('.') for h in allowed_hosts}:
        raise ValueError('URL hostname must be included in --allow-host')
    if parsed.port not in (None, 443):
        raise ValueError('Custom ports are not allowed')
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError('Could not resolve the destination') from exc
    for entry in addresses:
        address=ipaddress.ip_address(entry[4][0])
        if not address.is_global:
            raise ValueError('Local, private and reserved destinations are prohibited')
    return url


def main():
    parser=argparse.ArgumentParser(description='Inspect a user-approved public webpage, read-only')
    parser.add_argument('--url',required=True,help='Public HTTPS webpage URL')
    parser.add_argument('--allow-host',action='append',required=True,help='Hostname approved by the user')
    parser.add_argument('--output',default='browser-inspection',help='Output directory for screenshot and page text')
    args=parser.parse_args()
    url=validate_url(args.url,args.allow_host)
    # Not installed on Render; explicit local developer tool only.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit('Install locally: pip install playwright && playwright install chromium')
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    # This script never modifies the HITMAN AI application or a Git repository.
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(accept_downloads=False,permissions=[],java_script_enabled=True)
        def route_handler(route):
            try:
                target=validate_url(route.request.url,args.allow_host)
                if target:route.continue_()
            except ValueError:
                route.abort()
        context.route('**/*',route_handler)
        page=context.new_page()
        page.goto(url,wait_until='domcontentloaded',timeout=20000)
        page.wait_for_timeout(1000)
        title=page.title()
        text=page.locator('body').inner_text(timeout=5000)[:20000]
        page.screenshot(path=str(out/'page.png'),full_page=False)
        (out/'page.txt').write_text(text,encoding='utf8')
        (out/'metadata.json').write_text(json.dumps({'url':url,'title':title},indent=2),encoding='utf8')
        browser.close()
    print('Saved read-only website inspection in',out)

if __name__=='__main__':
    main()
