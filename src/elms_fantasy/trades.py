from __future__ import annotations

from elms_fantasy.models import LeagueSnapshot, Player, TradeEvaluation
from elms_fantasy.valuation import category_weights, player_value, population_zscores


def evaluate_trade(snapshot: LeagueSnapshot, players_in: tuple[Player, ...], players_out: tuple[Player, ...]) -> TradeEvaluation:
    categories = snapshot.settings.categories
    weights = category_weights(snapshot)
    pool = tuple(snapshot.my_team.players) + players_in + players_out + tuple(snapshot.free_agents)
    z = population_zscores(pool, categories)
    incoming = sum(player_value(p, categories, weights, z[p.player_id]) for p in players_in)
    outgoing = sum(player_value(p, categories, weights, z[p.player_id]) for p in players_out)
    deltas = {c: sum(p.stats.get(c, 0.0) for p in players_in) - sum(p.stats.get(c, 0.0) for p in players_out) for c in categories}
    delta = incoming - outgoing
    verdict = "ACCEPT" if delta > 0.35 else "REJECT" if delta < -0.35 else "NEUTRAL"
    return TradeEvaluation(delta, deltas, tuple(p.name for p in players_in), tuple(p.name for p in players_out), verdict)
