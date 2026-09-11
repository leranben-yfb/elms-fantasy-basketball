# Yahoo Fantasy integration

## Current state

The application can complete Yahoo OAuth and safely persist access/refresh tokens in
`.yahoo_tokens.json` (gitignored). The live Fantasy Sports endpoint currently returns
`401 additional_authorization_required`, which means Yahoo authentication succeeded
but the application still needs Fantasy Sports API permission provisioned on its
Client ID.

The code treats this as a provisioning condition and prints an actionable message
rather than a Python traceback.

## Security rules

Never commit or paste into chat:

- `.env`
- Yahoo Client Secret
- `.yahoo_tokens.json`
- access tokens
- refresh tokens
- callback URLs containing authorization codes

## Commands

Check local setup without showing secrets:

```powershell
elms-fantasy yahoo-status
```

Authorize/re-authorize:

```powershell
elms-fantasy yahoo-auth
```

Discover basketball leagues:

```powershell
elms-fantasy yahoo-leagues
```

Print the raw discovery response only when debugging locally:

```powershell
elms-fantasy yahoo-leagues --raw
```

Once a league exists, query individual read-only resources:

```powershell
elms-fantasy yahoo-league LEAGUE_KEY --section settings
elms-fantasy yahoo-league LEAGUE_KEY --section teams
elms-fantasy yahoo-league LEAGUE_KEY --section standings
elms-fantasy yahoo-league LEAGUE_KEY --section scoreboard
elms-fantasy yahoo-league LEAGUE_KEY --section transactions
elms-fantasy yahoo-league LEAGUE_KEY --section draftresults
```

Export the surfaces needed to build and validate the normalization layer:

```powershell
elms-fantasy yahoo-export LEAGUE_KEY data/yahoo_league_export.json
```

The export is intended for local development and can contain league/user data. Review
it before sharing or committing it.

## Provisioning recovery

If `yahoo-leagues` reports `additional_authorization_required`, Yahoo must associate
the approved Fantasy Sports API permission with the application's Client ID. After
Yahoo confirms the permission is attached, run `yahoo-auth` again so a fresh token is
issued under the updated application permissions, then retry `yahoo-leagues`.

## Integration plan after the real league exists

1. Discover the league key.
2. Export metadata, settings, teams, standings, scoreboard, transactions, and draft results.
3. Validate Yahoo's real JSON shape using fixture copies with private data removed.
4. Normalize settings, teams, rosters, players, matchup, and free agents into `LeagueSnapshot`.
5. Add pagination for player/free-agent pools.
6. Persist snapshots and feed them into waiver, streaming, matchup, trade, and lineup engines.
7. Keep all Yahoo operations read-only until analysis quality is validated.
