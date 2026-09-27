from __future__ import annotations

import argparse
import json
import webbrowser
from dataclasses import asdict

from elms_fantasy.draft import load_draft_state, rank_draft_board, record_pick, save_draft_state
from elms_fantasy.draft_import import build_consensus_snapshot
from elms_fantasy.engine import rank_free_agents, rank_streamers
from elms_fantasy.matchup import project_matchup
from elms_fantasy.providers.json_file import JsonFileProvider
from elms_fantasy.storage import HistoryStore
from elms_fantasy.yahoo_api import (
    YahooAPIError,
    get_basketball_leagues,
    get_league_draft_results,
    get_league_metadata,
    get_league_scoreboard,
    get_league_settings,
    get_league_standings,
    get_league_teams,
    get_league_transactions,
    provisioning_message,
)
from elms_fantasy.yahoo_export import write_league_bundle
from elms_fantasy.yahoo_oauth import (
    DEFAULT_TOKEN_PATH,
    build_authorization_url,
    exchange_code,
    extract_code,
    yahoo_credentials,
)
from elms_fantasy.yahoo_parser import compact_league_payload


def _add_yahoo_commands(sub) -> None:
    sub.add_parser("yahoo-auth", help="Authorize Yahoo and save OAuth tokens locally")
    sub.add_parser("yahoo-status", help="Check local Yahoo OAuth configuration without exposing secrets")

    p = sub.add_parser("yahoo-leagues", help="Fetch Yahoo Fantasy Basketball leagues for the signed-in user")
    p.add_argument("--raw", action="store_true", help="Print the complete Yahoo JSON response")

    p = sub.add_parser("yahoo-league", help="Fetch a read-only Yahoo league resource")
    p.add_argument("league_key")
    p.add_argument(
        "--section",
        choices=("metadata", "settings", "teams", "standings", "scoreboard", "transactions", "draftresults"),
        default="metadata",
    )

    p = sub.add_parser("yahoo-export", help="Export all available read-only Yahoo league surfaces to JSON")
    p.add_argument("league_key")
    p.add_argument("output", nargs="?", default="data/yahoo_league_export.json")


def _run_yahoo_auth() -> None:
    url, state = build_authorization_url()
    print("Opening Yahoo authorization in your browser...")
    print(url)
    webbrowser.open(url)
    print()
    print("After approving access, Yahoo will redirect to your callback URL.")
    print("If the browser shows a localhost connection error, that is okay.")
    print("Copy the FULL URL from the browser address bar and paste it below.")
    callback = input("Callback URL (or authorization code): ").strip()
    code = extract_code(callback, expected_state=state if "://" in callback else None)
    payload = exchange_code(code)
    print("Yahoo OAuth succeeded.")
    print("Access token received:", bool(payload.get("access_token")))
    print("Refresh token received:", bool(payload.get("refresh_token")))
    print("Tokens saved locally to .yahoo_tokens.json (gitignored).")


def _run_yahoo_status() -> None:
    try:
        client_id, client_secret, redirect_uri = yahoo_credentials()
        credentials_ok = bool(client_id and client_secret)
    except RuntimeError:
        credentials_ok = False
        redirect_uri = "(not configured)"
    print("Credentials configured:", credentials_ok)
    print("Redirect URI:", redirect_uri)
    print("Token file present:", DEFAULT_TOKEN_PATH.exists())
    print("Fantasy API permission: test with `elms-fantasy yahoo-leagues`")


def _league_section(league_key: str, section: str):
    functions = {
        "metadata": get_league_metadata,
        "settings": get_league_settings,
        "teams": get_league_teams,
        "standings": get_league_standings,
        "scoreboard": get_league_scoreboard,
        "transactions": get_league_transactions,
        "draftresults": get_league_draft_results,
    }
    return functions[section](league_key)


def _handle_yahoo_error(exc: YahooAPIError) -> None:
    message = provisioning_message(exc)
    if message:
        print("Yahoo Fantasy API permission is not active for this application.")
        print(message)
        raise SystemExit(2)
    raise exc


