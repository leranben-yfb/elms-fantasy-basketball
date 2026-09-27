from elms_fantasy.draft import rank_draft_board, record_pick
from elms_fantasy.models import LeagueSettings, LeagueSnapshot, Player, TeamRoster


def player(pid, name, pos, pts, reb, ast):
    return Player(pid, name, pos, "X", stats={"PTS": pts, "REB": reb, "AST": ast})


def snapshot():
    settings = LeagueSettings("1", "Draft", ("PTS", "REB", "AST"), ("PG", "SG", "SF", "PF", "C", "UTIL", "BN"))
    pool = (
        player("1", "Alpha Guard", ("PG",), 30, 4, 9),
        player("2", "Beta Wing", ("SG", "SF"), 24, 7, 5),
        player("3", "Gamma Big", ("C",), 20, 13, 2),
        player("4", "Delta Guard", ("PG", "SG"), 18, 3, 7),
    )
    return LeagueSnapshot(settings, TeamRoster("me", "Mine", ()), free_agents=pool)


def test_drafted_players_are_removed():
    board = rank_draft_board(snapshot(), drafted_ids={"1"})
    assert all(x.player_id != "1" for x in board)


def test_board_returns_ranked_recommendations():
    board = rank_draft_board(snapshot(), limit=3)
    assert len(board) == 3
    assert board[0].score >= board[1].score >= board[2].score


def test_record_pick_tracks_my_roster():
    state = {"drafted": [], "mine": []}
    picked = record_pick(snapshot(), state, "Alpha Guard", mine=True)
    assert picked.player_id in state["drafted"]
    assert picked.player_id in state["mine"]
