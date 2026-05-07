"""
DuckDB スキーマ定義と初期化モジュール

DataSchema.md に基づき、3層構造のテーブルを定義・初期化する。

  Raw Layer      : 取得した生データ
  Processed Layer: 整形済み市場データ
  Feature Layer  : 戦略・AI用特徴量
  Execution Layer: 発注・約定・ポジション管理
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL 定義
# ---------------------------------------------------------------------------

# ---- Raw Layer -------------------------------------------------------------

_RAW_PRICES = """
CREATE TABLE IF NOT EXISTS raw_prices (
    date        DATE        NOT NULL,
    code        VARCHAR     NOT NULL,
    open        DECIMAL(18,4) CHECK (open >= 0),
    high        DECIMAL(18,4) CHECK (high >= 0),
    low         DECIMAL(18,4) CHECK (low >= 0),
    close       DECIMAL(18,4) CHECK (close >= 0),
    volume      BIGINT        CHECK (volume >= 0),
    turnover    DECIMAL(18,2) CHECK (turnover >= 0),
    adj_factor  DECIMAL(18,6),
    fetched_at  TIMESTAMP   NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (date, code)
)
"""

_RAW_FINANCIALS = """
CREATE TABLE IF NOT EXISTS raw_financials (
    code            VARCHAR     NOT NULL,
    report_date     DATE        NOT NULL,
    period_type     VARCHAR     NOT NULL,
    revenue         DECIMAL(20,4),
    operating_profit DECIMAL(20,4),
    net_income      DECIMAL(20,4),
    eps             DECIMAL(18,4),
    roe             DECIMAL(10,6),
    bps             DECIMAL(18,4),
    fetched_at      TIMESTAMP   NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (code, report_date, period_type)
)
"""

_RAW_NEWS = """
CREATE TABLE IF NOT EXISTS raw_news (
    id          VARCHAR     NOT NULL PRIMARY KEY,
    datetime    TIMESTAMP   NOT NULL,
    source      VARCHAR     NOT NULL,
    title       VARCHAR,
    content     VARCHAR,
    url         VARCHAR,
    fetched_at  TIMESTAMP   NOT NULL DEFAULT current_timestamp
)
"""

_RAW_EXECUTIONS = """
CREATE TABLE IF NOT EXISTS raw_executions (
    execution_id    VARCHAR     NOT NULL PRIMARY KEY,
    order_id        VARCHAR     NOT NULL,
    datetime        TIMESTAMP   NOT NULL,
    code            VARCHAR     NOT NULL,
    side            VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell')),
    price           DECIMAL(18,4) NOT NULL CHECK (price >= 0),
    size            BIGINT        NOT NULL CHECK (size > 0),
    fetched_at      TIMESTAMP     NOT NULL DEFAULT current_timestamp
)
"""

_RAW_DISCLOSURES = """
CREATE TABLE IF NOT EXISTS raw_disclosures (
    id              VARCHAR   NOT NULL PRIMARY KEY,
    disclosed_at    TIMESTAMP NOT NULL,
    code            VARCHAR,
    company_name    VARCHAR,
    title           VARCHAR,
    document_url    VARCHAR,
    document_type   VARCHAR,
    source          VARCHAR   NOT NULL CHECK (source IN ('tdnet', 'edinet')),
    fetched_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
)
"""

# ---- Processed Layer -------------------------------------------------------

_PRICES_DAILY = """
CREATE TABLE IF NOT EXISTS prices_daily (
    date        DATE          NOT NULL,
    code        VARCHAR       NOT NULL,
    open        DECIMAL(18,4) NOT NULL CHECK (open >= 0),
    high        DECIMAL(18,4) NOT NULL CHECK (high >= 0),
    low         DECIMAL(18,4) NOT NULL CHECK (low >= 0 AND low <= high),
    close       DECIMAL(18,4) NOT NULL CHECK (close >= 0),
    volume      BIGINT        NOT NULL CHECK (volume >= 0),
    turnover    DECIMAL(18,2)          CHECK (turnover >= 0),
    PRIMARY KEY (date, code)
)
"""

_MARKET_CALENDAR = """
CREATE TABLE IF NOT EXISTS market_calendar (
    date            DATE        NOT NULL PRIMARY KEY,
    is_trading_day  BOOLEAN     NOT NULL,
    is_half_day     BOOLEAN     NOT NULL DEFAULT false,
    is_sq_day       BOOLEAN     NOT NULL DEFAULT false,
    holiday_name    VARCHAR
)
"""

_FUNDAMENTALS = """
CREATE TABLE IF NOT EXISTS fundamentals (
    code                VARCHAR     NOT NULL,
    report_date         DATE        NOT NULL,
    period_type         VARCHAR     NOT NULL,
    revenue             DECIMAL(20,4),
    operating_profit    DECIMAL(20,4),
    net_income          DECIMAL(20,4),
    eps                 DECIMAL(18,4),
    roe                 DECIMAL(10,6),
    PRIMARY KEY (code, report_date, period_type)
)
"""

_NEWS_ARTICLES = """
CREATE TABLE IF NOT EXISTS news_articles (
    id          VARCHAR     NOT NULL PRIMARY KEY,
    datetime    TIMESTAMP   NOT NULL,
    source      VARCHAR     NOT NULL,
    title       VARCHAR,
    content     VARCHAR,
    url         VARCHAR
)
"""

_NEWS_SYMBOLS = """
CREATE TABLE IF NOT EXISTS news_symbols (
    news_id     VARCHAR     NOT NULL,
    code        VARCHAR     NOT NULL,
    PRIMARY KEY (news_id, code),
    -- Note: ON DELETE CASCADE は DuckDB 1.5.0 非サポートのため省略。
    --       raw_news 削除時はアプリ側で先に news_symbols を削除すること。
    FOREIGN KEY (news_id) REFERENCES raw_news(id)
)
"""

_DISCLOSURE_EVENTS = """
CREATE TABLE IF NOT EXISTS disclosure_events (
    id               VARCHAR   NOT NULL PRIMARY KEY,
    disclosed_at     TIMESTAMP NOT NULL,
    code             VARCHAR,
    event_type       VARCHAR   NOT NULL,
    event_score      DOUBLE    NOT NULL,
    buy_caution      BOOLEAN   NOT NULL DEFAULT false,
    hold_caution     BOOLEAN   NOT NULL DEFAULT false,
    review_required  BOOLEAN   NOT NULL DEFAULT false,
    title            VARCHAR,
    source           VARCHAR   NOT NULL CHECK (source IN ('tdnet', 'edinet')),
    classified_at    TIMESTAMP NOT NULL DEFAULT current_timestamp
)
"""

# ---- Master Data Layer -----------------------------------------------------

_STOCKS = """
CREATE TABLE IF NOT EXISTS stocks (
    code        VARCHAR     NOT NULL,
    name        VARCHAR,
    market      VARCHAR,
    sector      VARCHAR,
    -- UPSERT 時は ON CONFLICT DO UPDATE SET ... updated_at = now() を明示すること。
    -- DEFAULT now() は INSERT 時のみ設定される（UPSERT では自動更新されない）。
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (code)
)
"""

# ---- Feature Layer ---------------------------------------------------------

_FEATURES = """
CREATE TABLE IF NOT EXISTS features (
    date            DATE        NOT NULL,
    code            VARCHAR     NOT NULL,
    momentum_20     DOUBLE,
    momentum_60     DOUBLE,
    volatility_20   DOUBLE,
    volume_ratio    DOUBLE,
    per             DOUBLE,
    pbr             DOUBLE,
    div_yield       DOUBLE,
    ma200_dev       DOUBLE,
    topix_rel_20    DOUBLE,
    topix_rel_60    DOUBLE,
    quality_score   DOUBLE,
    created_at      TIMESTAMP   NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (date, code)
)
"""

_AI_SCORES = """
CREATE TABLE IF NOT EXISTS ai_scores (
    date                DATE        NOT NULL,
    code                VARCHAR     NOT NULL,
    sentiment_score     DOUBLE,
    regime_score        DOUBLE,
    ai_score            DOUBLE,
    created_at          TIMESTAMP   NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (date, code)
)
"""

_MARKET_REGIME = """
CREATE TABLE IF NOT EXISTS market_regime (
    date             DATE      NOT NULL PRIMARY KEY,
    regime_score     DOUBLE    NOT NULL,
    regime_label     VARCHAR   NOT NULL,
    ma200_ratio      DOUBLE,
    macro_sentiment  DOUBLE,
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp
)
"""

_MARKET_BREADTH = """
CREATE TABLE IF NOT EXISTS market_breadth (
    date                DATE    PRIMARY KEY,
    adv_decline_ratio   DOUBLE  NOT NULL,
    ma25_above_pct      DOUBLE  NOT NULL,
    new_high_low_ratio  DOUBLE,
    breadth_stop        BOOLEAN NOT NULL,
    created_at          TIMESTAMP DEFAULT current_timestamp
)
"""

# ---- Execution Layer -------------------------------------------------------

_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    date             DATE        NOT NULL,
    code             VARCHAR     NOT NULL,
    side             VARCHAR     NOT NULL CHECK (side IN ('buy', 'sell')),
    score            DOUBLE,
    signal_rank      INTEGER,
    size_multiplier  DOUBLE      NOT NULL DEFAULT 1.0,
    PRIMARY KEY (date, code, side)
)
"""

