#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "rich>=13.0",
# ]
# ///
"""parlayapi-arb-scanner: find sportsbook arbitrage with the ParlayAPI odds API.

Zero-setup by default: runs against ParlayAPI's keyless sandbox endpoints.
Set the PARLAY_API_KEY environment variable to scan live odds instead.

Usage:
    uv run arb_scanner.py                       # sandbox NBA, server-side arb feed
    uv run arb_scanner.py --list-sports         # what can I scan?
    uv run arb_scanner.py icehockey_nhl         # another sport
    uv run arb_scanner.py --source odds         # compute arbs locally from raw odds
    uv run arb_scanner.py --bankroll 500        # stake split for a $500 bankroll
    PARLAY_API_KEY=pk_... uv run arb_scanner.py # live data (free tier works)

Built by the ParlayAPI team. Docs: https://parlay-api.com/docs
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from rich import box
from rich.console import Console
from rich.table import Table

API_KEY = os.environ.get("PARLAY_API_KEY", "").strip()
LIVE = bool(API_KEY)
BASE = "https://parlay-api.com/v1" if LIVE else "https://parlay-api.com/v1/sandbox"

console = Console()


def get(path, params=None):
    """GET a ParlayAPI endpoint, return parsed JSON."""
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={"User-Agent": "parlayapi-arb-scanner/1.0"})
    if LIVE:
        req.add_header("X-API-Key", API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        console.print(f"[red]HTTP {e.code} from {url}[/red]\n{body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        console.print(f"[red]Network error reaching {url}: {e.reason}[/red]")
        sys.exit(1)


def american_to_decimal(a):
    """Convert American odds (+115 / -110) to decimal odds (2.15 / 1.909)."""
    a = float(a)
    if a > 0:
        return 1.0 + a / 100.0
    return 1.0 + 100.0 / abs(a)


def fmt_american(a):
    a = int(round(float(a)))
    return f"+{a}" if a > 0 else str(a)


def stake_split(decimals, bankroll):
    """Split a bankroll across outcomes so every result pays the same.

    Returns (stakes, guaranteed_profit). Only meaningful when
    sum(1/d for d in decimals) < 1 (a true arbitrage).
    """
    inv = sum(1.0 / d for d in decimals)
    stakes = [bankroll * (1.0 / d) / inv for d in decimals]
    payout = bankroll / inv
    return stakes, payout - bankroll


def mode_banner():
    if LIVE:
        console.print(f"[bold green]LIVE[/bold green] mode: {BASE} (key from PARLAY_API_KEY)")
    else:
        console.print(
            f"[bold yellow]SANDBOX[/bold yellow] mode: {BASE} (synthetic data, no key needed). "
            "Set PARLAY_API_KEY for live odds."
        )


def cmd_list_sports():
    sports = get("/sports")
    table = Table(title="Sports", box=box.ASCII)
    table.add_column("key", style="cyan")
    table.add_column("group")
    table.add_column("title")
    for s in sports:
        table.add_row(s["key"], s.get("group", ""), s.get("title", ""))
    console.print(table)


def cmd_scan_api(sport, min_profit, bankroll, limit, as_json):
    """Server-side scan: ParlayAPI's /sports/{key}/arbitrage endpoint."""
    params = {}
    if LIVE:
        params = {"minProfit": min_profit, "limit": max(limit * 5, 100)}
    data = get(f"/sports/{sport}/arbitrage", params)
    arbs = [a for a in data.get("arbs", []) if a.get("profit_pct", 0) >= min_profit]
    if as_json:
        print(json.dumps(arbs, indent=2))
        return
    arbs.sort(key=lambda a: a.get("profit_pct", 0), reverse=True)
    arbs = arbs[:limit]
    if not arbs:
        console.print(f"No arbs at or above {min_profit}% profit right now for {sport}.")
        console.print("That is normal. Real arbitrage is rare and disappears in minutes.")
        return
    table = Table(title=f"Arbitrage: {sport} ({data.get('count', len(arbs))} found)", box=box.ASCII)
    table.add_column("Matchup")
    table.add_column("Market")
    table.add_column("Side A", style="cyan")
    table.add_column("Side B", style="magenta")
    table.add_column("Profit %", justify="right", style="green")
    table.add_column(f"Stakes (${bankroll:g})", justify="right")
    for a in arbs:
        sa, sb = a["side_a"], a["side_b"]
        d1, d2 = american_to_decimal(sa["odds"]), american_to_decimal(sb["odds"])
        stakes, _ = stake_split([d1, d2], bankroll)
        matchup = f"{a.get('away_team', '?')} @ {a.get('home_team', '?')}"
        market = a.get("market", a.get("market_key", ""))
        if a.get("player"):
            market += f" {a['player']}"
        if a.get("line") is not None:
            market += f" {a['line']}"
        table.add_row(
            matchup,
            market,
            f"{sa['bet']} {fmt_american(sa['odds'])} @ {sa['bookmaker']}",
            f"{sb['bet']} {fmt_american(sb['odds'])} @ {sb['bookmaker']}",
            f"{a.get('profit_pct', 0):.2f}",
            f"{stakes[0]:.2f} / {stakes[1]:.2f}",
        )
    console.print(table)
    if data.get("note"):
        console.print(f"[dim]{data['note']}[/dim]")


