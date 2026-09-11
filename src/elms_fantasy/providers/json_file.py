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
        minutes=float(raw["minutes"]) if raw.get("minutes") is not None else None,
        usage_rate=float(raw["usage_rate"]) if raw.get("usage_rate") is not None else None,
        roster_pct=float(raw["roster_pct"]) if raw.get("roster_pct") is not None else None,
        projected_games=tuple(raw.get("projected_games", [])),
    )


def _team(raw: dict) -> TeamRoster:
    return TeamRoster(team_id=str(raw["team_id"]), name=raw["name"], players=tuple(_player(p) for p in raw.get("players", [])))


class JsonFileProvider(FantasyProvider):
    """Local normalized provider used before or alongside Yahoo ingestion."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def get_snapshot(self) -> LeagueSnapshot:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        s = raw["settings"]
        settings = LeagueSettings(
            league_id=str(s["league_id"]),
            name=s["name"],
            categories=tuple(s["categories"]),
            roster_slots=tuple(s.get("roster_slots", [])),
            max_adds_per_week=s.get("max_adds_per_week"),
            scoring_type=s.get("scoring_type", "categories"),
            playoff_start_week=s.get("playoff_start_week"),
            games_cap=s.get("games_cap"),
        )
        return LeagueSnapshot(
            settings=settings,
            my_team=_team(raw["my_team"]),
            opponents=tuple(_team(t) for t in raw.get("opponents", [])),
            free_agents=tuple(_player(p) for p in raw.get("free_agents", [])),
            current_opponent_id=raw.get("current_opponent_id"),
            as_of=raw.get("as_of"),
        )
