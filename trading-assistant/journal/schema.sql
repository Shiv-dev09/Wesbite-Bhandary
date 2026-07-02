-- Trading assistant SQLite schema (paper-trading journal + local caches).
-- This database never stores anything related to real broker orders --
-- see broker/paper_broker.py for the enforced paper-only boundary.

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,                 -- BUY / SELL
    entry_time TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_time TEXT,
    exit_price REAL,
    qty INTEGER NOT NULL,
    initial_sl REAL,
    trailing_sl REAL,
    target REAL,
    exit_reason TEXT,                   -- SL_HIT / TARGET_HIT / TRAILING_SL / EOD_FLATTEN / MANUAL
    indicator_snapshot TEXT,            -- JSON blob
    confidence_score REAL,
    pnl REAL,
    holding_seconds INTEGER,
    status TEXT NOT NULL DEFAULT 'OPEN' -- OPEN / CLOSED
);

CREATE TABLE IF NOT EXISTS daily_summary (
    trade_date TEXT PRIMARY KEY,
    realized_pnl REAL NOT NULL DEFAULT 0,
    trades_count INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    target_hit INTEGER NOT NULL DEFAULT 0,
    loss_limit_hit INTEGER NOT NULL DEFAULT 0
);

-- Written externally by utils/feed_ingest.py from Kite MCP snapshots (LTP/
-- quote calls). Read by broker/external_feed_provider.py. Never written by
-- strategies/risk/broker/dashboard code directly.
CREATE TABLE IF NOT EXISTS market_snapshots (
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,
    ltp REAL,
    bid REAL,
    ask REAL,
    volume INTEGER,
    oi INTEGER,
    ohlc_json TEXT,
    PRIMARY KEY (symbol, ts)
);

-- OHLCV bar cache shared by the backtest engine (historical, populated via
-- get_historical_data MCP calls) and the live-paper feed (intraday minute
-- bars, populated via utils/feed_ingest.py). Same shape, different callers.
CREATE TABLE IF NOT EXISTS bars (
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,   -- e.g. 'minute', 'day'
    ts TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    PRIMARY KEY (symbol, interval, ts)
);

CREATE TABLE IF NOT EXISTS instrument_cache (
    tradingsymbol TEXT PRIMARY KEY,
    exchange TEXT,
    instrument_token INTEGER,
    lot_size INTEGER,
    tick_size REAL,
    instrument_type TEXT,
    expiry TEXT,
    strike REAL
);

CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_ts ON market_snapshots(symbol, ts);
CREATE INDEX IF NOT EXISTS idx_bars_symbol_interval_ts ON bars(symbol, interval, ts);
