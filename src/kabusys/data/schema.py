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
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      DOUBLE,
    turnover    DOUBLE,
    fetched_at  TIMESTAMP   NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (date, code)
)
"""

_RAW_FINANCIALS = """
CREATE TABLE IF NOT EXISTS raw_financials (
    code            VARCHAR     NOT NULL,
    report_date     DATE        NOT NULL,
    period_type     VARCHAR,
    revenue         DOUBLE,
    operating_profit DOUBLE,
    net_income      DOUBLE,
    eps             DOUBLE,
    roe             DOUBLE,
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
    side            VARCHAR     NOT NULL,
    price           DOUBLE      NOT NULL,
    size            INTEGER     NOT NULL,
    fetched_at      TIMESTAMP   NOT NULL DEFAULT current_timestamp
)
"""

# ---- Processed Layer -------------------------------------------------------

_PRICES_DAILY = """
CREATE TABLE IF NOT EXISTS prices_daily (
    date        DATE        NOT NULL,
    code        VARCHAR     NOT NULL,
    open        DOUBLE      NOT NULL,
    high        DOUBLE      NOT NULL,
    low         DOUBLE      NOT NULL,
    close       DOUBLE      NOT NULL,
    volume      DOUBLE      NOT NULL,
    turnover    DOUBLE,
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
    period_type         VARCHAR,
    revenue             DOUBLE,
    operating_profit    DOUBLE,
    net_income          DOUBLE,
    eps                 DOUBLE,
    roe                 DOUBLE,
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
    PRIMARY KEY (news_id, code)
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
    date    DATE        NOT NULL,
    code    VARCHAR     NOT NULL,
    side    VARCHAR     NOT NULL CHECK (side IN ('buy', 'sell')),
    score   DOUBLE,
    rank    INTEGER,
    PRIMARY KEY (date, code, side)
)
"""

_SIGNAL_QUEUE = """
CREATE TABLE IF NOT EXISTS signal_queue (
    signal_id       VARCHAR     NOT NULL PRIMARY KEY,
    date            DATE        NOT NULL,
    code            VARCHAR     NOT NULL,
    side            VARCHAR     NOT NULL CHECK (side IN ('buy', 'sell')),
    size            INTEGER     NOT NULL,
    order_type      VARCHAR     NOT NULL,
    price           DOUBLE,
    status          VARCHAR     NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','processing','executed','cancelled','error')),
    created_at      TIMESTAMP   NOT NULL DEFAULT current_timestamp,
    processed_at    TIMESTAMP
)
"""

_PORTFOLIO_TARGETS = """
CREATE TABLE IF NOT EXISTS portfolio_targets (
    date            DATE        NOT NULL,
    code            VARCHAR     NOT NULL,
    target_weight   DOUBLE,
    target_size     INTEGER,
    PRIMARY KEY (date, code)
)
"""

_ORDERS = """
CREATE TABLE IF NOT EXISTS orders (
    order_id    VARCHAR     NOT NULL PRIMARY KEY,
    signal_id   VARCHAR,
    datetime    TIMESTAMP   NOT NULL,
    code        VARCHAR     NOT NULL,
    side        VARCHAR     NOT NULL CHECK (side IN ('buy', 'sell')),
    size        INTEGER     NOT NULL,
    price       DOUBLE,
    status      VARCHAR     NOT NULL DEFAULT 'created'
                            CHECK (status IN ('created','sent','filled','cancelled','rejected'))
)
"""

_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id    VARCHAR     NOT NULL PRIMARY KEY,
    order_id    VARCHAR     NOT NULL,
    datetime    TIMESTAMP   NOT NULL,
    code        VARCHAR     NOT NULL,
    price       DOUBLE      NOT NULL,
    size        INTEGER     NOT NULL
)
"""

_POSITIONS = """
CREATE TABLE IF NOT EXISTS positions (
    date            DATE        NOT NULL,
    code            VARCHAR     NOT NULL,
    position_size   INTEGER     NOT NULL,
    avg_price       DOUBLE      NOT NULL,
    market_value    DOUBLE,
    PRIMARY KEY (date, code)
)
"""

_PORTFOLIO_PERFORMANCE = """
CREATE TABLE IF NOT EXISTS portfolio_performance (
    date            DATE        NOT NULL PRIMARY KEY,
    equity          DOUBLE      NOT NULL,
    cash            DOUBLE      NOT NULL,
    drawdown        DOUBLE,
    daily_return    DOUBLE
)
"""

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

    Args:
        db_path: DuckDB ファイルパス。":memory:" でインメモリ DB を使用可能。

    Returns:
        初期化済みの DuckDB 接続。
    """
    conn = duckdb.connect(str(db_path))
    for ddl in _ALL_DDL:
        conn.execute(ddl)
    return conn


def get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """既存の DuckDB データベースへの接続を返す。

    スキーマの初期化は行わない。初回は init_schema() を使用すること。
    """
    return duckdb.connect(str(db_path))