def main() -> None:
    parser = argparse.ArgumentParser(description="ELMS Fantasy Basketball decision engine")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("waivers", "streamers"):
        p = sub.add_parser(name)
        p.add_argument("snapshot")
        p.add_argument("--limit", type=int, default=10)
        p.add_argument("--save", action="store_true")

    p = sub.add_parser("matchup")
    p.add_argument("snapshot")
    p.add_argument("--opponent-id")

    p = sub.add_parser("draft-import", help="Build a consensus draft snapshot from projection files")
    p.add_argument("fantasypros")
    p.add_argument("lineup_experts")
    p.add_argument("--adp")
    p.add_argument("--ecr")
    p.add_argument("--output", default="data/draft_snapshot.json")

    p = sub.add_parser("draft-board", help="Show the live ELMS draft board")
    p.add_argument("snapshot")
    p.add_argument("--state", default="data/draft_state.json")
    p.add_argument("--limit", type=int, default=15)

    p = sub.add_parser("draft-pick", help="Record a draft pick and show the updated board")
    p.add_argument("snapshot")
    p.add_argument("player")
    p.add_argument("--mine", action="store_true")
    p.add_argument("--state", default="data/draft_state.json")
    p.add_argument("--limit", type=int, default=10)

    _add_yahoo_commands(sub)
    args = parser.parse_args()

    if args.command == "yahoo-auth":
        _run_yahoo_auth()
        return

    if args.command == "yahoo-status":
        _run_yahoo_status()
        return

    if args.command == "draft-import":
        path = build_consensus_snapshot(args.fantasypros, args.lineup_experts, args.output, adp=args.adp, ecr=args.ecr)
        print(f"Draft snapshot written to {path}")
        return

    if args.command in {"draft-board", "draft-pick"}:
        snapshot = JsonFileProvider(args.snapshot).get_snapshot()
        state = load_draft_state(args.state)
        if args.command == "draft-pick":
            try:
                player = record_pick(snapshot, state, args.player, mine=args.mine)
            except ValueError as exc:
                raise SystemExit(str(exc))
            save_draft_state(args.state, state)
            print(f"Recorded: {player.name}" + (" (MY TEAM)" if args.mine else ""))
        board = rank_draft_board(snapshot, drafted_ids=set(state.get("drafted", [])), my_roster_ids=set(state.get("mine", [])), limit=args.limit)
        print(f"Drafted: {len(state.get('drafted', []))} | Mine: {len(state.get('mine', []))}")
        for i, rec in enumerate(board, 1):
            adp_text = f" YahooADP={rec.yahoo_adp:.1f}" if rec.yahoo_adp is not None else ""
            conf = f" conf={rec.projection_confidence:.0%}" if rec.projection_confidence is not None else ""
            print(f"{i:>2}. {rec.name:<28} {'/'.join(rec.positions):<8} score={rec.score:+.2f}{adp_text}{conf}")
            print("    " + "; ".join(rec.reasons))
        return

    try:
        if args.command == "yahoo-leagues":
            payload = get_basketball_leagues()
            output = payload if args.raw else compact_league_payload(payload)
            print(json.dumps(output, indent=2))
            if not args.raw and not output:
                print("No Yahoo Fantasy Basketball leagues were found for this account.")
            return

        if args.command == "yahoo-league":
            print(json.dumps(_league_section(args.league_key, args.section), indent=2))
            return

        if args.command == "yahoo-export":
            path = write_league_bundle(args.league_key, args.output)
            print(f"Yahoo league export written to {path}")
            return
    except YahooAPIError as exc:
        _handle_yahoo_error(exc)

    snapshot = JsonFileProvider(args.snapshot).get_snapshot()

    if args.command in {"waivers", "streamers"}:
        recs = (
            rank_free_agents(snapshot, args.limit)
            if args.command == "waivers"
            else rank_streamers(snapshot, limit=args.limit)
        )
        for idx, rec in enumerate(recs, 1):
            move = f"ADD {rec.player_in}" + (f" / DROP {rec.player_out}" if rec.player_out else "")
            print(f"{idx}. {move} score={rec.score:.2f}")
            for reason in rec.reasons:
                print(f"   - {reason}")
        if args.save:
            store = HistoryStore()
            store.save_snapshot(snapshot)
            store.save_recommendations(snapshot, recs)
            store.close()
    else:
        opponent_id = args.opponent_id or snapshot.current_opponent_id
        opponent = next((t for t in snapshot.opponents if t.team_id == opponent_id), None)
        if opponent is None:
            raise SystemExit("Opponent not found; provide --opponent-id")
        projection = project_matchup(snapshot.my_team, opponent, snapshot.settings.categories)
        print(json.dumps(asdict(projection), indent=2))


if __name__ == "__main__":
    main()
