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


def test_il_slots_do_not_create_draft_demand():
    settings = LeagueSettings("1", "Draft", ("PTS",), ("PG", "UTIL", "BN", "IL", "IL"))
    pool = (
        Player("1", "Guard", ("PG",), "X", stats={"PTS": 20}),
        Player("2", "Center", ("C",), "X", stats={"PTS": 19}),
    )
    snap = LeagueSnapshot(settings, TeamRoster("me", "Mine", ()), free_agents=pool)
    board = rank_draft_board(snap)
    assert all("IL" not in reason for rec in board for reason in rec.reasons)


def test_adp_does_not_change_intrinsic_score():
    settings = LeagueSettings("1", "Draft", ("PTS",), ("UTIL", "BN"))
    pool = (
        Player("1", "Early ADP", ("PG",), "X", stats={"PTS": 20, "_YAHOO_ADP": 1}),
        Player("2", "Late ADP", ("PG",), "X", stats={"PTS": 20, "_YAHOO_ADP": 100}),
    )
    snap = LeagueSnapshot(settings, TeamRoster("me", "Mine", ()), free_agents=pool)
    board = rank_draft_board(snap)
    assert board[0].score == board[1].score
    assert board[0].market_value == board[1].market_value == 0.0


def test_out_status_gets_stronger_penalty():
    settings = LeagueSettings("1", "Draft", ("PTS",), ("UTIL", "BN"))
    healthy = Player("1", "Healthy", ("PG",), "X", stats={"PTS": 20})
    injured = Player("2", "Injured", ("PG",), "X", injury_status="OUT", stats={"PTS": 20})
    snap = LeagueSnapshot(settings, TeamRoster("me", "Mine", ()), free_agents=(healthy, injured))
    board = rank_draft_board(snap)
    scores = {rec.player_id: rec.score for rec in board}
    assert scores["1"] > scores["2"]


def test_percentage_categories_use_attempt_volume():
    settings = LeagueSettings("1", "Draft", ("FG%",), ("UTIL",))
    low_volume = Player("1", "Low Volume", ("SG",), "X", stats={"FG%": 55.0, "FGA": 4.0})
    high_volume = Player("2", "High Volume", ("SG",), "X", stats={"FG%": 55.0, "FGA": 20.0})
    neutral = Player("3", "Neutral", ("SG",), "X", stats={"FG%": 45.0, "FGA": 12.0})
    snap = LeagueSnapshot(settings, TeamRoster("me", "Mine", ()), free_agents=(low_volume, high_volume, neutral))
    board = rank_draft_board(snap, limit=3)
    scores = {rec.player_id: rec.score for rec in board}
    assert scores["2"] > scores["1"]


def test_position_aware_vorp_is_exposed():
    settings = LeagueSettings("1", "Draft", ("PTS",), ("PG", "C", "UTIL", "BN"))
    pool = tuple(
        [Player(str(i), f"Guard {i}", ("PG",), "X", stats={"PTS": 30 - i}) for i in range(1, 9)]
        + [Player("20", "Rare Center", ("C",), "X", stats={"PTS": 25})]
        + [Player(str(i), f"Center {i}", ("C",), "X", stats={"PTS": 12 - (i - 21)}) for i in range(21, 25)]
    )
    snap = LeagueSnapshot(settings, TeamRoster("me", "Mine", ()), free_agents=pool)
    board = rank_draft_board(snap, limit=len(pool))
    center = next(rec for rec in board if rec.player_id == "20")
    assert center.vorp is not None
    assert center.replacement_level is not None
    assert any("VORP" in reason for reason in center.reasons)


def test_open_slot_matching_preserves_specialist_slot():
    from elms_fantasy.draft import _open_slots

    settings = LeagueSettings("1", "Draft", ("PTS",), ("PG", "G", "UTIL"))
    combo = Player("1", "Combo", ("PG", "SG"), "X", stats={"PTS": 20})
    specialist = Player("2", "Point Only", ("PG",), "X", stats={"PTS": 19})
    snap = LeagueSnapshot(settings, TeamRoster("me", "Mine", ()), free_agents=(combo, specialist))
    remaining = _open_slots(snap, (combo, specialist))
    assert remaining == ("UTIL",)
