from __future__ import annotations

from statistics import mean, pstdev

from elms_fantasy.models import LOWER_IS_BETTER, LeagueSnapshot, Player


def category_weights(snapshot: LeagueSnapshot) -> dict[str, float]:
    categories = snapshot.settings.categories
    if not categories:
        return {}
    my = {c: sum(float(p.stats.get(c, 0.0)) for p in snapshot.my_team.players) for c in categories}
    if not snapshot.opponents:
        return {c: 1.0 for c in categories}

    weights: dict[str, float] = {}
    for c in categories:
        opp = [sum(float(p.stats.get(c, 0.0)) for p in t.players) for t in snapshot.opponents]
        benchmark = mean(opp) if opp else 0.0
        scale = abs(benchmark) or 1.0
        gap = (benchmark - my[c]) / scale
        if c.upper() in LOWER_IS_BETTER:
            gap *= -1
        weights[c] = max(0.35, min(2.5, 1.0 + gap))
    return weights


def population_zscores(players: tuple[Player, ...], categories: tuple[str, ...]) -> dict[str, dict[str, float]]:
    out = {p.player_id: {} for p in players}
    for category in categories:
        vals = [float(p.stats.get(category, 0.0)) for p in players]
        mu = mean(vals) if vals else 0.0
        sigma = pstdev(vals) if len(vals) > 1 else 0.0
        for p, value in zip(players, vals):
            z = 0.0 if sigma == 0 else (value - mu) / sigma
            if category.upper() in LOWER_IS_BETTER:
                z *= -1
            out[p.player_id][category] = z
    return out


def player_value(player: Player, categories: tuple[str, ...], weights: dict[str, float], zscores: dict[str, float] | None = None) -> float:
    if zscores is None:
        core = sum(float(player.stats.get(c, 0.0)) * weights.get(c, 1.0) for c in categories)
    else:
        core = sum(float(zscores.get(c, 0.0)) * weights.get(c, 1.0) for c in categories)
    games = max(player.games_remaining, 0)
    schedule_multiplier = 1.0 + min(games, 7) * 0.04
    injury = (player.injury_status or "").lower()
    injury_multiplier = 1.0
    if injury:
        injury_multiplier = 0.55 if any(x in injury for x in ("out", "injured", "susp")) else 0.82
    minutes_multiplier = 1.0 if player.minutes is None else max(0.70, min(1.10, player.minutes / 30.0))
    return core * schedule_multiplier * injury_multiplier * minutes_multiplier


def replacement_level(players: tuple[Player, ...], categories: tuple[str, ...], weights: dict[str, float]) -> float:
    if not players:
        return 0.0
    zs = population_zscores(players, categories)
    values = sorted(player_value(p, categories, weights, zs[p.player_id]) for p in players)
    idx = max(0, int(len(values) * 0.35) - 1)
    return values[idx]


def reliability_score(player: Player) -> float:
    score = 1.0
    if player.injury_status:
        score -= 0.25
    if player.minutes is not None:
        score += min(0.15, max(-0.15, (player.minutes - 24.0) / 100.0))
    if player.usage_rate is not None:
        score += min(0.10, max(-0.10, (player.usage_rate - 18.0) / 100.0))
    return max(0.4, min(1.2, score))
