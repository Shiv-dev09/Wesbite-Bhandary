# Trading Assistant — NSE Intraday Paper-Trading Decision Support

A modular decision-support system for NSE intraday trading (NIFTY, BANKNIFTY,
FINNIFTY, and liquid large-cap stocks): 10 independent strategies behind a
shared multi-confirmation scoring layer, config-driven risk management,
position sizing, a SQLite+CSV trade journal, a backtest engine, and a
terminal dashboard — built against the Kite MCP connection.

## This system is paper trading only

No code path in this project places, modifies, or cancels a real broker
order. `broker/`, `strategies/`, `risk/`, and `dashboard/` never import or
reference a live Kite order-mutation tool (`place_order`, `modify_order`,
`cancel_order`, `place_gtt_order`, `modify_gtt_order`, `delete_gtt_order`).
This is enforced two ways:

1. **Structurally** — `broker/paper_broker.py` is the only concrete broker
   ever instantiated, and it simulates fills against a `MarketDataProvider`
   quote plus a slippage model. It has no dependency on any live order tool.
2. **By a static test** — `tests/test_broker/test_no_live_order_imports.py`
   parses every module under `broker/`, `strategies/`, `risk/`, and
   `dashboard/` with the `ast` module and fails the build if any of those
   identifiers appears as an actual import, call, or attribute access
   (not just in a comment or docstring).

This also sidesteps SEBI's Feb-2025 API algo-trading framework, which
requires broker/exchange registration and an approved algo-ID before any
retail API can place live orders automatically — none of that exists here.

## Why market data is handled the way it is

Kite market data is only reachable via MCP tools, which are only callable
from an orchestrating Claude Code session — not from an unattended
background Python process. So "how new market data arrives" is decoupled
from "how the strategy/risk/broker engine consumes it":

- `broker/market_data.py` defines `MarketDataProvider` — the only
  interface strategies, risk, broker, and dashboard code touch.
- `broker/backtest_data_provider.py` implements it by replaying bars
  cached locally in the `bars` SQLite table (populated ahead of time via
  a one-off `get_historical_data` MCP ingestion).
- `broker/external_feed_provider.py` implements it by reading the latest
  snapshot from `market_snapshots` / `bars` — it never calls MCP itself.
- `utils/feed_ingest.py` is the only thing that writes into those tables.
  During a live-paper session, the orchestrating agent calls
  `get_ltp`/`get_quotes` (and periodically `get_historical_data` for
  fresh minute bars) for the watchlist, normalizes the result into the
  JSON shape documented in `feed_ingest.py`'s docstring, pipes it through
  `feed_ingest.py`, then runs `python main.py run-cycle`.

`backtest/engine.py` and `main.py run-cycle` run the *identical* pipeline
(strategy → confirmation → risk → position sizing → paper broker); only
the injected `MarketDataProvider` differs. That's what proves the
paper-only wall holds regardless of which mode you're running.

**Future option, not implemented in this build:** true continuous
unattended polling would need a user-run local script using the real
`kiteconnect` pip package with the user's own API key/access token,
implementing `MarketDataProvider` the same way (e.g. `KiteConnectDataProvider`).
That's a deliberate scope boundary, not an oversight.

## Known simplifications

- **Index instruments and options.** `option_momentum` and
  `banknifty_scalping` generate a directional bias from the underlying
  index's own price action, but the paper broker currently simulates the
  fill at the index/underlying LTP itself rather than routing through an
  actual resolved option contract (ATM/ITM1 strike selection via
  `broker/instruments.py` + `indicators/greeks.py` exists as infrastructure
  for this, but the order-routing step that picks a real contract symbol
  from `search_instruments` results isn't wired up yet). Treat these two
  strategies' PnL as a directional proxy, not a realistic options P&L.
- **Consecutive-loss pause across process restarts.** `main.py run-cycle`
  is a fresh process each invocation; trade counts, wins/losses, and
  realized PnL are correctly reconstructed from the SQLite journal on
  each run, but the wall-clock pause timer after 3 consecutive losses
  does not survive a process restart mid-pause.
- **Volume safety check on minute bars.** `safety_checks.volume_check`
  compares the *current bar's* volume against `min_volume` (50,000 by
  default). That's a reasonable single-tick liquidity filter, but it is
  not a cumulative-session-volume check — a low-volume single minute can
  reject an otherwise fine setup.

## Setup

```bash
cd trading-assistant
python -m venv .venv
.venv\Scripts\activate        # or `source .venv/bin/activate` on Linux/Mac
pip install -r requirements.txt
python main.py init-db
```

## CLI

```bash
python main.py init-db
python main.py backtest --strategy ema_trend_following --symbol RELIANCE --interval minute
python main.py backtest-compare --symbol RELIANCE --interval minute
python main.py run-cycle     # one live-paper tick; reads local DB only
python main.py dashboard     # render current state without advancing the engine
```

`--interval` must stay intraday (`minute`, `3minute`, etc.) for
session-time gating (09:15 scan start / 09:20 first trade / 14:45 no new
entries / 15:15 square-off) to produce any trades — daily candles carry a
midnight timestamp that always falls outside the session window.

## Configuration

All trading parameters — capital, risk limits, session times, safety
checks, options filters, confirmation weights/threshold, per-strategy
params, and the watchlist — live in `config/default.yaml`. Nothing is
hardcoded in strategy or risk code; add a new strategy by implementing
`StrategyBase.generate_signal()`, registering it in
`strategies/registry.py`, and adding its `params` block to the config.

## Testing

```bash
pytest
```

175 tests cover indicators, all 10 strategies (contract + individual
logic), the confirmation engine, risk manager (daily limits, session-time
gating, safety checks), position sizer, stop/target/trailing-stop logic,
the paper broker (fills, flatten, slippage), the journal (SQLite + CSV),
backtest metrics, and the no-live-order-imports regression guard — all
against synthetic fixtures, with zero MCP access required.
