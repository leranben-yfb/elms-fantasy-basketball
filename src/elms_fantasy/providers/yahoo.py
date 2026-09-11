from __future__ import annotations

import os

from elms_fantasy.models import LeagueSnapshot
from elms_fantasy.providers.base import FantasyProvider


class YahooFantasyProvider(FantasyProvider):
    """Yahoo adapter boundary.

    OAuth/network implementation will be enabled once Yahoo provisions the
    approved application's Client ID and Fantasy Sports permission.
    """

    def __init__(self) -> None:
        self.client_id = os.getenv("YAHOO_CLIENT_ID", "")
        self.client_secret = os.getenv("YAHOO_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("YAHOO_REDIRECT_URI", "http://localhost:8765/callback")
        self.league_key = os.getenv("YAHOO_LEAGUE_KEY", "")

    def get_snapshot(self) -> LeagueSnapshot:
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Yahoo credentials are not configured yet. Use the JSON provider "
                "until Yahoo provisions the approved developer app."
            )
        raise NotImplementedError(
            "Yahoo OAuth/API ingestion is intentionally isolated here and will be "
            "implemented as soon as the approved Client ID is available."
        )
