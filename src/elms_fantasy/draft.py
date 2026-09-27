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
    yahoo_adp: float | None = None
    consensus_adp: float | None = None
    ecr: float | None = None
    projection_confidence: float | None = None
    market_value: float = 0.0
    replacement_level: float | None = None
    vorp: float | None = None


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
    slots = [s for s in snapshot.settings.roster_slots if s.upper() not in {"IL", "IR", "IR+"}]
    if not roster:
        return tuple(slots)

    # Maximum bipartite matching avoids the greedy-slot bug where an early
    # multi-position player can consume a slot required by a later specialist.
    # Restrictive slots are visited first; UTIL/bench are preserved when possible.
    priority = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0, "G": 1, "F": 1, "UTIL": 2, "BN": 3, "BE": 3}
    order = sorted(range(len(slots)), key=lambda i: (priority.get(slots[i].upper(), 2), i))
    match: dict[int, int] = {}

    player_order = sorted(
        range(len(roster)),
        key=lambda pi: sum(1 for si in order if _eligible(roster[pi], slots[si])),
    )

    def assign(player_idx: int, seen: set[int]) -> bool:
        for slot_idx in order:
            if slot_idx in seen or not _eligible(roster[player_idx], slots[slot_idx]):
                continue
            seen.add(slot_idx)
            previous = match.get(slot_idx)
            if previous is None or assign(previous, seen):
                match[slot_idx] = player_idx
                return True
        return False

    for player_idx in player_order:
        assign(player_idx, set())

    occupied = set(match)
    return tuple(slot for i, slot in enumerate(slots) if i not in occupied)


def _normal_roster_size(snapshot: LeagueSnapshot) -> int:
    return sum(1 for s in snapshot.settings.roster_slots if s.upper() not in {"IL", "IR", "IR+"})


