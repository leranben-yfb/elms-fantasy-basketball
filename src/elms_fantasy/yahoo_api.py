from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from elms_fantasy.yahoo_oauth import TOKEN_URL, yahoo_credentials

TOKEN_PATH = Path(".yahoo_tokens.json")
FANTASY_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"


@dataclass(frozen=True)
class YahooAPIError(RuntimeError):
    status: int
    body: str
    path: str
    problem: str | None = None

    def __str__(self) -> str:
        detail = f"Yahoo API HTTP {self.status}"
        if self.problem:
            detail += f" ({self.problem})"
        return f"{detail}: {self.body}"


def _load_tokens() -> dict[str, Any]:
    if not TOKEN_PATH.exists():
        raise RuntimeError("Missing .yahoo_tokens.json. Run: elms-fantasy yahoo-auth")
    return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))


def _save_tokens(tokens: dict[str, Any]) -> None:
    TOKEN_PATH.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def _extract_problem(body: str) -> str | None:
    markers = (
        'oauth_problem="',
        '"oauth_problem":"',
        "oauth_problem=",
    )
    for marker in markers:
        if marker in body:
            tail = body.split(marker, 1)[1]
            if marker.endswith('"'):
                return tail.split('"', 1)[0]
            return tail.split(",", 1)[0].split(" ", 1)[0].strip('"')
    if "additional_authorization_required" in body:
        return "additional_authorization_required"
    return None


def refresh_access_token(tokens: dict[str, Any] | None = None) -> dict[str, Any]:
    tokens = dict(tokens or _load_tokens())
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Yahoo refresh token is missing. Run: elms-fantasy yahoo-auth")

    client_id, client_secret, redirect_uri = yahoo_credentials()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "redirect_uri": redirect_uri,
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
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
        refreshed = json.loads(response.read().decode("utf-8"))

    # Yahoo can rotate refresh tokens. Preserve the previous token if omitted.
    if not refreshed.get("refresh_token"):
        refreshed["refresh_token"] = refresh_token
    _save_tokens(refreshed)
    return refreshed


def yahoo_get(path: str, retry_refresh: bool = True) -> dict[str, Any]:
    tokens = _load_tokens()
    access_token = tokens.get("access_token")
    if not access_token:
        tokens = refresh_access_token(tokens)
        access_token = tokens.get("access_token")

    url = path if path.startswith("http") else f"{FANTASY_BASE}/{path.lstrip('/')}"
    separator = "&" if "?" in url else "?"
    if "format=" not in url:
        url = f"{url}{separator}format=json"

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "ELMS-Fantasy-Basketball/0.3",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401 and retry_refresh and "additional_authorization_required" not in body:
            refresh_access_token(tokens)
            return yahoo_get(path, retry_refresh=False)
        raise YahooAPIError(
            status=exc.code,
            body=body,
            path=path,
            problem=_extract_problem(body),
        ) from exc


def get_basketball_leagues() -> dict[str, Any]:
    return yahoo_get("users;use_login=1/games;game_codes=nba/leagues")


def get_league_metadata(league_key: str) -> dict[str, Any]:
    return yahoo_get(f"league/{league_key}/metadata")


def get_league_settings(league_key: str) -> dict[str, Any]:
    return yahoo_get(f"league/{league_key}/settings")


def get_league_teams(league_key: str) -> dict[str, Any]:
    return yahoo_get(f"league/{league_key}/teams")


def get_league_standings(league_key: str) -> dict[str, Any]:
    return yahoo_get(f"league/{league_key}/standings")


def get_league_scoreboard(league_key: str, week: int | None = None) -> dict[str, Any]:
    suffix = f";week={week}" if week is not None else ""
    return yahoo_get(f"league/{league_key}/scoreboard{suffix}")


def get_league_transactions(league_key: str) -> dict[str, Any]:
    return yahoo_get(f"league/{league_key}/transactions")


def get_league_draft_results(league_key: str) -> dict[str, Any]:
    return yahoo_get(f"league/{league_key}/draftresults")


def get_team_roster(team_key: str, week: int | None = None, date: str | None = None) -> dict[str, Any]:
    qualifiers: list[str] = []
    if week is not None:
        qualifiers.append(f"week={week}")
    if date is not None:
        qualifiers.append(f"date={date}")
    suffix = ";" + ";".join(qualifiers) if qualifiers else ""
    return yahoo_get(f"team/{team_key}/roster{suffix}")


def get_team_matchups(team_key: str) -> dict[str, Any]:
    return yahoo_get(f"team/{team_key}/matchups")


def get_league_players(
    league_key: str,
    *,
    status: str | None = None,
    start: int = 0,
    count: int = 25,
) -> dict[str, Any]:
    qualifiers = [f"start={max(0, start)}", f"count={max(1, min(count, 100))}"]
    if status:
        qualifiers.append(f"status={status}")
    return yahoo_get(f"league/{league_key}/players;" + ";".join(qualifiers))


def provisioning_message(error: YahooAPIError) -> str | None:
    if error.problem == "additional_authorization_required":
        return (
            "OAuth is valid, but this Yahoo application is not authorized for the "
            "Fantasy Sports API. Yahoo must attach the approved Fantasy Sports "
            "permission to this Client ID; then run yahoo-auth again."
        )
    return None
