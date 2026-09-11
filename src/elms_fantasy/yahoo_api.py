from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from elms_fantasy.yahoo_oauth import TOKEN_URL, yahoo_credentials

TOKEN_PATH = Path('.yahoo_tokens.json')
FANTASY_BASE = 'https://fantasysports.yahooapis.com/fantasy/v2'


def _load_tokens() -> dict:
    if not TOKEN_PATH.exists():
        raise RuntimeError('Missing .yahoo_tokens.json. Run: elms-fantasy yahoo-auth')
    return json.loads(TOKEN_PATH.read_text(encoding='utf-8'))


def _save_tokens(tokens: dict) -> None:
    TOKEN_PATH.write_text(json.dumps(tokens, indent=2), encoding='utf-8')


def refresh_access_token(tokens: dict | None = None) -> dict:
    tokens = dict(tokens or _load_tokens())
    refresh_token = tokens.get('refresh_token')
    if not refresh_token:
        raise RuntimeError('Yahoo refresh token is missing. Run: elms-fantasy yahoo-auth')

    client_id, client_secret, redirect_uri = yahoo_credentials()
    basic = base64.b64encode(f'{client_id}:{client_secret}'.encode('utf-8')).decode('ascii')
    body = urllib.parse.urlencode(
        {
            'grant_type': 'refresh_token',
            'redirect_uri': redirect_uri,
            'refresh_token': refresh_token,
        }
    ).encode('utf-8')
    request = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={
            'Authorization': f'Basic {basic}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        refreshed = json.loads(response.read().decode('utf-8'))

    if not refreshed.get('refresh_token'):
        refreshed['refresh_token'] = refresh_token
    _save_tokens(refreshed)
    return refreshed


def yahoo_get(path: str, retry_refresh: bool = True) -> dict:
    tokens = _load_tokens()
    access_token = tokens.get('access_token')
    if not access_token:
        tokens = refresh_access_token(tokens)
        access_token = tokens.get('access_token')

    url = path if path.startswith('http') else f"{FANTASY_BASE}/{path.lstrip('/')}"
    separator = '&' if '?' in url else '?'
    if 'format=' not in url:
        url = f'{url}{separator}format=json'

    request = urllib.request.Request(
        url,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
            'User-Agent': 'ELMS-Fantasy-Basketball/0.2',
        },
        method='GET',
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and retry_refresh:
            refresh_access_token(tokens)
            return yahoo_get(path, retry_refresh=False)
        body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Yahoo API HTTP {exc.code}: {body}') from exc


def get_basketball_leagues() -> dict:
    return yahoo_get('users;use_login=1/games;game_codes=nba/leagues')