def _replacement_levels(
    snapshot: LeagueSnapshot,
    pool: tuple[Player, ...],
    values: dict[str, float],
    drafted_count: int,
    *,
    league_teams: int = 12,
) -> dict[str, float]:
    """Estimate best freely replaceable value after a normal 12-team draft.

    Players inside the remaining expected drafted pool are treated as rostered.
    The strongest eligible player outside that pool is the replacement baseline
    for each slot. This makes replacement level respond to actual positional
    depth instead of using one global player-144 cutoff.
    """
    remaining_draft_slots = max(0, _normal_roster_size(snapshot) * league_teams - drafted_count)
    ordered = sorted(pool, key=lambda p: values.get(p.player_id, float("-inf")), reverse=True)
    replacement_pool = ordered[remaining_draft_slots:] if remaining_draft_slots < len(ordered) else ordered[-1:]
    slots = {s.upper() for s in snapshot.settings.roster_slots if s.upper() not in {"IL", "IR", "IR+"}}

    levels: dict[str, float] = {}
    for slot in slots:
        eligible = [values[p.player_id] for p in replacement_pool if _eligible(p, slot)]
        if eligible:
            levels[slot] = max(eligible)
        else:
            all_eligible = [values[p.player_id] for p in ordered if _eligible(p, slot)]
            levels[slot] = min(all_eligible) if all_eligible else 0.0
    return levels


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

    # Build adjusted intrinsic values first so replacement level uses the same
    # category, availability, minutes, and injury assumptions as the live board.
    adjusted_values: dict[str, float] = {}
    for candidate in pool:
        cpz = zs.get(candidate.player_id, {})
        cneeds = sum(cpz.get(c, 0.0) * need_weights[c] for c in categories)
        cgp = float(candidate.stats.get("_CONSENSUS_GP", 76.0))
        cavailability = max(0.72, min(1.03, cgp / 76.0))
        cinjury = (candidate.injury_status or "").lower()
        cinjury_penalty = 0.0
        if cinjury:
            if any(x in cinjury for x in ("out", "injured", "susp", "ir")):
                cinjury_penalty = 2.25
            elif any(x in cinjury for x in ("dtd", "gtd", "question", " q")):
                cinjury_penalty = 0.55
            else:
                cinjury_penalty = 0.35
        cminutes = 0.0 if candidate.minutes is None else max(-0.25, min(0.25, (candidate.minutes - 30.0) / 24.0))
        adjusted_values[candidate.player_id] = cneeds * cavailability + cminutes - cinjury_penalty

    replacement_levels = _replacement_levels(
        snapshot, pool, adjusted_values, len(drafted_ids)
    )

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
        # Availability matters in season-long roto/H2H value. Use projected
        # games as a modest reliability adjustment, not a linear totals boost.
        projected_gp = float(player.stats.get("_CONSENSUS_GP", 76.0))
        availability = max(0.72, min(1.03, projected_gp / 76.0))
        base = sum(pz.get(c, 0.0) for c in categories)
        needs_value = sum(pz.get(c, 0.0) * need_weights[c] for c in categories)
        need_bonus = needs_value - base
        availability_adjustment = needs_value * (availability - 1.0)
        weighted = needs_value * availability

        compatible = [s for s in open_slots if _eligible(player, s)]
        scarce = max((scarcity.get(s, 0.0) for s in compatible), default=0.0)
        scarcity_bonus = min(0.75, scarce * 8.0)

        injury = (player.injury_status or "").lower()
        injury_penalty = 0.0
        if injury:
            if any(x in injury for x in ("out", "injured", "susp", "ir")):
                injury_penalty = 2.25
            elif any(x in injury for x in ("dtd", "gtd", "question", " q")):
                injury_penalty = 0.55
            else:
                injury_penalty = 0.35

        minutes_bonus = 0.0 if player.minutes is None else max(-0.25, min(0.25, (player.minutes - 30.0) / 24.0))
        yahoo_adp = player.stats.get("_YAHOO_ADP")
        consensus_adp = player.stats.get("_CONSENSUS_ADP")
        ecr = player.stats.get("_ECR")
        disagreement = float(player.stats.get("_PROJ_DISAGREEMENT", 0.0))
        projection_confidence = max(0.0, min(1.0, 1.0 - disagreement))
        market_value = 0.0
        # ADP is market timing information, not player quality. Until the
        # exact snake slot is known it should not move the intrinsic board.
        # It remains exposed on each recommendation for later turn-survival logic.
        if yahoo_adp is not None:
            market_value = 0.0
        adjusted_value = weighted + minutes_bonus - injury_penalty + market_value
        compatible_replacement_slots = [
            s.upper() for s in open_slots
            if s.upper() not in {"BN", "BE"} and _eligible(player, s)
        ]
        if not compatible_replacement_slots:
            compatible_replacement_slots = ["UTIL"] if "UTIL" in replacement_levels else []
        replacement_level = min(
            (replacement_levels[s] for s in compatible_replacement_slots if s in replacement_levels),
            default=replacement_levels.get("UTIL", 0.0),
        )
        vorp = adjusted_value - replacement_level

        # Blend absolute category strength with position-aware value over
        # replacement. This prevents weak specialists from outranking true stars
        # while still rewarding scarce positions in a 12-team/144-player pool.
        score = adjusted_value * 0.65 + vorp * 0.35 + scarcity_bonus

        reasons = [f"category value {base:+.2f}", f"VORP {vorp:+.2f} (replacement {replacement_level:+.2f})"]
        if abs(need_bonus) >= 0.05:
            reasons.append(f"team-needs adjustment {need_bonus:+.2f}")
        if scarcity_bonus >= 0.05:
            reasons.append(f"position scarcity +{scarcity_bonus:.2f}")
        if abs(availability - 1.0) >= 0.03:
            reasons.append(f"availability {projected_gp:.0f} GP ({availability_adjustment:+.2f})")
        if injury_penalty:
            reasons.append(f"injury/status penalty -{injury_penalty:.2f}")
        if yahoo_adp is not None:
            reasons.append(f"Yahoo ADP {float(yahoo_adp):.1f}")
        if disagreement >= 0.12:
            reasons.append(f"projection disagreement {disagreement:.0%}")
        ranked.append(DraftRecommendation(
            player.player_id, player.name, player.positions, score, base,
            scarcity_bonus, need_bonus, tuple(reasons),
            float(yahoo_adp) if yahoo_adp is not None else None,
            float(consensus_adp) if consensus_adp is not None else None,
            float(ecr) if ecr is not None else None,
            projection_confidence, market_value,
            replacement_level, vorp
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
