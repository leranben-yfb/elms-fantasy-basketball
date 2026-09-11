from __future__ import annotations

from abc import ABC, abstractmethod

from elms_fantasy.models import LeagueSnapshot


class FantasyProvider(ABC):
    """Boundary between the decision engine and a fantasy platform/data source."""

    @abstractmethod
    def get_snapshot(self) -> LeagueSnapshot:
        """Return a normalized league snapshot."""
        raise NotImplementedError