_SIGNAL_QUEUE = """
CREATE TABLE IF NOT EXISTS signal_queue (
    signal_id       VARCHAR     NOT NULL PRIMARY KEY,
    date            DATE        NOT NULL,
    code            VARCHAR     NOT NULL,
    side            VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell')),
    size            BIGINT        NOT NULL CHECK (size > 0),
    order_type      VARCHAR       NOT NULL CHECK (order_type IN ('market', 'limit', 'stop')),
    price           DECIMAL(18,4)          CHECK (price >= 0),
    status          VARCHAR       NOT NULL DEFAULT 'pending'
                                  CHECK (status IN ('pending','processing','filled','cancelled','error','failed')),
    created_at      TIMESTAMP   NOT NULL DEFAULT current_timestamp,
    processed_at    TIMESTAMP
)
"""

_PORTFOLIO_TARGETS = """
CREATE TABLE IF NOT EXISTS portfolio_targets (
    date            DATE        NOT NULL,
    code            VARCHAR     NOT NULL,
    target_weight   DOUBLE,
    target_size     BIGINT,
    PRIMARY KEY (date, code)
)
"""

_ORDERS = """
CREATE TABLE IF NOT EXISTS orders (
    order_id    VARCHAR       NOT NULL PRIMARY KEY,
    signal_id   VARCHAR,
    datetime    TIMESTAMP     NOT NULL,
    code        VARCHAR       NOT NULL,
    side        VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell')),
    size        BIGINT        NOT NULL CHECK (size > 0),
    price       DECIMAL(18,4)          CHECK (price >= 0),
    status      VARCHAR       NOT NULL DEFAULT 'created'
                              CHECK (status IN ('created','sent','filled','cancelled','rejected')),
    -- Note: ON DELETE SET NULL は DuckDB 1.5.0 非サポートのため省略。
    --       signal_queue 削除時はアプリ側で orders.signal_id を NULL に更新してから削除すること。
    FOREIGN KEY (signal_id) REFERENCES signal_queue(signal_id)
)
"""

