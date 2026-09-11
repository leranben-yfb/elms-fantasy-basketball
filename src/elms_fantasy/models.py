from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Player:
    player_id: str
    name: str
    positions: tuple[str, ...]
    team: str
    games_remaining: int = 0
    injury_status: str | None = None
    stats: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TeamRoster:
    team_id: str
    name: str
    players: tuple[Player, ...]


@dataclass(frozen=True)
class LeagueSettings:
    league_id: str
    name: str
    categories: tuple[str, ...]
    roster_slots: tuple[str, ...]
    max_adds_per_week: int | None = None


@dataclass(frozen=True)
class LeagueSnapshot:
    settings: LeagueSettings
    my_team: TeamRoster
    opponents: tuple[TeamRoster, ...] = ()
    free_agents: tuple[Player, ...] = ()


@dataclass(frozen=True)
class Recommendation:
    action: str
    player_in: str | None
    player_out: str | None
    score: float
    reasons: tuple[str, ...]


def sum_categories(players: Iterable[Player], categories: Iterable[str]) -> dict[str, float]:
    totals = {category: 0.0 for category in categories}
    for player in players:
        for category in totals:
            totals[category] += float(player.stats.get(category, 0.0))
    return totals
