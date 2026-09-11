from pathlib import Path

from elms_fantasy.engine import rank_free_agents
from elms_fantasy.providers.json_file import JsonFileProvider


def test_sample_snapshot_generates_ranked_moves():
    path = Path("data/sample_league.json")
    snapshot = JsonFileProvider(path).get_snapshot()
    recommendations = rank_free_agents(snapshot)

    assert recommendations
    assert recommendations[0].player_in is not None
    assert recommendations[0].action in {"ADD", "ADD_DROP"}
    assert recommendations == sorted(recommendations, key=lambda r: r.score, reverse=True)
