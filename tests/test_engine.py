from elms_fantasy.engine import rank_free_agents, rank_streamers
from elms_fantasy.matchup import project_matchup
from elms_fantasy.models import LeagueSettings, LeagueSnapshot, Player, TeamRoster
from elms_fantasy.trades import evaluate_trade


def p(pid, name, pts, reb, ast, to=0, games=3):
    return Player(pid, name, ("G",), "X", games_remaining=games, stats={"PTS": pts, "REB": reb, "AST": ast, "TO": to})


def snap():
    settings = LeagueSettings("1", "Test", ("PTS", "REB", "AST", "TO"), ("G", "G"))
    mine = TeamRoster("me", "Mine", (p("1", "Low", 5, 2, 1, 4), p("2", "Star", 25, 8, 7, 2)))
    opp = TeamRoster("opp", "Opp", (p("3", "Opp1", 18, 6, 5, 3), p("4", "Opp2", 15, 7, 4, 2)))
    fas = (p("5", "Good FA", 20, 6, 6, 1, 4), p("6", "Bad FA", 4, 1, 1, 5, 2))
    return LeagueSnapshot(settings, mine, (opp,), fas, current_opponent_id="opp")


def test_waiver_ranking_prefers_good_fa():
    recs = rank_free_agents(snap())
    assert recs[0].player_in == "Good FA"
    assert recs[0].player_out == "Low"


def test_matchup_probability_is_bounded():
    s = snap()
    m = project_matchup(s.my_team, s.opponents[0], s.settings.categories)
    assert 0 <= m.matchup_win_probability <= 1
    assert len(m.categories) == 4


def test_streamer_uses_matchup():
    assert rank_streamers(snap())[0].player_in == "Good FA"


def test_trade_evaluation():
    s = snap()
    result = evaluate_trade(s, (s.free_agents[0],), (s.my_team.players[0],))
    assert result.score_delta > 0
    assert result.verdict == "ACCEPT"
