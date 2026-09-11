from elms_fantasy.yahoo_api import YahooAPIError, provisioning_message
from elms_fantasy.yahoo_parser import find_leagues, find_player_keys, find_team_keys


def test_find_leagues_handles_numeric_wrappers():
    payload = {
        "fantasy_content": {
            "users": {
                "0": {
                    "user": [
                        {"guid": "abc"},
                        {
                            "games": {
                                "0": {
                                    "game": [
                                        {"code": "nba", "season": "2026"},
                                        {
                                            "leagues": {
                                                "0": {
                                                    "league": [
                                                        {
                                                            "league_key": "999.l.123",
                                                            "league_id": "123",
                                                            "name": "Test League",
                                                            "season": "2026",
                                                        }
                                                    ]
                                                }
                                            }
                                        },
                                    ]
                                }
                            }
                        },
                    ]
                }
            }
        }
    }
    leagues = find_leagues(payload)
    assert len(leagues) == 1
    assert leagues[0].league_key == "999.l.123"
    assert leagues[0].name == "Test League"


def test_find_team_and_player_keys():
    payload = {
        "x": [
            {"team_key": "999.l.1.t.2"},
            {"nested": {"player_key": "999.p.42"}},
            {"team_key": "999.l.1.t.2"},
        ]
    }
    assert find_team_keys(payload) == ("999.l.1.t.2",)
    assert find_player_keys(payload) == ("999.p.42",)


def test_permission_error_has_actionable_diagnostic():
    error = YahooAPIError(
        status=401,
        body='oauth_problem="additional_authorization_required"',
        path="users;use_login=1/games",
        problem="additional_authorization_required",
    )
    message = provisioning_message(error)
    assert message is not None
    assert "Fantasy Sports" in message
