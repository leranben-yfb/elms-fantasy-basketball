from __future__ import annotations

from statistics import mean, pstdev

from elms_fantasy.models import LeagueSnapshot, Player, Recommendation


def _category_weights(snapshot: LeagueSnapshot) -> dict[str, float]:
    categories = snapshot.settings.categories
    my_totals = {c: sum(p.stats.get(c, 0.0) for p in snapshot.my_team.players) for c in categories}
    if not snapshot.opponents:
        return {c: 1.0 for c in categories}

    opp_totals: dict[str, list[float]] = {c: [] for c in categories}
    for team in snapshot.opponents:
        for c in categories:
            opp_totals[c].append(sum(p.stats.get(c, 0.0) for p in team.players))

    weights: dict[str, float] = {}
    for c in categories:
        benchmark = mean(opp_totals[c]) if opp_totals[c] else 0.0
        gap = benchmark - my_totals[c]
        scale = abs(benchmark) or 1.0
        weights[c] = 1.0 + max(-0.5, min(1.5, gap / scale))
    return weights


def _player_score(player: Player, categories: tuple[str, ...], weights: dict[str, float]) -> float:
    raw = sum(float(player.stats.get(c, 0.0)) * weights[c] for c in categories)
    schedule_boost = 1.0 + min(max(player.games_remaining, 0), 7) * 0.03
    injury_penalty = 0.70 if player.injury_status else 1.0
    return raw * schedule_boost * injury_penalty


def rank_free_agents(snapshot: LeagueSnapshot, limit: int = 10) -> list[Recommendation]:
    categories = snapshot.settings.categories
    weights = _category_weights(snapshot)
    roster = list(snapshot.my_team.players)
    if not roster:
        drop_candidates: list[Player | None] = [None]
    else:
        drop_candidates = sorted(roster, key=lambda p: _player_score(p, categories, weights))

    recommendations: list[Recommendation] = []
    for free_agent in snapshot.free_agents:
        incoming = _player_score(free_agent, categories, weights)
        outgoing_player = drop_candidates[0]
        outgoing = _player_score(outgoing_player, categories, weights) if outgoing_player else 0.0
        delta = incoming - outgoing
        reasons = [f"Projected weighted roster improvement: {delta:.2f}"]
        if free_agent.games_remaining:
            reasons.append(f"{free_agent.games_remaining} games remaining in the evaluation window")
        weak_categories = sorted(categories, key=lambda c: weights[c], reverse=True)[:3]
        helpful = [c for c in weak_categories if free_agent.stats.get(c, 0.0) > 0]
        if helpful:
            reasons.append("Helps priority categories: " + ", ".join(helpful))
        recommendations.append(
            Recommendation(
                action="ADD_DROP" if outgoing_player else "ADD",
                player_in=free_agent.name,
                player_out=outgoing_player.name if outgoing_player else None,
                score=delta,
                reasons=tuple(reasons),
            )
        )

    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations[:limit]
