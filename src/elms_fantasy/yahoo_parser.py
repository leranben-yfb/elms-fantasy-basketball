from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class YahooLeagueSummary:
    league_key: str
    league_id: str | None
    name: str
    season: str | None = None
    game_code: str | None = None
    url: str | None = None


def walk(value: Any) -> Iterable[Any]:
    """Depth-first traversal of Yahoo's deeply nested/numerically keyed JSON."""
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def _string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        return str(value)
    return None


def find_leagues(payload: dict[str, Any]) -> tuple[YahooLeagueSummary, ...]:
    """Extract league summaries without depending on Yahoo's numeric wrapper keys."""
    found: dict[str, YahooLeagueSummary] = {}
    for node in walk(payload):
        if not isinstance(node, dict):
            continue
        league_key = _string(node.get("league_key"))
        name = _string(node.get("name"))
        if not league_key or not name:
            continue
        found[league_key] = YahooLeagueSummary(
            league_key=league_key,
            league_id=_string(node.get("league_id")),
            name=name,
            season=_string(node.get("season")),
            game_code=_string(node.get("code") or node.get("game_code")),
            url=_string(node.get("url")),
        )
    return tuple(found.values())


def find_team_keys(payload: dict[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for node in walk(payload):
        if isinstance(node, dict):
            value = _string(node.get("team_key"))
            if value and value not in keys:
                keys.append(value)
    return tuple(keys)


def find_player_keys(payload: dict[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for node in walk(payload):
        if isinstance(node, dict):
            value = _string(node.get("player_key"))
            if value and value not in keys:
                keys.append(value)
    return tuple(keys)


def compact_league_payload(payload: dict[str, Any]) -> list[dict[str, str | None]]:
    return [
        {
            "league_key": league.league_key,
            "league_id": league.league_id,
            "name": league.name,
            "season": league.season,
            "game_code": league.game_code,
        }
        for league in find_leagues(payload)
    ]
