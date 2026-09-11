from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from elms_fantasy.yahoo_api import (
    get_league_draft_results,
    get_league_metadata,
    get_league_scoreboard,
    get_league_settings,
    get_league_standings,
    get_league_teams,
    get_league_transactions,
)


def collect_league_bundle(league_key: str) -> dict[str, Any]:
    """Collect the read-only league surfaces needed by the normalization layer."""
    return {
        "schema_version": 1,
        "league_key": league_key,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "metadata": get_league_metadata(league_key),
        "settings": get_league_settings(league_key),
        "teams": get_league_teams(league_key),
        "standings": get_league_standings(league_key),
        "scoreboard": get_league_scoreboard(league_key),
        "transactions": get_league_transactions(league_key),
        "draft_results": get_league_draft_results(league_key),
    }


def write_league_bundle(league_key: str, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = collect_league_bundle(league_key)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
