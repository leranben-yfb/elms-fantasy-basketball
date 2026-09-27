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
- Yahoo-independent live draft board with manual pick tracking
- Draft recommendations that adapt to category needs, position-aware value over replacement, injuries, and roster construction
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

## Draft-day fallback (no Yahoo API required)

Yahoo is not on the critical path for draft day. Put the complete projected player pool in the snapshot's `free_agents` array, then use a local state file to track picks:

```bash
elms-fantasy draft-board data/draft_snapshot.json --limit 15
elms-fantasy draft-pick data/draft_snapshot.json "Nikola Jokic"
elms-fantasy draft-pick data/draft_snapshot.json "YOUR PLAYER" --mine
```

Every `draft-pick` immediately removes that player from the board. Picks marked `--mine` also change subsequent recommendations based on category needs and remaining roster-slot scarcity. State defaults to `data/draft_state.json`; use `--state` to keep separate mock drafts.

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

**v0.3 development — draft-day operation no longer depends on Yahoo. OAuth/read-only Yahoo integration remains ready for automatic sync once Yahoo provisions Fantasy Sports permission.**


## 2026-27 ELMS draft build

League model: 12 teams, snake draft, 9-category scoring, PG/SG/G/SF/PF/F/C/UTIL/UTIL plus 3 bench. The two IL slots are excluded from normal draft roster demand.

Build the consensus snapshot from the supplied FantasyPros average projections, LineupExperts workbook, FantasyPros Yahoo/ESPN ADP, and FantasyPros ECR:

```powershell
elms-fantasy draft-import "FantasyPros_NBA_Fantasy_Basketball_Overall_2026-27_Average_Projections.csv" "lineupexperts.com projections 26-27.xlsx" --adp "FantasyPros_2026_Overall_NBA_ADP_Rankings.csv" --ecr "FantasyPros_2026_Draft_ALL_Rankings.csv" --output data/draft_snapshot.json
```

Then run the board and record picks:

```powershell
elms-fantasy draft-board data/draft_snapshot.json --limit 20
elms-fantasy draft-pick data/draft_snapshot.json "Nikola Jokic"
elms-fantasy draft-pick data/draft_snapshot.json "Your Player" --mine
```

The consensus layer averages FantasyPros and LineupExperts counting-stat projections when both are available, derives shooting-attempt volume for attempt-weighted FG%/FT% impact, tracks projection disagreement as a confidence signal, and preserves Yahoo ADP/ECR as secondary draft-timing signals rather than substitutes for 9-cat value. The draft board also estimates position-aware replacement level from the 12-team, 12-normal-roster-slot player pool and blends absolute category strength with VORP.
