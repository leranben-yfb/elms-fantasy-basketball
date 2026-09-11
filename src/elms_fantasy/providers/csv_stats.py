from __future__ import annotations

import csv
from pathlib import Path

from elms_fantasy.models import Player

IDENTITY = {"player_id", "name", "team", "positions", "games_remaining", "injury_status", "minutes", "usage_rate", "roster_pct"}


def load_players_csv(path: str | Path) -> tuple[Player, ...]:
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    players = []
    for i, row in enumerate(rows):
        stats = {}
        for k, v in row.items():
            if k in IDENTITY or v in (None, ""):
                continue
            try:
                stats[k] = float(v)
            except ValueError:
                pass
        players.append(Player(player_id=str(row.get("player_id") or i), name=row.get("name") or "Unknown", positions=tuple(x.strip() for x in (row.get("positions") or "").split(",") if x.strip()), team=row.get("team") or "", games_remaining=int(float(row.get("games_remaining") or 0)), injury_status=row.get("injury_status") or None, stats=stats, minutes=float(row["minutes"]) if row.get("minutes") else None, usage_rate=float(row["usage_rate"]) if row.get("usage_rate") else None, roster_pct=float(row["roster_pct"]) if row.get("roster_pct") else None))
    return tuple(players)
