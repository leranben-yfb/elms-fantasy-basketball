from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from elms_fantasy.models import LeagueSnapshot, Player
from elms_fantasy.valuation import population_zscores


@dataclass(frozen=True)
class DraftRecommendation:
    player_id: str
    name: str
    positions: tuple[str, ...]
    score: float
    base_value: float
    scarcity_bonus: float
    need_bonus: float
    reasons: tuple[str, ...]


def _eligible(player: Player, slot: str) -> bool:
    slot = slot.upper()
    positions = {p.upper() for p in player.positions}
    if slot in {"UTIL", "BN", "BE"}:
        return True
    if slot == "G":
        return bool(positions & {"PG", "SG", "G"})
    if slot == "F":
        return bool(positions & {"SF", "PF", "F"})
    return slot in positions


def _open_slots(snapshot: LeagueSnapshot, roster: tuple[Player, ...]) -> tuple[str, ...]:
    slots = list(snapshot.settings.roster_slots)
    # Bench is intentionally filled last; assign each drafted player to the
    # most restrictive compatible active slot first.
    active = [s for s in slots if s.upper() not in {"BN", "BE"}]
    bench = [s for s in slots if s.upper() in {"BN", "BE"}]
    for player in roster:
        choices = [i for i, slot in enumerate(active) if _eligible(player, slot)]
        if choices:
            active.pop(choices[0])
        elif bench:
            bench.pop(0)
    return tuple(active + bench)


def rank_draft_board(
    snapshot: LeagueSnapshot,
    *,
    drafted_ids: set[str] | None = None,
    my_roster_ids: set[str] | None = None,
    limit: int = 15,
) -> tuple[DraftRecommendation, ...]:
    drafted_ids = drafted_ids or set()
    my_roster_ids = my_roster_ids or set()
    pool = tuple(p for p in snapshot.free_agents if p.player_id not in drafted_ids)
    if not pool:
        return ()

    categories = snapshot.settings.categories
    zs = population_zscores(tuple(snapshot.free_agents), categories)
    my_roster = tuple(p for p in snapshot.free_agents if p.player_id in my_roster_ids)
    open_slots = _open_slots(snapshot, my_roster)

    # Category need is relative to the drafted roster itself. Early in the draft
    # it stays neutral; later it rewards players who repair weak categories.
    need_weights = {c: 1.0 for c in categories}
    if len(my_roster) >= 2:
        for c in categories:
            values = [zs.get(p.player_id, {}).get(c, 0.0) for p in my_roster]
            avg = sum(values) / len(values) if values else 0.0
            need_weights[c] = max(0.75, min(1.35, 1.0 - avg * 0.12))

    # Scarcity is measured from remaining players who can fill each open slot.
    scarcity: dict[str, float] = {}
    for slot in set(open_slots):
        if slot.upper() in {"BN", "BE", "UTIL"}:
            continue
        count = sum(1 for p in pool if _eligible(p, slot))
        scarcity[slot] = 1.0 / max(count, 1)

    ranked: list[DraftRecommendation] = []
    for player in pool:
        pz = zs.get(player.player_id, {})
        base = sum(pz.get(c, 0.0) for c in categories)
        weighted = sum(pz.get(c, 0.0) * need_weights[c] for c in categories)
        need_bonus = weighted - base

        compatible = [s for s in open_slots if _eligible(player, s)]
        scarce = max((scarcity.get(s, 0.0) for s in compatible), default=0.0)
        scarcity_bonus = min(0.75, scarce * 8.0)

        injury = (player.injury_status or "").lower()
        injury_penalty = 0.0
        if injury:
            injury_penalty = 1.0 if any(x in injury for x in ("out", "injured", "susp")) else 0.35

        minutes_bonus = 0.0 if player.minutes is None else max(-0.25, min(0.25, (player.minutes - 30.0) / 24.0))
        score = weighted + scarcity_bonus + minutes_bonus - injury_penalty

        reasons = [f"category value {base:+.2f}"]
        if abs(need_bonus) >= 0.05:
            reasons.append(f"team-needs adjustment {need_bonus:+.2f}")
        if scarcity_bonus >= 0.05:
            reasons.append(f"position scarcity +{scarcity_bonus:.2f}")
        if injury_penalty:
            reasons.append(f"injury/status penalty -{injury_penalty:.2f}")
        ranked.append(DraftRecommendation(
            player.player_id, player.name, player.positions, score, base,
            scarcity_bonus, need_bonus, tuple(reasons)
        ))

    ranked.sort(key=lambda r: (r.score, r.base_value), reverse=True)
    return tuple(ranked[:max(1, limit)])


def load_draft_state(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"drafted": [], "mine": []}
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {"drafted": list(raw.get("drafted", [])), "mine": list(raw.get("mine", []))}


def save_draft_state(path: str | Path, state: dict) -> None:
    Path(path).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def record_pick(snapshot: LeagueSnapshot, state: dict, query: str, mine: bool = False) -> Player:
    q = query.strip().lower()
    players = snapshot.free_agents
    exact = [p for p in players if p.player_id.lower() == q or p.name.lower() == q]
    matches = exact or [p for p in players if q in p.name.lower()]
    if len(matches) != 1:
        names = ", ".join(p.name for p in matches[:8])
        raise ValueError(f"Pick must match exactly one player; matches: {names or 'none'}")
    player = matches[0]
    drafted = state.setdefault("drafted", [])
    if player.player_id in drafted:
        raise ValueError(f"{player.name} is already drafted")
    drafted.append(player.player_id)
    if mine:
        state.setdefault("mine", []).append(player.player_id)
    return player
