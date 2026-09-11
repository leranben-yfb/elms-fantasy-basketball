from __future__ import annotations

import argparse

from elms_fantasy.engine import rank_free_agents
from elms_fantasy.providers.json_file import JsonFileProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="ELMS Fantasy Basketball decision engine")
    parser.add_argument("snapshot", help="Path to a normalized league snapshot JSON file")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    snapshot = JsonFileProvider(args.snapshot).get_snapshot()
    recommendations = rank_free_agents(snapshot, limit=args.limit)

    print(f"League: {snapshot.settings.name}")
    print(f"Team: {snapshot.my_team.name}\n")
    for idx, rec in enumerate(recommendations, 1):
        move = f"ADD {rec.player_in}"
        if rec.player_out:
            move += f" / DROP {rec.player_out}"
        print(f"{idx}. {move}  score={rec.score:.2f}")
        for reason in rec.reasons:
            print(f"   - {reason}")


if __name__ == "__main__":
    main()
