# Architecture

The system is intentionally split into normalized fantasy-domain logic and provider adapters.

## Core flow

1. A provider produces a `LeagueSnapshot`.
2. The valuation layer computes category-aware player values and team needs.
3. The matchup layer estimates category and matchup win probabilities.
4. The decision engine ranks waiver and streaming moves by incremental value.
5. Trade and roster optimizers evaluate alternative roster states.
6. Optional SQLite persistence records snapshots and recommendations for later backtesting.

## Provider boundary

`JsonFileProvider` is the working local/offline provider. `YahooFantasyProvider` remains isolated behind the same provider interface while Yahoo finishes application provisioning. Additional NBA/stat/schedule/injury sources can be normalized into the same `Player` model without changing decision logic.

## Current decision modules

- `valuation.py`: category weights, z-scores, schedule/injury/minutes adjustments, replacement level.
- `matchup.py`: category and overall matchup probabilities.
- `engine.py`: waiver-wire and matchup-aware streamer rankings.
- `trades.py`: trade impact evaluation.
- `optimizer.py`: roster-value optimization and best single swap.
- `storage.py`: SQLite history for snapshots and recommendations.
- `providers/csv_stats.py`: generic CSV stat ingestion.
- `providers/json_file.py`: normalized league snapshot ingestion.
- `providers/yahoo.py`: Yahoo adapter boundary awaiting credentials/provisioning.

## Deliberate limitations before live Yahoo/NBA feeds

The math is operational but the quality of recommendations depends on the quality and time horizon of the supplied projections. Percentages are currently treated as normalized category values; a later iteration should use attempt-weighted FG%/FT% inputs when raw made/attempted data is available. Positional slot legality, transaction timing, playoff schedule optimization, and live injury/news ingestion are designed as subsequent provider/constraint layers rather than hard-coded into the core model.
