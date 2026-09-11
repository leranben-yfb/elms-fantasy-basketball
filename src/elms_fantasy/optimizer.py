from __future__ import annotations

from elms_fantasy.models import LeagueSnapshot, Player
from elms_fantasy.valuation import category_weights, player_value, population_zscores


def best_roster(snapshot: LeagueSnapshot, roster_size: int | None = None) -> tuple[Player, ...]:
    size = roster_size or len(snapshot.my_team.players)
    candidates = tuple(snapshot.my_team.players) + tuple(snapshot.free_agents)
    if size <= 0 or not candidates:
        return ()
    weights = category_weights(snapshot)
    z = population_zscores(candidates, snapshot.settings.categories)
    ranked = sorted(candidates, key=lambda p: player_value(p, snapshot.settings.categories, weights, z[p.player_id]), reverse=True)
    return tuple(ranked[:size])


def best_single_swap(snapshot: LeagueSnapshot) -> tuple[Player | None, Player | None, float]:
    recs = []
    weights = category_weights(snapshot)
    pool = tuple(snapshot.my_team.players) + tuple(snapshot.free_agents)
    z = population_zscores(pool, snapshot.settings.categories)
    for fa in snapshot.free_agents:
        for current in snapshot.my_team.players:
            delta = player_value(fa, snapshot.settings.categories, weights, z[fa.player_id]) - player_value(current, snapshot.settings.categories, weights, z[current.player_id])
            recs.append((fa, current, delta))
    return max(recs, key=lambda x: x[2]) if recs else (None, None, 0.0)
