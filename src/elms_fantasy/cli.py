from __future__ import annotations

import argparse
import json
import webbrowser
from dataclasses import asdict

from elms_fantasy.engine import rank_free_agents, rank_streamers
from elms_fantasy.matchup import project_matchup
from elms_fantasy.providers.json_file import JsonFileProvider
from elms_fantasy.storage import HistoryStore
from elms_fantasy.yahoo_oauth import build_authorization_url, exchange_code, extract_code


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

    sub.add_parser("yahoo-auth", help="Authorize Yahoo and save OAuth tokens locally")

    args = parser.parse_args()

    if args.command == "yahoo-auth":
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
        return

    snapshot = JsonFileProvider(args.snapshot).get_snapshot()

    if args.command in {"waivers", "streamers"}:
        recs = rank_free_agents(snapshot, args.limit) if args.command == "waivers" else rank_streamers(snapshot, limit=args.limit)
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
