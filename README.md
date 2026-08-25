# parlayapi-arb-scanner

A small Python CLI that finds sportsbook arbitrage using the [ParlayAPI](https://parlay-api.com) odds API.

Zero setup by default: it runs against ParlayAPI's keyless sandbox endpoints, so the quickstart below works with no account, no API key, and no config. Set one environment variable to point it at live odds from 45+ sportsbooks and sources.

## 30-second quickstart

Requires [uv](https://docs.astral.sh/uv/). Dependencies resolve automatically on first run.

```bash
git clone https://github.com/JacobiusMakes/parlayapi-arb-scanner.git
cd parlayapi-arb-scanner
uv run arb_scanner.py
```

Real captured sandbox run:

```text
SANDBOX mode: https://parlay-api.com/v1/sandbox (synthetic data, no key needed). Set PARLAY_API_KEY for live
odds.
                                      Arbitrage: basketball_nba (3 found)
+--------------------------------------------------------------------------------------------------------------+
| Matchup               | Market    | Side A                | Side B                | Profit % | Stakes ($100) |
|-----------------------+-----------+-----------------------+-----------------------+----------+---------------|
| Sandbox Away 1 @      | Moneyline | over +120 @ betmgm    | under -105 @ caesars  |     0.80 | 47.02 / 52.98 |
| Sandbox Home 1        |           |                       |                       |          |               |
| Sandbox Away 0 @      | Total     | over +120 @ betmgm    | under -110 @ fanatics |     0.69 | 46.46 / 53.54 |
| Sandbox Home 0        |           |                       |                       |          |               |
| Sandbox Away 2 @      | Total     | over +110 @           | under -115 @ bet365   |     0.69 | 47.10 / 52.90 |
| Sandbox Home 2        |           | draftkings            |                       |          |               |
+--------------------------------------------------------------------------------------------------------------+
Synthetic data; matches production /v1/sports/{key}/arbitrage shape.
```

## What it does

Two scan modes against two ParlayAPI endpoints:

- `--source api` (default): hits `/v1/sports/{sport}/arbitrage`, ParlayAPI's server-side arb feed, and renders it with an equal-payout stake split for your bankroll.
- `--source odds`: hits `/v1/sports/{sport}/odds`, takes the best available price on every outcome across all books, and computes the arb math locally. Good for seeing how detection actually works, and it handles 3-way markets (soccer) too.

```bash
uv run arb_scanner.py --list-sports                    # what can I scan?
uv run arb_scanner.py icehockey_nhl                    # another sport
uv run arb_scanner.py --source odds                    # compute arbs locally from raw odds
uv run arb_scanner.py --min-profit 1.5 --bankroll 500  # filter, and size stakes for $500
uv run arb_scanner.py --json                           # machine-readable output
```

## Going live

Grab a free API key (1,000 credits/month, no card required) at [parlay-api.com](https://parlay-api.com), then:

```bash
PARLAY_API_KEY=pk_your_key uv run arb_scanner.py
```

That switches every request from the sandbox to the live `/v1` endpoints: 45+ sportsbooks and sources, 90+ sports, sub-5-second freshness on major markets. Paid tiers and limits are on the [pricing page](https://parlay-api.com/pricing).

## How the arb math works

Decimal odds `d` imply a probability of `1/d`. For one market, take the best price on each outcome across all books and sum the implied probabilities. If the total is under 100%, backing every outcome locks in the gap:

```text
inv    = 1/d_1 + 1/d_2 + ... + 1/d_n     (arb if inv < 1)
stake_i = bankroll * (1/d_i) / inv        (every outcome pays the same)
profit  = bankroll * (1/inv - 1)
```

Worked example: best prices of +105 (decimal 2.05) at one book and +100 (decimal 2.00) at another give `1/2.05 + 1/2.00 = 0.9878`. Staking $49.38 / $50.62 of a $100 bankroll returns about $101.23 whichever side wins, a 1.23% locked profit. The `--source odds` mode does exactly this computation on live ParlayAPI data.

An honest note: real arbitrage is rare, margins are usually under 1-2%, windows close in minutes as books move their lines, and sportsbooks limit accounts that do this consistently. The sandbox data is synthetic and deliberately generous so the tool always has something to show. Nothing here is betting advice.

## Options

| Flag | Default | What it does |
|---|---|---|
| `sport` (positional) | `basketball_nba` | Sport key, see `--list-sports` |
| `--source api\|odds` | `api` | Server-side arb feed, or local math from raw odds |
| `--min-profit PCT` | `0` | Hide arbs below this profit percent |
| `--bankroll N` | `100` | Bankroll used for the stake split columns |
| `--limit N` | `20` | Max rows displayed |
| `--json` | off | Raw JSON instead of a table |
| `--list-sports` | off | List available sport keys and exit |

## About

Built by the ParlayAPI team. ParlayAPI is a drop-in replacement for the-odds-api with a free tier, a [Python SDK](https://pypi.org/project/parlay-api/) (`pip install parlay-api`), an [MCP server](https://pypi.org/project/parlayapi-mcp/) for AI agents, and [full docs](https://parlay-api.com/docs).

MIT licensed. See [LICENSE](LICENSE).
