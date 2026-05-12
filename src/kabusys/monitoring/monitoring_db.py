# src/kabusys/monitoring/monitoring_db.py
"""MonitoringDB — SQLite を使った監視ログの永続化層。

ビジネスロジックを持たない。読み書きのみ。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone


def init_monitoring_db(conn: sqlite3.Connection) -> None:
    """7テーブル + インデックスを作成する（冪等）。"""
    # WAL モード: 複数プロセスからの同時書き込みに対して行レベルロックを使う
    # PRAGMA はトランザクション外で実行する必要があるため executescript の前に置く
    conn.execute("PRAGMA journal_mode=WAL")
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
        CREATE INDEX IF NOT EXISTS idx_risk_logs_event_detail_time
            ON risk_logs (event_type, detail, logged_at);

        CREATE TABLE IF NOT EXISTS dashboard (
            id               INTEGER PRIMARY KEY CHECK (id = 1),
            updated_at       TEXT    NOT NULL,
            portfolio_value  REAL    NOT NULL,
            cash             REAL    NOT NULL,
            drawdown_pct     REAL    NOT NULL,
            open_order_count INTEGER NOT NULL,
            position_count   INTEGER NOT NULL,
            peak_value       REAL
        );

        CREATE TABLE IF NOT EXISTS ai_wizard_messages (
            id          INTEGER   PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT      NOT NULL,
            -- 現在は user/assistant のみ使用。system は将来の拡張用。
            role        TEXT      NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content     TEXT      NOT NULL,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        -- id は挿入順を保証するため ORDER BY id ASC で利用する
        CREATE INDEX IF NOT EXISTS idx_wizard_messages_session
            ON ai_wizard_messages (session_id, id);

        CREATE TABLE IF NOT EXISTS process_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name    TEXT    NOT NULL,
            pid         INTEGER,
            started_at  TEXT    NOT NULL,
            finished_at TEXT,
            status      TEXT    NOT NULL DEFAULT 'running',
            log_file    TEXT,
            error_msg   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_process_runs_started_at
            ON process_runs (started_at);
        CREATE INDEX IF NOT EXISTS idx_process_runs_status
            ON process_runs (status);
    """)
    conn.commit()

    # 既存 DB に peak_value カラムがない場合のマイグレーション
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(dashboard)")}
    if "peak_value" not in existing_cols:
        conn.execute("ALTER TABLE dashboard ADD COLUMN peak_value REAL")
        conn.commit()

    # 既存 DB に latency_ms カラムがない場合のマイグレーション
    existing_trade_cols = {row[1] for row in conn.execute("PRAGMA table_info(trade_logs)")}
    if "latency_ms" not in existing_trade_cols:
        conn.execute("ALTER TABLE trade_logs ADD COLUMN latency_ms REAL")
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
        latency_ms: float | None = None,
    ) -> None:
        """発注イベントを trade_logs テーブルに追記する。

        price: 成行注文は 0.0（order_repository.py と同規約）
        filled_qty / state: スキーマ列順と一致させること
        """
        ts = logged_at.isoformat() if logged_at else self._now()
        self._conn.execute(
            """
            INSERT INTO trade_logs
                (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                event_type,
                client_order_id,
                code,
                side,
                qty,
                price,
                filled_qty,
                state,
                latency_ms,
            ),
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
        dedup_minutes: int | None = None,
    ) -> bool:
        """リスクイベントを risk_logs テーブルに追記する。

        dedup_minutes が指定されている場合、同一 (event_type, detail) ペアが
        直近 dedup_minutes 分以内に記録済みであれば INSERT をスキップして False を返す。
        スキップ判定 SELECT が失敗した場合はフェイルオープン（INSERT を実行）。

        Returns:
            True: INSERT 実行 / False: スキップ
        """
        now_dt = logged_at or datetime.now(timezone.utc)
        ts = now_dt.isoformat()

        if dedup_minutes is not None:
            try:
                cutoff_ts = (now_dt - timedelta(minutes=dedup_minutes)).isoformat()
                if detail is None:
                    row = self._conn.execute(
                        """
                        SELECT 1 FROM risk_logs
                        WHERE event_type = ?
                          AND detail IS NULL
                          AND logged_at >= ?
                        LIMIT 1
                        """,
                        (event_type, cutoff_ts),
                    ).fetchone()
                else:
                    row = self._conn.execute(
                        """
                        SELECT 1 FROM risk_logs
                        WHERE event_type = ?
                          AND detail = ?
                          AND logged_at >= ?
                        LIMIT 1
                        """,
                        (event_type, detail, cutoff_ts),
                    ).fetchone()
                if row:
                    return False
            except (sqlite3.Error, ValueError, TypeError):
                pass  # フェイルオープン: SELECT 失敗時は INSERT を実行

        self._conn.execute(
            """
            INSERT INTO risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ts, event_type, metric_name, metric_value, threshold, detail),
        )
        self._conn.commit()
        return True

    def upsert_dashboard(
        self,
        portfolio_value: float,
        cash: float,
        drawdown_pct: float,
        open_order_count: int,
        position_count: int,
        updated_at: datetime | None = None,
        peak_value: float | None = None,
    ) -> None:
        """ダッシュボード集計を更新する（常に id=1 の1行のみ保持）。

        peak_value=None の場合、既存の peak_value を上書きしない。
        INSERT ... ON CONFLICT DO UPDATE SET + COALESCE を使用することで、
        INSERT OR REPLACE の DELETE→INSERT 問題を回避する。
        """
        ts = updated_at.isoformat() if updated_at else self._now()
        self._conn.execute(
            """
            INSERT INTO dashboard
                (id, updated_at, portfolio_value, cash, drawdown_pct,
                 open_order_count, position_count, peak_value)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at       = excluded.updated_at,
                portfolio_value  = excluded.portfolio_value,
                cash             = excluded.cash,
                drawdown_pct     = excluded.drawdown_pct,
                open_order_count = excluded.open_order_count,
                position_count   = excluded.position_count,
                peak_value       = COALESCE(excluded.peak_value, dashboard.peak_value)
            """,
            (
                ts,
                portfolio_value,
                cash,
                drawdown_pct,
                open_order_count,
                position_count,
                peak_value,
            ),
        )
        self._conn.commit()

    def get_dashboard(self) -> dict | None:
        """ダッシュボード集計を dict で返す。レコードなしの場合は None。

        row_factory = sqlite3.Row が設定済みであることを前提とする。
        """
        cursor = self._conn.execute("SELECT * FROM dashboard WHERE id = 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_wizard_message(self, session_id: str, role: str, content: str) -> None:
        """AI ウィザードの発言を ai_wizard_messages テーブルに保存する。"""
        self._conn.execute(
            "INSERT INTO ai_wizard_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        self._conn.commit()

    def load_wizard_messages(self, session_id: str) -> list[dict]:
        """session_id に紐づく発言履歴を時系列順で返す。

        Returns:
            [{"role": "user"|"assistant", "content": "..."}, ...]
        """
        rows = self._conn.execute(
            "SELECT role, content FROM ai_wizard_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def clear_wizard_messages(self, session_id: str) -> None:
        """session_id に紐づく全発言を削除する。"""
        self._conn.execute(
            "DELETE FROM ai_wizard_messages WHERE session_id = ?",
            (session_id,),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # process_runs — プロセス実行管理
    # ------------------------------------------------------------------

    def start_process(
        self,
        job_name: str,
        pid: int | None = None,
        log_file: str | None = None,
        started_at: datetime | None = None,
    ) -> int:
        """process_runs にプロセス開始を記録して run_id を返す。"""
        ts = started_at.isoformat() if started_at else self._now()
        cursor = self._conn.execute(
            """
            INSERT INTO process_runs (job_name, pid, started_at, status, log_file)
            VALUES (?, ?, ?, 'running', ?)
            """,
            (job_name, pid, ts, log_file),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def finish_process(
        self,
        run_id: int,
        status: str,
        error_msg: str | None = None,
        finished_at: datetime | None = None,
    ) -> int:
        """process_runs のレコードを完了・失敗として更新する。更新件数を返す。"""
        ts = finished_at.isoformat() if finished_at else self._now()
        cur = self._conn.execute(
            "UPDATE process_runs SET finished_at=?, status=?, error_msg=? WHERE id=?",
            (ts, status, error_msg, run_id),
        )
        self._conn.commit()
        return cur.rowcount

    def list_recent_processes(self, hours: int = 24) -> list[dict]:
        """直近 hours 時間のプロセス一覧を返す（実行中含む）。

        実行中（finished_at IS NULL）のレコードは hours に関わらず常に含む。
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = self._conn.execute(
            """
            SELECT * FROM process_runs
            WHERE finished_at IS NULL
               OR started_at >= ?
               OR finished_at >= ?
            ORDER BY COALESCE(finished_at, started_at) DESC
            """,
            (cutoff, cutoff),
        ).fetchall()
        return [dict(row) for row in rows]

    def prune_old_process_runs(self, days: int = 30) -> int:
        """days 日以上前の完了済みレコードを削除する。実行中レコードは削除しない。

        Returns:
            削除件数
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = self._conn.execute(
            "DELETE FROM process_runs WHERE started_at < ? AND finished_at IS NOT NULL",
            (cutoff,),
        )
        self._conn.commit()
        return cursor.rowcount
