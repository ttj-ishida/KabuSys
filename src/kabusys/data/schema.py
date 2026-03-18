"""
DuckDB スキーマ定義と初期化モジュール

DataSchema.md に基づき、3層構造のテーブルを定義・初期化する。

  Raw Layer      : 取得した生データ
  Processed Layer: 整形済み市場データ
  Feature Layer  : 戦略・AI用特徴量
  Execution Layer: 発注・約定・ポジション管理
"""

from __future__ import annotations

from pathlib import Path

import duckdb

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
    --       news_articles 削除時はアプリ側で先に news_symbols を削除すること。
    FOREIGN KEY (news_id) REFERENCES news_articles(id)
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

# ---- Execution Layer -------------------------------------------------------

_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    date         DATE        NOT NULL,
    code         VARCHAR     NOT NULL,
    side         VARCHAR     NOT NULL CHECK (side IN ('buy', 'sell')),
    score        DOUBLE,
    signal_rank  INTEGER,
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
                                  CHECK (status IN ('pending','processing','filled','cancelled','error')),
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

_PORTFOLIO_PERFORMANCE = """
CREATE TABLE IF NOT EXISTS portfolio_performance (
    date            DATE        NOT NULL PRIMARY KEY,
    equity          DECIMAL(20,4) NOT NULL,
    cash            DECIMAL(20,4) NOT NULL,
    drawdown        DOUBLE,
    daily_return    DOUBLE
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
    # Processed
    _PRICES_DAILY,
    _MARKET_CALENDAR,
    _FUNDAMENTALS,
    _NEWS_ARTICLES,
    _NEWS_SYMBOLS,
    # Feature
    _FEATURES,
    _AI_SCORES,
    # Execution
    _SIGNALS,
    _SIGNAL_QUEUE,
    _PORTFOLIO_TARGETS,
    _ORDERS,
    _TRADES,
    _POSITIONS,
    _PORTFOLIO_PERFORMANCE,
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
        except Exception:
            pass
        raise
    return conn


def get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """既存の DuckDB データベースへの接続を返す。

    スキーマの初期化は行わない。初回は init_schema() を使用すること。
    """
    return duckdb.connect(str(db_path))
