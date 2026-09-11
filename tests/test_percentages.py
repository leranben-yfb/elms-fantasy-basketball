from elms_fantasy.models import Player, sum_categories


def player(pid: str, **stats: float) -> Player:
    return Player(pid, pid, ("G",), "X", stats=stats)


def test_fg_percentage_is_attempt_weighted():
    players = (
        player("high-volume", FGM=10, FGA=20, **{"FG%": 0.50}),
        player("low-volume", FGM=1, FGA=2, **{"FG%": 0.50}),
    )
    totals = sum_categories(players, ("FG%",))
    assert totals["FG%"] == 0.5


def test_ft_percentage_uses_makes_and_attempts():
    players = (
        player("a", FTM=8, FTA=10),
        player("b", FTM=1, FTA=2),
    )
    totals = sum_categories(players, ("FT%",))
    assert totals["FT%"] == 9 / 12


def test_percentage_falls_back_to_mean_when_attempts_missing():
    players = (
        player("a", **{"FG%": 0.4}),
        player("b", **{"FG%": 0.6}),
    )
    totals = sum_categories(players, ("FG%",))
    assert totals["FG%"] == 0.5
