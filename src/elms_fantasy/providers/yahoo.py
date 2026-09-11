from __future__ import annotations

import os
from typing import Any

from elms_fantasy.models import LeagueSnapshot
from elms_fantasy.providers.base import FantasyProvider
from elms_fantasy.yahoo_api import (
    get_basketball_leagues,
    get_league_draft_results,
    get_league_metadata,
    get_league_scoreboard,
    get_league_settings,
    get_league_standings,
    get_league_teams,
    get_league_transactions,
)
from elms_fantasy.yahoo_oauth import load_env_file
from elms_fantasy.yahoo_parser import find_leagues


class YahooFantasyProvider(FantasyProvider):
    """Read-only Yahoo adapter.

    Raw league ingestion is operational. Full normalization into LeagueSnapshot
    is intentionally gated on real Yahoo league payloads so the parser can be
    validated against the user's actual league configuration rather than guessed.
    """

    def __init__(self, league_key: str | None = None) -> None:
        load_env_file()
        self.league_key = league_key or os.getenv("YAHOO_LEAGUE_KEY", "").strip()

    def discover_leagues(self):
        return find_leagues(get_basketball_leagues())

    def get_raw_league(self, league_key: str | None = None) -> dict[str, Any]:
        key = league_key or self.league_key
        if not key:
            raise RuntimeError(
                "No Yahoo league key configured. Run elms-fantasy yahoo-leagues "
                "after Yahoo Fantasy API permission is provisioned."
            )
        return {
            "metadata": get_league_metadata(key),
            "settings": get_league_settings(key),
            "teams": get_league_teams(key),
            "standings": get_league_standings(key),
            "scoreboard": get_league_scoreboard(key),
            "transactions": get_league_transactions(key),
            "draft_results": get_league_draft_results(key),
        }

    def get_snapshot(self) -> LeagueSnapshot:
        raise RuntimeError(
            "Yahoo raw ingestion is ready, but LeagueSnapshot normalization needs "
            "one real Yahoo basketball league payload. Use yahoo-export once the "
            "league exists; the engine remains usable with JSON snapshots meanwhile."
        )
