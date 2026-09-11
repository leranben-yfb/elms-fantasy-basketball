from __future__ import annotations

from dataclasses import replace

from elms_fantasy.matchup import project_matchup
from elms_fantasy.models import LeagueSnapshot, Player, Recommendation, TeamRoster
from elms_fantasy.valuation import category_weights, player_value, population_zscores


def _candidate_pool(snapshot: LeagueSnapshot) -> tuple[Player, ...]:
    return tuple(snapshot.my_team.players) + tuple(snapshot.free_agents)


def rank_free_agents(snapshot: LeagueSnapshot, limit: int = 10) -> list[Recommendation]:
    categories = snapshot.settings.categories
    weights = category_weights(snapshot)
    pool = _candidate_pool(snapshot)
    zscores = population_zscores(pool, categories)
    roster = list(snapshot.my_team.players)
    drop_candidates = sorted(roster, key=lambda p: player_value(p, categories, weights, zscores.get(p.player_id, {})))
    weakest = drop_candidates[0] if drop_candidates else None
    weakest_score = player_value(weakest, categories, weights, zscores.get(weakest.player_id, {})) if weakest else 0.0

    recommendations: list[Recommendation] = []
    for fa in snapshot.free_agents:
        incoming = player_value(fa, categories, weights, zscores.get(fa.player_id, {}))
        delta = incoming - weakest_score
        reasons = [f"Estimated roster value change: {delta:+.2f}"]
        priority = sorted(categories, key=lambda c: weights.get(c, 1.0), reverse=True)[:3]
        helpful = [c for c in priority if zscores.get(fa.player_id, {}).get(c, 0.0) > 0]
        if helpful:
            reasons.append("Helps priority categories: " + ", ".join(helpful))
        if fa.games_remaining:
            reasons.append(f"{fa.games_remaining} games remaining in evaluation window")
        if fa.injury_status:
            reasons.append(f"Availability flag: {fa.injury_status}")
        recommendations.append(Recommendation(action="ADD_DROP" if weakest else "ADD", player_in=fa.name, player_out=weakest.name if weakest else None, score=delta, reasons=tuple(reasons), metadata={"incoming_value": incoming, "outgoing_value": weakest_score}))
    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations[:limit]


def rank_streamers(snapshot: LeagueSnapshot, opponent: TeamRoster | None = None, limit: int = 10) -> list[Recommendation]:
    base = rank_free_agents(snapshot, limit=max(limit * 3, 20))
    if opponent is None and snapshot.current_opponent_id:
        opponent = next((t for t in snapshot.opponents if t.team_id == snapshot.current_opponent_id), None)
    if opponent is None:
        return base[:limit]

    baseline = project_matchup(snapshot.my_team, opponent, snapshot.settings.categories)
    by_name = {p.name: p for p in snapshot.free_agents}
    roster_by_name = {p.name: p for p in snapshot.my_team.players}
    rescored: list[Recommendation] = []
    for rec in base:
        incoming = by_name.get(rec.player_in or "")
        outgoing = roster_by_name.get(rec.player_out or "")
        if incoming is None:
            continue
        players = [p for p in snapshot.my_team.players if outgoing is None or p.player_id != outgoing.player_id] + [incoming]
        new_team = TeamRoster(snapshot.my_team.team_id, snapshot.my_team.name, tuple(players))
        after = project_matchup(new_team, opponent, snapshot.settings.categories)
        swing = after.matchup_win_probability - baseline.matchup_win_probability
        reasons = rec.reasons + (f"Estimated matchup win-probability swing: {swing:+.1%}",)
        rescored.append(replace(rec, score=rec.score + swing * 10.0, reasons=reasons, metadata={**rec.metadata, "matchup_swing": swing}))
    return sorted(rescored, key=lambda r: r.score, reverse=True)[:limit]