_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id    VARCHAR       NOT NULL PRIMARY KEY,
    order_id    VARCHAR       NOT NULL,
    datetime    TIMESTAMP     NOT NULL,
    code        VARCHAR       NOT NULL,
    price       DECIMAL(18,4) NOT NULL CHECK (price >= 0),
    size        BIGINT        NOT NULL CHECK (size > 0),
    -- Note: ON DELETE CASCADE は DuckDB 1.5.0 非サポートのため省略。
    --       orders 削除時はアプリ側で先に trades を削除すること。
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
)
"""

_POSITIONS = """
CREATE TABLE IF NOT EXISTS positions (
    date            DATE        NOT NULL,
    code            VARCHAR     NOT NULL,
    position_size   BIGINT      NOT NULL,
    avg_price       DECIMAL(18,4) NOT NULL,
    market_value    DECIMAL(20,4),
    PRIMARY KEY (date, code)
)
"""

_POSITION_ENTRIES = """
CREATE TABLE IF NOT EXISTS position_entries (
    code        VARCHAR  NOT NULL,
    entry_date  DATE     NOT NULL,
    sell_date   DATE,
    PRIMARY KEY (code, entry_date)
)
"""

_EARNINGS_CALENDAR = """
CREATE TABLE IF NOT EXISTS earnings_calendar (
    code              VARCHAR   NOT NULL,
    announcement_date DATE      NOT NULL,
    fetched_at        TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (code, announcement_date)
)
"""

_PORTFOLIO_PERFORMANCE = """
CREATE TABLE IF NOT EXISTS portfolio_performance (
    date            DATE          NOT NULL,
    env             VARCHAR       NOT NULL DEFAULT 'live',
    equity          DECIMAL(20,4) NOT NULL,
    cash            DECIMAL(20,4) NOT NULL DEFAULT 0,
    drawdown        DOUBLE,
    daily_return    DOUBLE,
    PRIMARY KEY (date, env)
)
"""

# ---- Bootstrap Layer -------------------------------------------------------

_DIVIDENDS = """
CREATE TABLE IF NOT EXISTS dividends (
    code         VARCHAR       NOT NULL,
    pub_date     DATE          NOT NULL,
    ref_no       VARCHAR       NOT NULL,
    ex_date      DATE,
    record_date  DATE,
    pay_date     DATE,
    div_rate     DECIMAL(18,4),
    fetched_at   TIMESTAMP     NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (code, pub_date, ref_no)
)
"""

_TOPIX_DAILY = """
CREATE TABLE IF NOT EXISTS topix_daily (
    date   DATE          NOT NULL PRIMARY KEY,
    open   DECIMAL(18,4) NOT NULL,
    high   DECIMAL(18,4) NOT NULL,
    low    DECIMAL(18,4) NOT NULL,
    close  DECIMAL(18,4) NOT NULL
)
"""

_BOOTSTRAP_LOAD_HISTORY = """
CREATE TABLE IF NOT EXISTS bootstrap_load_history (
    file_key   VARCHAR   NOT NULL PRIMARY KEY,
    endpoint   VARCHAR   NOT NULL,
    file_name  VARCHAR   NOT NULL,
    status     VARCHAR   NOT NULL DEFAULT 'pending',
    row_count  BIGINT,
    error_msg  VARCHAR,
    loaded_at  TIMESTAMP
)
"""

# ---- Backtest Layer --------------------------------------------------------

_BACKTEST_RUNS = """
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id                  VARCHAR       PRIMARY KEY,
    created_at              TIMESTAMP     NOT NULL DEFAULT current_timestamp,
    start_date              DATE          NOT NULL,
    end_date                DATE          NOT NULL,
    initial_cash            DECIMAL(18,2) NOT NULL,
    scope_mode              VARCHAR       NOT NULL,
    scope_codes_json        VARCHAR,
    params_json             VARCHAR       NOT NULL,
    cagr                    DOUBLE,
    sharpe                  DOUBLE,
    max_drawdown            DOUBLE,
    win_rate                DOUBLE,
    payoff_ratio            DOUBLE,
    profit_factor           DOUBLE,
    annual_volatility       DOUBLE,
    calmar_ratio            DOUBLE,
    avg_holding_days        DOUBLE,
    total_trades            INTEGER,
    effective_universe_size INTEGER
)
"""

_BACKTEST_TRADES = """
CREATE TABLE IF NOT EXISTS backtest_trades (
    run_id        VARCHAR       NOT NULL,
    trade_seq     INTEGER       NOT NULL,
    date          DATE          NOT NULL,
    code          VARCHAR       NOT NULL,
    side          VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell')),
    shares        INTEGER       NOT NULL,
    price         DECIMAL(18,4) NOT NULL,
    commission    DECIMAL(18,4) NOT NULL,
    realized_pnl  DECIMAL(18,4),
    PRIMARY KEY (run_id, trade_seq)
)
"""

_BACKTEST_DAILY_EQUITY = """
CREATE TABLE IF NOT EXISTS backtest_daily_equity (
    run_id           VARCHAR       NOT NULL,
    date             DATE          NOT NULL,
    portfolio_value  DECIMAL(18,2) NOT NULL,
    cash             DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (run_id, date)
)
"""

# ---------------------------------------------------------------------------
# インデックス定義（頻出クエリパターン: 銘柄×日付範囲スキャン、ステータス検索）
# ---------------------------------------------------------------------------

_INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_prices_daily_code_date ON prices_daily(code, date)",
    "CREATE INDEX IF NOT EXISTS idx_features_code_date ON features(code, date)",
    "CREATE INDEX IF NOT EXISTS idx_ai_scores_code_date ON ai_scores(code, date)",
    "CREATE INDEX IF NOT EXISTS idx_signals_code_date ON signals(code, date)",
    "CREATE INDEX IF NOT EXISTS idx_signal_queue_status ON signal_queue(status)",
    "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
    "CREATE INDEX IF NOT EXISTS idx_orders_signal_id ON orders(signal_id)",
    "CREATE INDEX IF NOT EXISTS idx_trades_order_id ON trades(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_news_symbols_code ON news_symbols(code)",
    "CREATE INDEX IF NOT EXISTS idx_raw_news_datetime ON raw_news(datetime)",
    "CREATE INDEX IF NOT EXISTS idx_position_entries_code_sell ON position_entries(code, sell_date)",
    "CREATE INDEX IF NOT EXISTS idx_position_entries_code_entry ON position_entries(code, entry_date)",
    "CREATE INDEX IF NOT EXISTS idx_raw_disclosures_code ON raw_disclosures(code)",
    "CREATE INDEX IF NOT EXISTS idx_raw_disclosures_disclosed_at ON raw_disclosures(disclosed_at)",
    "CREATE INDEX IF NOT EXISTS idx_disclosure_events_code ON disclosure_events(code)",
    "CREATE INDEX IF NOT EXISTS idx_disclosure_events_disclosed_at ON disclosure_events(disclosed_at)",
    "CREATE INDEX IF NOT EXISTS idx_backtest_trades_run_date ON backtest_trades(run_id, date)",
]

# ---------------------------------------------------------------------------
# スキーママイグレーション（既存 DB への後付けカラム追加）
# ---------------------------------------------------------------------------

_MIGRATIONS: list[str] = [
    # v0.x → v0.y: signals に size_multiplier を追加
    "ALTER TABLE signals ADD COLUMN size_multiplier DOUBLE NOT NULL DEFAULT 1.0",
    # v0.x → v0.y: raw_prices に adj_factor を追加
    "ALTER TABLE raw_prices ADD COLUMN adj_factor DECIMAL(18,6)",
    # v0.x → v0.y: portfolio_performance に env を追加
    "ALTER TABLE portfolio_performance ADD COLUMN env VARCHAR NOT NULL DEFAULT 'live'",
    # Issue #185: raw_financials に bps を追加
    "ALTER TABLE raw_financials ADD COLUMN IF NOT EXISTS bps DECIMAL(18,4)",
    # Issue #259: backtest 永続化テーブル追加（新規 DB は _ALL_DDL で作成済み。既存 DB 用）
    "CREATE TABLE IF NOT EXISTS backtest_runs (run_id VARCHAR PRIMARY KEY, created_at TIMESTAMP NOT NULL DEFAULT current_timestamp, start_date DATE NOT NULL, end_date DATE NOT NULL, initial_cash DECIMAL(18,2) NOT NULL, scope_mode VARCHAR NOT NULL, scope_codes_json VARCHAR, params_json VARCHAR NOT NULL, cagr DOUBLE, sharpe DOUBLE, max_drawdown DOUBLE, win_rate DOUBLE, payoff_ratio DOUBLE, profit_factor DOUBLE, annual_volatility DOUBLE, calmar_ratio DOUBLE, avg_holding_days DOUBLE, total_trades INTEGER, effective_universe_size INTEGER)",
    "CREATE TABLE IF NOT EXISTS backtest_trades (run_id VARCHAR NOT NULL, trade_seq INTEGER NOT NULL, date DATE NOT NULL, code VARCHAR NOT NULL, side VARCHAR NOT NULL CHECK (side IN ('buy', 'sell')), shares INTEGER NOT NULL, price DECIMAL(18,4) NOT NULL, commission DECIMAL(18,4) NOT NULL, realized_pnl DECIMAL(18,4), PRIMARY KEY (run_id, trade_seq))",
    "CREATE TABLE IF NOT EXISTS backtest_daily_equity (run_id VARCHAR NOT NULL, date DATE NOT NULL, portfolio_value DECIMAL(18,2) NOT NULL, cash DECIMAL(18,2) NOT NULL, PRIMARY KEY (run_id, date))",
    # Issue #257: features に TOPIX 相対強度・品質スコアを追加
    "ALTER TABLE features ADD COLUMN IF NOT EXISTS topix_rel_20 DOUBLE",
    "ALTER TABLE features ADD COLUMN IF NOT EXISTS topix_rel_60 DOUBLE",
    "ALTER TABLE features ADD COLUMN IF NOT EXISTS quality_score DOUBLE",
]

# ---------------------------------------------------------------------------
# テーブル作成順（外部キー依存を考慮）
# ---------------------------------------------------------------------------

_ALL_DDL: list[str] = [
    # Raw
    _RAW_PRICES,
    _RAW_FINANCIALS,
    _RAW_NEWS,
    _RAW_EXECUTIONS,
    _RAW_DISCLOSURES,
    # Processed
    _PRICES_DAILY,
    _MARKET_CALENDAR,
    _FUNDAMENTALS,
    _NEWS_ARTICLES,
    _NEWS_SYMBOLS,
    _DISCLOSURE_EVENTS,
    # Master
    _STOCKS,
    # Feature
    _FEATURES,
    _AI_SCORES,
    _MARKET_REGIME,
    _MARKET_BREADTH,  # 追加
    # Execution
    _SIGNALS,
    _SIGNAL_QUEUE,
    _PORTFOLIO_TARGETS,
    _ORDERS,
    _TRADES,
    _POSITIONS,
    _POSITION_ENTRIES,
    _EARNINGS_CALENDAR,
    _PORTFOLIO_PERFORMANCE,
    # Bootstrap
    _DIVIDENDS,
    _TOPIX_DAILY,
    _BOOTSTRAP_LOAD_HISTORY,
    # Backtest
    _BACKTEST_RUNS,
    _BACKTEST_TRADES,
    _BACKTEST_DAILY_EQUITY,
]


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """DuckDB データベースを初期化し、全テーブルを作成して接続を返す。

    既にテーブルが存在する場合はスキップ（冪等）。
    db_path の親ディレクトリが存在しない場合は自動作成する。

    Args:
        db_path: DuckDB ファイルパス。":memory:" でインメモリ DB を使用可能。

    Returns:
        初期化済みの DuckDB 接続。
    """
    db_path_str = str(db_path)
    if db_path_str != ":memory:":
        Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path_str)
    conn.execute("BEGIN")
    try:
        for ddl in _ALL_DDL:
            conn.execute(ddl)
        for idx in _INDEXES:
            conn.execute(idx)
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("init_schema: ROLLBACK failed: %s", rb_exc)
        raise

    # マイグレーション（既存 DB への後付けカラム追加）
    # ALTER TABLE は IF NOT EXISTS 非サポートのため、失敗時は既存カラムとみなしてスキップ
    for migration in _MIGRATIONS:
        try:
            conn.execute(migration)
        except Exception:
            pass

    return conn


def get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """既存の DuckDB データベースへの接続を返す。

    スキーマの初期化は行わない。初回は init_schema() を使用すること。
    """
    return duckdb.connect(str(db_path))
