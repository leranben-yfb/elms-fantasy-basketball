# ELMS Fantasy Basketball

ELMS Fantasy Basketball is a personal fantasy basketball analytics and decision-support system built to answer one question:

> What available move gives my team the highest probability of winning the league?

The architecture intentionally separates **data ingestion** from the **decision engine**. That means development can continue while Yahoo finishes provisioning the approved Fantasy Sports API application. Yahoo will become one provider; the engine itself does not depend on Yahoo-specific response formats.

## Current status

**v0.1 foundation is now runnable.**

Implemented:

- normalized league/player/roster models
- pluggable provider interface
- local JSON provider for development before Yahoo credentials arrive
- isolated Yahoo provider boundary ready for OAuth/API implementation
- category-aware waiver/free-agent ranking
- roster weakness weighting relative to opponents
- schedule/game-count boost
- basic injury penalty
- add/drop recommendation generation with reasons
- command-line interface
- sample league fixture
- smoke test

Yahoo integration is the next adapter to complete once the approved Client ID and Fantasy Sports permission are visible.

## Project structure

```text
src/elms_fantasy/
  models.py                 normalized domain models
  engine.py                 decision logic
  cli.py                    local command line interface
  providers/
    base.py                 provider contract
    json_file.py            development/test data source
    yahoo.py                Yahoo adapter boundary

data/
  sample_league.json        runnable sample snapshot
tests/
  test_engine.py            smoke test
```

## Quick start

Requires Python 3.11+.

```bash
git clone https://github.com/leranben-yfb/elms-fantasy-basketball.git
cd elms-fantasy-basketball
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
elms-fantasy data/sample_league.json
pytest
```

You can also run the CLI without installing the console script:

```powershell
$env:PYTHONPATH="src"
python -m elms_fantasy.cli data/sample_league.json
```

## Yahoo credentials

Copy `.env.example` to `.env` once Yahoo provides the approved developer application credentials:

```text
YAHOO_CLIENT_ID=
YAHOO_CLIENT_SECRET=
YAHOO_REDIRECT_URI=http://localhost:8765/callback
YAHOO_LEAGUE_KEY=
```

Do **not** commit real secrets.

## Decision-engine direction

The current ranking logic is intentionally a foundation, not the final model. The target system will evaluate moves using league-specific scoring and constraints, including:

- category strengths and weaknesses
- opponent matchup state
- roster and position eligibility
- games remaining and NBA schedule density
- back-to-backs and streaming windows
- injuries and expected return dates
- player trends and minutes/role changes
- rest and lineup news
- add limits and waiver rules
- replacement value
- category scarcity
- punt strategies
- trade impact
- playoff-week schedules
- historical league state

The engine should ultimately compare the **expected effect of a move on matchup and season win probability**, rather than simply ranking players in isolation.

## Yahoo Fantasy Sports API plan

Initial Yahoo integration will be read-only and will normalize these resources into the internal model:

- league settings and scoring categories
- teams and rosters
- player pool/free agents/waivers
- standings
- matchups
- transactions
- draft results

The Yahoo-specific code will stay behind `YahooFantasyProvider`, allowing the rest of the system to be tested without live API access.

## Development principles

1. Keep platform-specific API code isolated from decision logic.
2. Preserve raw source data where useful, but make recommendations from normalized models.
3. Every recommendation should explain *why* it was produced.
4. League rules and scoring settings are inputs, never hard-coded assumptions.
5. Test new decision logic against historical snapshots before trusting it live.
6. Read-only recommendations come before automated roster actions.
