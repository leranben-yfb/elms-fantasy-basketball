from __future__ import annotations

from math import erf, sqrt

from elms_fantasy.models import LOWER_IS_BETTER, CategoryProjection, MatchupProjection, TeamRoster, sum_categories


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def project_matchup(my_team: TeamRoster, opponent: TeamRoster, categories: tuple[str, ...]) -> MatchupProjection:
    mine = sum_categories(my_team.players, categories)
    theirs = sum_categories(opponent.players, categories)
    projections: list[CategoryProjection] = []
    probs: list[float] = []
    for c in categories:
        a, b = mine[c], theirs[c]
        diff = a - b
        if c.upper() in LOWER_IS_BETTER:
            diff *= -1
        scale = max(abs(a), abs(b), 1.0) * 0.18
        p = _normal_cdf(diff / scale)
        projections.append(CategoryProjection(c, a, b, p))
        probs.append(p)
    expected = sum(probs)
    if not probs:
        overall = 0.5
    else:
        threshold = len(probs) / 2
        overall = _normal_cdf((expected - threshold) / max(0.75, sqrt(len(probs)) * 0.35))
    return MatchupProjection(tuple(projections), expected, overall)