def cmd_scan_odds(sport, min_profit, bankroll, limit, as_json):
    """Local scan: pull raw odds from /sports/{key}/odds and do the math here.

    For each event, take the best available price on every outcome across all
    bookmakers. If the implied probabilities of those best prices sum to less
    than 100%, backing every outcome locks in a profit.
    """
    events = get(f"/sports/{sport}/odds", {"markets": "h2h", "oddsFormat": "american"})
    rows = []
    for ev in events:
        best = {}  # outcome name -> (american, decimal, book)
        for bm in ev.get("bookmakers", []):
            for mkt in bm.get("markets", []):
                if mkt.get("key") != "h2h":
                    continue
                for out in mkt.get("outcomes", []):
                    d = american_to_decimal(out["price"])
                    cur = best.get(out["name"])
                    if cur is None or d > cur[1]:
                        best[out["name"]] = (out["price"], d, bm.get("title") or bm["key"])
        if len(best) < 2:
            continue
        decimals = [v[1] for v in best.values()]
        total_implied = sum(1.0 / d for d in decimals) * 100.0
        profit_pct = (100.0 / total_implied - 1.0) * 100.0
        rows.append((ev, best, total_implied, profit_pct))
    rows.sort(key=lambda r: r[2])
    if as_json:
        print(json.dumps([
            {
                "event": f"{r[0].get('away_team')} @ {r[0].get('home_team')}",
                "commence_time": r[0].get("commence_time"),
                "best_prices": {k: {"odds": v[0], "book": v[2]} for k, v in r[1].items()},
                "total_implied_pct": round(r[2], 2),
                "profit_pct": round(r[3], 2),
                "is_arb": r[3] > 0,
            } for r in rows
        ], indent=2))
        return
    table = Table(title=f"Best-price scan from raw odds: {sport} (h2h)", box=box.ASCII)
    table.add_column("Matchup")
    table.add_column("Best prices (book)")
    table.add_column("Implied %", justify="right")
    table.add_column("Profit %", justify="right")
    table.add_column(f"Stakes (${bankroll:g})", justify="right")
    n_arbs = 0
    for ev, best, total_implied, profit_pct in rows[:limit]:
        is_arb = profit_pct > 0 and profit_pct >= min_profit
        if is_arb:
            n_arbs += 1
        prices = ", ".join(
            f"{name} {fmt_american(v[0])} ({v[2]})" for name, v in best.items()
        )
        stakes, _ = stake_split([v[1] for v in best.values()], bankroll)
        stakes_str = " / ".join(f"{s:.2f}" for s in stakes) if is_arb else "-"
        style = "green" if is_arb else None
        table.add_row(
            f"{ev.get('away_team', '?')} @ {ev.get('home_team', '?')}",
            prices,
            f"{total_implied:.2f}",
            f"{profit_pct:+.2f}",
            stakes_str,
            style=style,
        )
    console.print(table)
    console.print(
        f"{n_arbs} arb(s) at or above {min_profit}% profit. "
        "Implied % under 100 means backing every outcome at those books locks in the margin."
    )


def main():
    p = argparse.ArgumentParser(
        prog="arb_scanner",
        description="Scan sportsbook odds for arbitrage using ParlayAPI.",
    )
    p.add_argument("sport", nargs="?", default="basketball_nba",
                   help="sport key, e.g. basketball_nba (default). See --list-sports.")
    p.add_argument("--source", choices=["api", "odds"], default="api",
                   help="api: server-side /arbitrage feed (default). odds: fetch raw /odds and compute locally.")
    p.add_argument("--min-profit", type=float, default=0.0, metavar="PCT",
                   help="only show arbs with at least this profit percent (default 0)")
    p.add_argument("--bankroll", type=float, default=100.0,
                   help="bankroll used for the stake split columns (default 100)")
    p.add_argument("--limit", type=int, default=20, help="max rows to display (default 20)")
    p.add_argument("--list-sports", action="store_true", help="list available sport keys and exit")
    p.add_argument("--json", action="store_true", help="print raw JSON instead of a table")
    args = p.parse_args()

    if not args.json:
        mode_banner()
    if args.list_sports:
        cmd_list_sports()
    elif args.source == "odds":
        cmd_scan_odds(args.sport, args.min_profit, args.bankroll, args.limit, args.json)
    else:
        cmd_scan_api(args.sport, args.min_profit, args.bankroll, args.limit, args.json)


if __name__ == "__main__":
    main()
