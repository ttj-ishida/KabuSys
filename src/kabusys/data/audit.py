"""
監査ログ・トレーサビリティモジュール

DataPlatform.md Section 8 に基づき、シグナルから約定に至るフローを
UUID 連鎖によって完全にトレース可能にする監査テーブルを定義・初期化する。

トレーサビリティ階層:
    business_date (営業日)
      └─ strategy_id (戦略バージョン)
           └─ signal_id (シグナル固有ID)
                └─ order_request_id (内部発注ID / 冪等キー)
                     └─ broker_order_id (証券会社受付ID)

設計原則:
  - エラーや棄却されたシグナル・発注も必ず永続化する（ステータス付与）
  - order_request_id は冪等キーとして機能し、二重発注を防止する
  - すべてのテーブルに created_at を持ち、監査証跡を保証する
"""

from __future__ import annotations

from pathlib import Path

import duckdb

# ---------------------------------------------------------------------------
# DDL 定義
# ---------------------------------------------------------------------------

# シグナル生成ログ
# 戦略層が生成したシグナルをすべて記録する。リスク管理で棄却されたものも含む。
_SIGNAL_EVENTS = """
CREATE TABLE IF NOT EXISTS signal_events (
    signal_id       VARCHAR       NOT NULL PRIMARY KEY,  -- UUID
    business_date   DATE          NOT NULL,
    strategy_id     VARCHAR       NOT NULL,
    code            VARCHAR       NOT NULL,
    side            VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell', 'hold')),
    final_score     DOUBLE,
    decision        VARCHAR       NOT NULL
                    CHECK (decision IN (
                        'buy', 'sell', 'hold',
                        'rejected_by_risk',
                        'rejected_by_position_limit',
                        'rejected_by_drawdown',
                        'cancelled',
                        'error'
                    )),
    reason          VARCHAR,
    created_at      TIMESTAMP     NOT NULL DEFAULT current_timestamp
)
"""

# 発注要求ログ（冪等キー付き）
# order_request_id が冪等キー。同一キーで再送しても一度しか処理されない。
_ORDER_REQUESTS = """
CREATE TABLE IF NOT EXISTS order_requests (
    order_request_id    VARCHAR       NOT NULL PRIMARY KEY,  -- UUID (冪等キー)
    signal_id           VARCHAR       NOT NULL,              -- signal_events.signal_id
    business_date       DATE          NOT NULL,
    code                VARCHAR       NOT NULL,
    side                VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell')),
    requested_qty       BIGINT        NOT NULL CHECK (requested_qty > 0),
    order_type          VARCHAR       NOT NULL CHECK (order_type IN ('market', 'limit', 'stop')),
    limit_price         DECIMAL(18,4)          CHECK (limit_price >= 0),
    broker_order_id     VARCHAR,                             -- 証券会社受付ID (送信後に設定)
    status              VARCHAR       NOT NULL DEFAULT 'pending'
                        CHECK (status IN (
                            'pending',
                            'sent',
                            'filled',
                            'partially_filled',
                            'cancelled',
                            'rejected',
                            'error'
                        )),
    error_message       VARCHAR,
    created_at          TIMESTAMP     NOT NULL DEFAULT current_timestamp,
    updated_at          TIMESTAMP     NOT NULL DEFAULT current_timestamp,
    FOREIGN KEY (signal_id) REFERENCES signal_events(signal_id)
)
"""

# 約定ログ
# 証券会社から返された実際の約定情報を記録する。
_EXECUTIONS = """
CREATE TABLE IF NOT EXISTS executions (
    execution_id        VARCHAR       NOT NULL PRIMARY KEY,  -- UUID
    order_request_id    VARCHAR       NOT NULL,              -- order_requests.order_request_id
    broker_order_id     VARCHAR       NOT NULL,
    code                VARCHAR       NOT NULL,
    side                VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell')),
    filled_qty          BIGINT        NOT NULL CHECK (filled_qty > 0),
    fill_price          DECIMAL(18,4) NOT NULL CHECK (fill_price >= 0),
    commission          DECIMAL(18,4)          CHECK (commission >= 0),
    executed_at         TIMESTAMP     NOT NULL,
    created_at          TIMESTAMP     NOT NULL DEFAULT current_timestamp,
    FOREIGN KEY (order_request_id) REFERENCES order_requests(order_request_id)
)
"""

# ---------------------------------------------------------------------------
# インデックス定義
# ---------------------------------------------------------------------------

_AUDIT_INDEXES: list[str] = [
    # シグナルの日付・銘柄検索
    "CREATE INDEX IF NOT EXISTS idx_signal_events_date_code ON signal_events(business_date, code)",
    # 戦略別・日付別シグナル検索
    "CREATE INDEX IF NOT EXISTS idx_signal_events_strategy ON signal_events(strategy_id, business_date)",
    # 処理待ちキュー取得（status='pending' のスキャン）
    "CREATE INDEX IF NOT EXISTS idx_order_requests_status ON order_requests(status, created_at)",
    # signal_id → order_requests の JOIN
    "CREATE INDEX IF NOT EXISTS idx_order_requests_signal_id ON order_requests(signal_id)",
    # order_request_id → executions の JOIN
    "CREATE INDEX IF NOT EXISTS idx_executions_order_request_id ON executions(order_request_id)",
    # 約定日時での時系列検索
    "CREATE INDEX IF NOT EXISTS idx_executions_executed_at ON executions(executed_at)",
]

# ---------------------------------------------------------------------------
# テーブル作成順（外部キー依存を考慮）
# ---------------------------------------------------------------------------

_AUDIT_DDL: list[str] = [
    _SIGNAL_EVENTS,
    _ORDER_REQUESTS,
    _EXECUTIONS,
]


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """監査ログテーブルを初期化する（冪等）。

    既存の DuckDB 接続に監査ログテーブルを追加する。
    通常は data.schema.init_schema() で取得した接続を渡す。

    Args:
        conn: 初期化済みの DuckDB 接続。
    """
    with conn:
        for ddl in _AUDIT_DDL:
            conn.execute(ddl)
        for idx in _AUDIT_INDEXES:
            conn.execute(idx)


def init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """監査ログ専用の DuckDB データベースを初期化して接続を返す。

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
    init_audit_schema(conn)
    return conn
