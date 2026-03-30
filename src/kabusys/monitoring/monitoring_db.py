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

    def log_system_status(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        process_ok: bool,
        recorded_at: datetime | None = None,
    ) -> None:
        """システム状態を system_status テーブルに追記する。"""
        ts = recorded_at.isoformat() if recorded_at else self._now()
        self._conn.execute(
            """
            INSERT INTO system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, cpu_percent, memory_percent, disk_percent, 1 if process_ok else 0),
        )
        self._conn.commit()

    def log_trade_event(
        self,
        event_type: str,
        client_order_id: str,
        code: str,
        side: str,
        qty: int,
        price: float,
        filled_qty: int = 0,
        state: str = "",
        logged_at: datetime | None = None,
    ) -> None:
        """発注イベントを trade_logs テーブルに追記する。

        price: 成行注文は 0.0（order_repository.py と同規約）
        filled_qty / state: スキーマ列順と一致させること
        """
        ts = logged_at.isoformat() if logged_at else self._now()
        self._conn.execute(
            """
            INSERT INTO trade_logs
                (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, event_type, client_order_id, code, side, qty, price, filled_qty, state),
        )
        self._conn.commit()

    def upsert_position(
        self,
        code: str,
        qty: int,
        avg_price: float,
        current_price: float | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """保有ポジションを upsert する（code をキーに上書き）。"""
        ts = updated_at.isoformat() if updated_at else self._now()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO positions (code, qty, avg_price, current_price, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, qty, avg_price, current_price, ts),
        )
        self._conn.commit()

    def delete_position(self, code: str) -> None:
        """ポジション解消時に code を削除する。"""
        self._conn.execute("DELETE FROM positions WHERE code = ?", (code,))
        self._conn.commit()

    def log_risk_event(
        self,
        event_type: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        detail: str | None = None,
        logged_at: datetime | None = None,
    ) -> None:
        """リスクイベントを risk_logs テーブルに追記する。

        detail: JSON 文字列等の追加情報（NULL 可）
        """
        ts = logged_at.isoformat() if logged_at else self._now()
        self._conn.execute(
            """
            INSERT INTO risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ts, event_type, metric_name, metric_value, threshold, detail),
        )
        self._conn.commit()
