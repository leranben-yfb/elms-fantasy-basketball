from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

LOWER_IS_BETTER = frozenset({"TO", "TOV", "TURNOVERS"})
PERCENTAGE_CATEGORIES = frozenset({"FG%", "FT%", "FG_PCT", "FT_PCT"})


@dataclass(frozen=True)
class Player:
    player_id: str
    name: str
    positions: tuple[str, ...]
    team: str
    games_remaining: int = 0
    injury_status: str | None = None
    stats: dict[str, float] = field(default_factory=dict)
    minutes: float | None = None
    usage_rate: float | None = None
    roster_pct: float | None = None
    projected_games: tuple[str, ...] = ()


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
    scoring_type: str = "categories"
    playoff_start_week: int | None = None
    games_cap: int | None = None


@dataclass(frozen=True)
class LeagueSnapshot:
    settings: LeagueSettings
    my_team: TeamRoster
    opponents: tuple[TeamRoster, ...] = ()
    free_agents: tuple[Player, ...] = ()
    current_opponent_id: str | None = None
    as_of: str | None = None


@dataclass(frozen=True)
class Recommendation:
    action: str
    player_in: str | None
    player_out: str | None
    score: float
    reasons: tuple[str, ...]
    metadata: dict[str, float | str] = field(default_factory=dict)


@dataclass(frozen=True)
class CategoryProjection:
    category: str
    my_value: float
    opponent_value: float
    win_probability: float


@dataclass(frozen=True)
class MatchupProjection:
    categories: tuple[CategoryProjection, ...]
    expected_category_wins: float
    matchup_win_probability: float


@dataclass(frozen=True)
class TradeEvaluation:
    score_delta: float
    category_deltas: dict[str, float]
    players_in: tuple[str, ...]
    players_out: tuple[str, ...]
    verdict: str


def sum_categories(players: Iterable[Player], categories: Iterable[str]) -> dict[str, float]:
    totals = {category: 0.0 for category in categories}
    for player in players:
        for category in totals:
            totals[category] += float(player.stats.get(category, 0.0))
    return totals
