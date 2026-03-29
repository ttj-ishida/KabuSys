# src/kabusys/monitoring/monitoring_db.py
"""MonitoringDB — SQLite を使った監視ログの永続化層。

ビジネスロジックを持たない。読み書きのみ。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def init_monitoring_db(conn: sqlite3.Connection) -> None:
    """5テーブル + インデックスを作成する（冪等）。"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS system_status (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at    TEXT    NOT NULL,
            cpu_percent    REAL    NOT NULL,
            memory_percent REAL    NOT NULL,
            disk_percent   REAL    NOT NULL,
            process_ok     INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_system_status_recorded_at
            ON system_status (recorded_at);

        CREATE TABLE IF NOT EXISTS trade_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at       TEXT    NOT NULL,
            event_type      TEXT    NOT NULL,
            client_order_id TEXT    NOT NULL,
            code            TEXT    NOT NULL,
            side            TEXT    NOT NULL,
            qty             INTEGER NOT NULL,
            price           REAL    NOT NULL DEFAULT 0.0,
            filled_qty      INTEGER NOT NULL DEFAULT 0,
            state           TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_trade_logs_logged_at
            ON trade_logs (logged_at);
        CREATE INDEX IF NOT EXISTS idx_trade_logs_client_order_id
            ON trade_logs (client_order_id);

        CREATE TABLE IF NOT EXISTS positions (
            code          TEXT    PRIMARY KEY,
            qty           INTEGER NOT NULL,
            avg_price     REAL    NOT NULL,
            current_price REAL,
            updated_at    TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_positions_updated_at
            ON positions (updated_at);

        CREATE TABLE IF NOT EXISTS risk_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at    TEXT    NOT NULL,
            event_type   TEXT    NOT NULL,
            metric_name  TEXT    NOT NULL,
            metric_value REAL    NOT NULL,
            threshold    REAL    NOT NULL,
            detail       TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_risk_logs_logged_at
            ON risk_logs (logged_at);
        CREATE INDEX IF NOT EXISTS idx_risk_logs_event_type
            ON risk_logs (event_type);

        CREATE TABLE IF NOT EXISTS dashboard (
            id                INTEGER PRIMARY KEY CHECK (id = 1),
            updated_at        TEXT    NOT NULL,
            portfolio_value   REAL    NOT NULL,
            cash              REAL    NOT NULL,
            drawdown_pct      REAL    NOT NULL,
            open_order_count  INTEGER NOT NULL,
            position_count    INTEGER NOT NULL
        );
    """)
    conn.commit()


class MonitoringDB:
    """監視ログ DB の読み書きクラス。ビジネスロジックを持たない。

    Notes:
        __init__ で conn.row_factory = sqlite3.Row を設定する（order_repository.py と同パターン）。
        これは呼び出し元の conn オブジェクトへの副作用だが、monitoring.db と orders.db は
        別ファイルのため共有されない。
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        conn.row_factory = sqlite3.Row
        self._conn = conn

    def _now(self) -> str:
        """現在時刻を ISO8601 UTC 文字列で返す。"""
        return datetime.now(timezone.utc).isoformat()
