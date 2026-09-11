from __future__ import annotations

import json
from pathlib import Path

from elms_fantasy.models import LeagueSettings, LeagueSnapshot, Player, TeamRoster
from elms_fantasy.providers.base import FantasyProvider


def _player(raw: dict) -> Player:
    return Player(
        player_id=str(raw["player_id"]),
        name=raw["name"],
        positions=tuple(raw.get("positions", [])),
        team=raw.get("team", ""),
        games_remaining=int(raw.get("games_remaining", 0)),
        injury_status=raw.get("injury_status"),
        stats={k: float(v) for k, v in raw.get("stats", {}).items()},
    )


def _team(raw: dict) -> TeamRoster:
    return TeamRoster(
        team_id=str(raw["team_id"]),
        name=raw["name"],
        players=tuple(_player(p) for p in raw.get("players", [])),
    )


class JsonFileProvider(FantasyProvider):
    """Local provider used while Yahoo credentials are unavailable."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def get_snapshot(self) -> LeagueSnapshot:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        settings_raw = raw["settings"]
        settings = LeagueSettings(
            league_id=str(settings_raw["league_id"]),
            name=settings_raw["name"],
            categories=tuple(settings_raw["categories"]),
            roster_slots=tuple(settings_raw.get("roster_slots", [])),
            max_adds_per_week=settings_raw.get("max_adds_per_week"),
        )
        return LeagueSnapshot(
            settings=settings,
            my_team=_team(raw["my_team"]),
            opponents=tuple(_team(t) for t in raw.get("opponents", [])),
            free_agents=tuple(_player(p) for p in raw.get("free_agents", [])),
        )
