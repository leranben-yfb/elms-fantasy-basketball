# ELMS Fantasy Basketball

ELMS Fantasy Basketball is a fantasy basketball analytics and decision-support engine designed around one question:

> What available move gives my team the highest probability of winning the league?

The project is provider-agnostic. Yahoo Fantasy is the primary league source, while the decision engine also runs against normalized JSON/CSV inputs so development does not stop on external API provisioning.

## Current capabilities

- Normalized league/team/player domain model
- Category-aware player valuation and population z-scores
- Team-needs/category weighting
- Lower-is-better turnover handling
- Attempt-weighted FG% and FT% aggregation when makes/attempts are available
- Schedule, injury and minutes adjustments
- Waiver-wire add/drop ranking
- Matchup-aware streaming recommendations
- Per-category and overall matchup projections
- Trade impact analysis
- Best-roster / best-single-swap optimization helpers
- Generic CSV and JSON ingestion
- SQLite history for snapshots and recommendations
- Yahoo OAuth authorization with local token storage
- Yahoo access-token refresh support
- Yahoo league discovery and read-only league resource clients
- Yahoo league export bundle for normalization development
- Actionable handling of Yahoo Fantasy API provisioning errors
- Automated pytest coverage and GitHub Actions CI

## Architecture

The core engine does not know where league data came from. Providers normalize source data into `LeagueSnapshot`; valuation, matchup and decision layers then operate on that model.

See `docs/ARCHITECTURE.md` and `docs/YAHOO_INTEGRATION.md`.

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

## Core CLI

```bash
elms-fantasy waivers data/example_snapshot.json --limit 10
elms-fantasy streamers data/example_snapshot.json --limit 10
elms-fantasy matchup data/example_snapshot.json
elms-fantasy waivers data/example_snapshot.json --save
```

## Yahoo CLI

```bash
elms-fantasy yahoo-status
elms-fantasy yahoo-auth
elms-fantasy yahoo-leagues
elms-fantasy yahoo-league LEAGUE_KEY --section settings
elms-fantasy yahoo-export LEAGUE_KEY data/yahoo_league_export.json
```

The OAuth token file `.yahoo_tokens.json`, `.env`, and SQLite databases are ignored by git.

### Current Yahoo blocker

Yahoo OAuth is operational: authorization succeeds and Yahoo issues both access and refresh tokens. The Fantasy Sports endpoint currently returns `401 additional_authorization_required`. This indicates that the developer application still needs its approved Fantasy Sports API permission associated with the Client ID.

The CLI now detects that condition and explains the required provisioning step instead of dumping a traceback. Once Yahoo attaches the permission, re-run `yahoo-auth` and then `yahoo-leagues`.

The actual production basketball league does not need to exist yet. When it is created, the same authorized Yahoo account should join it, after which the league key can be discovered and the raw league surfaces exported for normalization.

## Percentage categories

Roster FG% and FT% are now aggregated from makes/attempts (`FGM/FGA`, `FTM/FTA`) when those fields are present. This fixes the previous behavior of summing player percentages. If a projection feed supplies only percentage values, the model falls back to an equal-weight mean until attempt data is available.

## What still depends on live data or league-specific rules

- Yahoo provisioning of Fantasy Sports permission
- one real Yahoo basketball league payload to validate normalization
- live NBA statistics/projections feed
- live injury/news feed
- NBA schedule and playoff-week optimization
- exact Yahoo roster-slot legality and daily lineup optimization
- waiver/transaction timing rules from the actual league
- historical backtesting against real decisions
- richer probability simulations calibrated from historical player variance

## Status

**v0.3 development — OAuth and read-only Yahoo integration layer operational; waiting on Yahoo Fantasy Sports permission and a real league payload for full normalization.**
