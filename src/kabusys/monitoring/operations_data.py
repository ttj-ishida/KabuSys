"""operations_data.py — 運用系 Streamlit ページ共通のデータロード関数。

Pre-Market チェック・執行起動サマリ・日中監視・障害サマリ・ペーパートレード
検証などの各データ取得をまとめる。

`dashboard_data.py`（監視エンジン系）とは責務を分離し、
Streamlit に依存しないため単体テスト可能。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# 1. load_premarket_data
# ---------------------------------------------------------------------------


def load_premarket_data(
    duckdb_conn: object,
    sqlite_conn: object,
    settings: object,
) -> dict:
    """Pre-Market チェック結果を収集して辞書で返す。

    Args:
        duckdb_conn: DuckDB 接続（prices_daily / signal_queue クエリ用）
        sqlite_conn: SQLite 接続（positions / signal_queue クエリ用）
        settings: 設定オブジェクト。以下の属性を参照する:
            - kill_flag_path (Path): 停止フラグのパス
            - task_name (str, optional): Task Scheduler タスク名
                                         デフォルト "KabuSys_ExecutionStart"

    Returns:
        dict with keys:
            status, checks, warnings, generated_at,
            signal_queue_pending, position_count,
            stop_flag_exists, data_freshness_ok, task_scheduler_ready
    """
    from kabusys.operations.pre_market_collector import collect
    from kabusys.operations.pre_market_report import build_report

    stop_flag_path: Path = Path(str(settings.kill_flag_path))
    task_name: str = getattr(settings, "task_name", "KabuSys_ExecutionStart")
    today = date.today()

    data = collect(
        duckdb_conn=duckdb_conn,
        sqlite_conn=sqlite_conn,
        stop_flag_path=stop_flag_path,
        task_name=task_name,
        today=today,
    )

    report = build_report(
        report_date=today,
        data_freshness_ok=data.data_freshness_ok,
        signal_queue_pending=data.signal_queue_pending,
        position_count=data.position_count,
        stop_flag_exists=data.stop_flag_exists,
        task_scheduler_ready=data.task_scheduler_ready,
    )

    return {
        "status": report.status,
        "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in report.checks],
        "warnings": report.warnings,
        "generated_at": report.generated_at,
        "signal_queue_pending": data.signal_queue_pending,
        "position_count": data.position_count,
        "stop_flag_exists": data.stop_flag_exists,
        "data_freshness_ok": data.data_freshness_ok,
        "task_scheduler_ready": data.task_scheduler_ready,
    }


# ---------------------------------------------------------------------------
# 2. load_execution_startup
# ---------------------------------------------------------------------------


def load_execution_startup(
    base_dir: Path,
    target_date: Optional[date] = None,
) -> Optional[dict]:
    """執行起動サマリを artifacts/execution_startup/{date}/summary.json から読み込む。

    Args:
        base_dir: execution_startup ディレクトリのベースパス
        target_date: 読み込む日付。省略時は本日。

    Returns:
        summary.json の内容を dict で返す。ファイルが存在しない場合は None。
    """
    if target_date is None:
        target_date = date.today()

    summary_path = Path(base_dir) / target_date.isoformat() / "summary.json"
    if not summary_path.exists():
        return None

    return json.loads(summary_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 3. load_intraday_summary
# ---------------------------------------------------------------------------


def load_intraday_summary(
    sqlite_conn: sqlite3.Connection,
    hours: int = 1,
) -> dict:
    """日中監視サマリを SQLite から取得する。

    Args:
        sqlite_conn: SQLite 接続（risk_logs / dashboard テーブルを持つ DB）
        hours: 集計対象の直近時間数（デフォルト 1 時間）

    Returns:
        dict with keys:
            order_errors (int): 直近 N 時間の ORDER_ERROR 件数
            stale_orders (int): 直近 N 時間の STALE_ORDER 件数
            drawdown_pct (float): 最新ドローダウン（%換算）。データなし時は 0.0
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # ORDER_ERROR カウント
    try:
        row = sqlite_conn.execute(
            "SELECT COUNT(*) FROM risk_logs WHERE event_type = 'ORDER_ERROR' AND logged_at >= ?",
            (cutoff,),
        ).fetchone()
        order_errors = int(row[0]) if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        order_errors = 0

    # STALE_ORDER カウント
    try:
        row = sqlite_conn.execute(
            "SELECT COUNT(*) FROM risk_logs WHERE event_type = 'STALE_ORDER' AND logged_at >= ?",
            (cutoff,),
        ).fetchone()
        stale_orders = int(row[0]) if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        stale_orders = 0

    # 最新 drawdown_pct（DB には分数 e.g. -0.05 で格納 → % 換算して返す）
    drawdown_pct = 0.0
    try:
        row = sqlite_conn.execute(
            "SELECT drawdown_pct FROM dashboard ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        if row and row[0] is not None:
            drawdown_pct = float(row[0]) * 100.0
    except sqlite3.OperationalError:
        pass

    return {
        "order_errors": order_errors,
        "stale_orders": stale_orders,
        "drawdown_pct": drawdown_pct,
    }


# ---------------------------------------------------------------------------
# 4. load_failure_summary
# ---------------------------------------------------------------------------


def load_failure_summary(
    sqlite_conn: sqlite3.Connection,
) -> dict:
    """直近 24 時間の障害イベントサマリを SQLite から取得する。

    Args:
        sqlite_conn: SQLite 接続（risk_logs テーブルを持つ DB）

    Returns:
        dict with keys:
            critical_count (int)
            kill_switch_count (int)
            risk_breach_count (int)
            order_error_count (int)
            recent_events (list[dict])
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    counts: dict[str, int] = {
        "CRITICAL": 0,
        "KILL_SWITCH": 0,
        "RISK_BREACH": 0,
        "ORDER_ERROR": 0,
    }
    recent_events: list[dict] = []

    try:
        # 全件 GROUP BY で正確なカウントを取得（LIMIT 100 によるアンダーカウントを防ぐ）
        cur = sqlite_conn.execute(
            """
            SELECT event_type, COUNT(*) AS cnt
            FROM risk_logs
            WHERE event_type IN ('CRITICAL', 'KILL_SWITCH', 'RISK_BREACH', 'ORDER_ERROR')
              AND logged_at >= ?
            GROUP BY event_type
            """,
            (cutoff,),
        )
        for row in cur.fetchall():
            et, cnt = row[0], row[1]
            if et in counts:
                counts[et] = cnt

        # 直近イベントは別クエリで LIMIT 50 取得
        cur2 = sqlite_conn.execute(
            """
            SELECT event_type, message, logged_at
            FROM risk_logs
            WHERE event_type IN ('CRITICAL', 'KILL_SWITCH', 'RISK_BREACH', 'ORDER_ERROR')
              AND logged_at >= ?
            ORDER BY logged_at DESC
            LIMIT 50
            """,
            (cutoff,),
        )
        cols = [d[0] for d in cur2.description]
        recent_events = [dict(zip(cols, row)) for row in cur2.fetchall()]
    except sqlite3.OperationalError:
        pass

    return {
        "critical_count": counts["CRITICAL"],
        "kill_switch_count": counts["KILL_SWITCH"],
        "risk_breach_count": counts["RISK_BREACH"],
        "order_error_count": counts["ORDER_ERROR"],
        "recent_events": recent_events,
    }


# ---------------------------------------------------------------------------
# 5. load_paper_verification_data
# ---------------------------------------------------------------------------


def _build_date_filter(
    ts_col: str,
    from_dt: Optional[str],
    to_dt: Optional[str],
) -> tuple[str, list[str]]:
    """日付フィルタの WHERE 句フラグメントとパラメータを返す。"""
    clauses: list[str] = []
    params: list[str] = []
    if from_dt:
        clauses.append(f"{ts_col} >= ?")
        params.append(from_dt)
    if to_dt:
        clauses.append(f"{ts_col} <= ?")
        params.append(to_dt)
    if clauses:
        return " AND ".join(clauses), params
    return "", []


def _paper_query_system_stability(
    conn: sqlite3.Connection,
    from_dt: Optional[str],
    to_dt: Optional[str],
) -> dict:
    """system_status テーブルからシステム安定性指標を取得する。"""
    where, params = _build_date_filter("recorded_at", from_dt, to_dt)
    where_clause = f"WHERE {where}" if where else ""

    row = conn.execute(
        f"""
        SELECT
            COUNT(*)            AS total_polls,
            SUM(1 - process_ok) AS error_count,
            CASE WHEN COUNT(*) > 0
                THEN CAST(SUM(process_ok) AS REAL) / COUNT(*) * 100.0
                ELSE NULL
            END AS uptime_pct
        FROM system_status
        {where_clause}
        """,
        params,
    ).fetchone()

    if row is None or row[0] == 0:
        return {"total_polls": 0, "error_count": 0, "uptime_pct": None}

    return {
        "total_polls": row[0],
        "error_count": row[1] if row[1] is not None else 0,
        "uptime_pct": row[2],
    }


def _paper_query_order_stats(
    conn: sqlite3.Connection,
    from_dt: Optional[str],
    to_dt: Optional[str],
) -> dict:
    """trade_logs テーブルから注文成功率・送信率指標を取得する。"""
    where, params = _build_date_filter("logged_at", from_dt, to_dt)
    where_clause = f"WHERE {where}" if where else ""

    row = conn.execute(
        f"""
        SELECT
            COUNT(CASE WHEN event_type = 'Created' THEN 1 END) AS created_count,
            COUNT(CASE WHEN event_type = 'Filled'  THEN 1 END) AS filled_count,
            COUNT(CASE WHEN event_type = 'Sent'    THEN 1 END) AS sent_count
        FROM trade_logs
        {where_clause}
        """,
        params,
    ).fetchone()

    if row is None:
        return {
            "created_count": 0,
            "filled_count": 0,
            "sent_count": 0,
            "fill_rate_pct": None,
            "send_rate_pct": None,
        }

    created = row[0] or 0
    filled = row[1] or 0
    sent = row[2] or 0

    fill_rate = (filled / created * 100.0) if created > 0 else None
    send_rate = (sent / created * 100.0) if created > 0 else None

    return {
        "created_count": created,
        "filled_count": filled,
        "sent_count": sent,
        "fill_rate_pct": fill_rate,
        "send_rate_pct": send_rate,
    }


def _paper_query_latency(
    conn: sqlite3.Connection,
    from_dt: Optional[str],
    to_dt: Optional[str],
) -> dict:
    """trade_logs テーブルからレイテンシ指標を取得する。"""
    import math

    where_parts, params = _build_date_filter("logged_at", from_dt, to_dt)
    latency_condition = "latency_ms IS NOT NULL"
    if where_parts:
        where_clause = f"WHERE {where_parts} AND {latency_condition}"
    else:
        where_clause = f"WHERE {latency_condition}"

    row = conn.execute(
        f"""
        SELECT
            AVG(latency_ms) AS avg_ms,
            MAX(latency_ms) AS max_ms
        FROM trade_logs
        {where_clause}
        """,
        params,
    ).fetchone()

    avg_ms = row[0] if row and row[0] is not None else None
    max_ms = row[1] if row and row[1] is not None else None

    # P95 計算用に全値を取得
    rows = conn.execute(
        f"SELECT latency_ms FROM trade_logs {where_clause}",
        params,
    ).fetchall()
    latency_values = [r[0] for r in rows if r[0] is not None]

    if latency_values:
        sorted_vals = sorted(latency_values)
        idx = max(math.ceil(len(sorted_vals) * 0.95) - 1, 0)
        p95_ms: Optional[float] = sorted_vals[idx]
    else:
        p95_ms = None

    return {
        "avg_ms": avg_ms,
        "max_ms": max_ms,
        "p95_ms": p95_ms,
    }


def load_paper_verification_data(
    paper_sqlite_path: Path,
    from_dt: Optional[str] = None,
    to_dt: Optional[str] = None,
) -> dict:
    """ペーパートレード検証データを SQLite から取得する。

    Args:
        paper_sqlite_path: paper trading SQLite DB ファイルのパス
        from_dt: フィルタ開始日時文字列（ISO8601 形式、省略可）
        to_dt:   フィルタ終了日時文字列（ISO8601 形式、省略可）

    Returns:
        DBが存在しない場合: {"available": False}
        DBが存在する場合:
            {
                "available": True,
                "uptime_pct": float | None,
                "fill_rate_pct": float | None,
                "send_rate_pct": float | None,
                "p95_latency_ms": float | None,
                "pass_fail": str,
                "total_polls": int,
                "created_count": int,
            }
    """
    from kabusys.tools.paper_verification_report import (
        THRESHOLD_FILL_RATE_PCT,
        THRESHOLD_P95_LATENCY_MS,
        THRESHOLD_SEND_RATE_PCT,
        THRESHOLD_UPTIME_PCT,
    )

    paper_sqlite_path = Path(paper_sqlite_path)
    if not paper_sqlite_path.exists():
        return {"available": False}

    uri = paper_sqlite_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        try:
            stability = _paper_query_system_stability(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            stability = {"total_polls": 0, "error_count": 0, "uptime_pct": None}

        try:
            orders = _paper_query_order_stats(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            orders = {
                "created_count": 0,
                "filled_count": 0,
                "sent_count": 0,
                "fill_rate_pct": None,
                "send_rate_pct": None,
            }

        try:
            latency = _paper_query_latency(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            latency = {"avg_ms": None, "max_ms": None, "p95_ms": None}
    finally:
        conn.close()

    uptime_pct = stability.get("uptime_pct")
    fill_rate_pct = orders.get("fill_rate_pct")
    send_rate_pct = orders.get("send_rate_pct")
    p95_latency_ms = latency.get("p95_ms")
    total_polls = stability.get("total_polls", 0)
    created_count = orders.get("created_count", 0)

    # Pass/Fail 判定 — paper_verification_report.py の CLI ロジックと同一基準
    failures: list[bool] = [
        uptime_pct is None,
        uptime_pct is not None and uptime_pct < THRESHOLD_UPTIME_PCT,
        created_count == 0,
        fill_rate_pct is not None and fill_rate_pct < THRESHOLD_FILL_RATE_PCT,
        send_rate_pct is not None and send_rate_pct < THRESHOLD_SEND_RATE_PCT,
        p95_latency_ms is not None and p95_latency_ms > THRESHOLD_P95_LATENCY_MS,
    ]
    pass_fail = "PASS" if not any(failures) else "FAIL"

    return {
        "available": True,
        "uptime_pct": uptime_pct,
        "fill_rate_pct": fill_rate_pct,
        "send_rate_pct": send_rate_pct,
        "p95_latency_ms": p95_latency_ms,
        "pass_fail": pass_fail,
        "total_polls": total_polls,
        "created_count": created_count,
    }
