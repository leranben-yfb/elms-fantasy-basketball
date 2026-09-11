from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from elms_fantasy.models import LeagueSnapshot, Recommendation


class HistoryStore:
    def __init__(self, path: str | Path = "data/elms_fantasy.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, captured_at TEXT NOT NULL, league_id TEXT NOT NULL, payload TEXT NOT NULL)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS recommendations (id INTEGER PRIMARY KEY, captured_at TEXT NOT NULL, league_id TEXT NOT NULL, action TEXT NOT NULL, score REAL NOT NULL, payload TEXT NOT NULL)")
        self.conn.commit()

    def save_snapshot(self, snapshot: LeagueSnapshot) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute("INSERT INTO snapshots(captured_at, league_id, payload) VALUES (?, ?, ?)", (now, snapshot.settings.league_id, json.dumps(asdict(snapshot))))
        self.conn.commit()
        return int(cur.lastrowid)

    def save_recommendations(self, snapshot: LeagueSnapshot, recs: list[Recommendation]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        for rec in recs:
            self.conn.execute("INSERT INTO recommendations(captured_at, league_id, action, score, payload) VALUES (?, ?, ?, ?, ?)", (now, snapshot.settings.league_id, rec.action, rec.score, json.dumps(asdict(rec))))
        self.conn.commit()
        return len(recs)

    def close(self) -> None:
        self.conn.close()
