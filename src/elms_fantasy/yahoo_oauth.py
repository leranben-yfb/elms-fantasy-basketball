from __future__ import annotations

import base64
import json
import os
import secrets
import urllib.parse
import urllib.request
from pathlib import Path

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
DEFAULT_TOKEN_PATH = Path(".yahoo_tokens.json")


def load_env_file(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs without adding a runtime dependency."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def yahoo_credentials() -> tuple[str, str, str]:
    load_env_file()
    client_id = os.getenv("YAHOO_CLIENT_ID", "").strip()
    client_secret = os.getenv("YAHOO_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("YAHOO_REDIRECT_URI", "https://localhost:8000/callback").strip()
    if not client_id or not client_secret:
        raise RuntimeError("YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET must be configured in .env")
    return client_id, client_secret, redirect_uri


def build_authorization_url() -> tuple[str, str]:
    client_id, _, redirect_uri = yahoo_credentials()
    state = secrets.token_urlsafe(24)
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
    )
    return f"{AUTH_URL}?{query}", state


def extract_code(value: str, expected_state: str | None = None) -> str:
    value = value.strip()
    if not value:
        raise ValueError("No authorization code or callback URL was provided")
    if "://" not in value:
        return value
    parsed = urllib.parse.urlparse(value)
    params = urllib.parse.parse_qs(parsed.query)
    if "error" in params:
        raise RuntimeError(f"Yahoo authorization error: {params['error'][0]}")
    if expected_state and params.get("state", [None])[0] != expected_state:
        raise RuntimeError("OAuth state mismatch; restart authorization")
    code = params.get("code", [""])[0]
    if not code:
        raise ValueError("Callback URL does not contain a code parameter")
    return code


def exchange_code(code: str, token_path: str | Path = DEFAULT_TOKEN_PATH) -> dict:
    client_id, client_secret, redirect_uri = yahoo_credentials()
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
    ).encode("utf-8")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    Path(token_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
