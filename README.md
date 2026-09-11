# ELMS Fantasy Basketball

ELMS Fantasy Basketball is a fantasy basketball analytics and decision-support engine designed around one question:

> What available move gives my team the highest probability of winning the league?

The project is deliberately provider-agnostic. Yahoo Fantasy will be the primary league source once API provisioning is complete, but the decision engine already runs against normalized JSON/CSV inputs so development does not depend on Yahoo authentication.

## Current capabilities

- Normalized league/team/player domain model
- Category-aware player valuation
- Population z-scores
- Team-needs/category weighting
- Lower-is-better turnover handling
- Schedule, injury and minutes adjustments
- Waiver-wire add/drop ranking
- Matchup-aware streaming recommendations
- Per-category matchup projections
- Overall matchup win-probability estimate
- Trade impact analysis
- Best-roster / best-single-swap optimization helpers
- Generic CSV player-stat ingestion
- JSON league snapshot ingestion
- SQLite history for league snapshots and recommendations
- Yahoo provider boundary ready for OAuth/API implementation
- Automated pytest coverage and GitHub Actions CI

## Architecture

The core engine does not know where league data came from. Providers normalize source data into `LeagueSnapshot`; the valuation, matchup and decision layers then operate on that model.

See `docs/ARCHITECTURE.md` for details.

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .[dev]
```

## Run tests

```bash
pytest -q
```

## CLI

Rank waiver moves:

```bash
elms-fantasy waivers data/example_snapshot.json --limit 10
```

Rank matchup-aware streamers:

```bash
elms-fantasy streamers data/example_snapshot.json --limit 10
```

Project the active matchup:

```bash
elms-fantasy matchup data/example_snapshot.json
```

Persist a snapshot and the resulting recommendations to SQLite:

```bash
elms-fantasy waivers data/example_snapshot.json --save
```

The local database is written to `data/elms_fantasy.db` and is ignored by git.

## Normalized player fields

A player can currently carry:

- player ID / name / NBA team
- eligible positions
- games remaining in evaluation window
- injury status
- projected category statistics
- minutes
- usage rate
- roster percentage
- projected game dates

This lets the engine work with manually supplied data, exported projections, or future live providers without rewriting the decision logic.

## Yahoo Fantasy integration

`src/elms_fantasy/providers/yahoo.py` is intentionally isolated. Yahoo access is approved but the developer application still needs to be correctly provisioned/associated with the Yahoo developer account before live OAuth ingestion can be completed.

Once Yahoo provides the Client ID/secret and Fantasy Sports permission, the adapter will populate the same normalized snapshot with:

- league settings and scoring categories
- teams and rosters
- standings and current matchup
- free agents / waivers
- transactions
- draft results

No redesign of the decision engine should be necessary.

## What still depends on live data or league-specific rules

The repository now contains the major Yahoo-independent engine pieces. The remaining high-value work needs real source data or actual league configuration, especially:

- Yahoo OAuth and live league ingestion
- live NBA statistics/projections feed
- live injury/news feed
- NBA schedule and playoff-week schedule optimization
- exact roster-slot legality and daily lineup optimization
- transaction/waiver timing rules
- attempt-weighted FG% and FT% modeling using makes/attempts
- historical backtesting against real league decisions
- richer simulations calibrated from historical player variance

## Status

**v0.2.0 — standalone decision-engine foundation operational.**

The next integration milestone is live Yahoo league ingestion when provisioning is complete; until then, the engine can be exercised with normalized JSON/CSV data.
