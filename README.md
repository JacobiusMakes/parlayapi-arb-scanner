# parlayapi-arb-scanner

A Python CLI example that displays arbitrage candidates from ParlayAPI responses
or calculates them from returned odds. A displayed candidate does not establish
complete compatible outcomes, current source prices or an executable profit.

The code selects a sandbox request path when no key is configured and account
requests when `PARLAY_API_KEY` is set. Check current endpoint access and exact
scope before a private evaluation; the retained example output below is not a
current availability check.

## Existing command-line quickstart

Requires [uv](https://docs.astral.sh/uv/). Dependencies resolve automatically on first run.

```bash
git clone https://github.com/JacobiusMakes/parlayapi-arb-scanner.git
cd parlayapi-arb-scanner
uv run arb_scanner.py
```

Retained sandbox transcript with invented data, not current source observations:

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

## Plan a private evaluation

Use the free [workload planner](https://parlay-api.com/tools/api-workload?utm_source=github&utm_medium=tool_readme&utm_campaign=arb-scanner)
to record your polling interval, active window, separately requested sports,
endpoints, pages and active days. It needs no account or key and makes no API
requests. Keep credit cost unknown until the exact unit cost is verified.

## Account requests

Create your own [account](https://parlay-api.com/signup?utm_source=github&utm_medium=tool_readme&utm_campaign=arb-scanner), keep its key private, then choose your request:

```bash
PARLAY_API_KEY=pk_your_key uv run arb_scanner.py
```

This selects account `/v1` request paths. Your own entitlement and allowance apply. Verify exact returned records, timestamp semantics and request-cost rules in the current [documentation](https://parlay-api.com/docs) and [pricing](https://parlay-api.com/pricing).

## How the arb math works

Decimal odds `d` imply a probability of `1/d`. For one market, take the best price on each outcome across all books and sum the implied probabilities. For a complete, compatible outcome set, the example uses the following equal-payout arithmetic. It assumes the entered numbers remain available and does not prove execution or profit:

```text
inv    = 1/d_1 + 1/d_2 + ... + 1/d_n     (arb if inv < 1)
stake_i = bankroll * (1/d_i) / inv        (every outcome pays the same)
profit  = bankroll * (1/inv - 1)
```

This is arithmetic on the entered numbers. The `--source odds` mode applies it
to returned records. Verify their exact event, market, settlement rules and
complete outcome set separately. A calculated payout is not an executed wager
or a verified market opportunity. The retained sandbox records are invented.

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

Built by the ParlayAPI team. See the current [Python client source](https://github.com/JacobiusMakes/parlay-api-python), [MCP server source](https://github.com/JacobiusMakes/parlay-api-mcp) and [documentation](https://parlay-api.com/docs).

MIT-licensed code, see [LICENSE](LICENSE). Sharing the software does not grant
permission to redistribute API data. Use your own account and applicable data-use
permissions for a private project.

---

Explore related source projects at [github.com/JacobiusMakes](https://github.com/JacobiusMakes).
