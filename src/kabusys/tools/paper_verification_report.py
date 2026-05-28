# src/kabusys/tools/paper_verification_report.py
"""Paper Trading 検証レポート生成スクリプト。

使用方法:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

環境変数:
    PAPER_TRADING_SQLITE_PATH: SQLite DBファイルパス (デフォルト: data/paper_trading.db)
"""

from __future__ import annotations

import argparse
import math
import os
import sqlite3
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Pass/Fail 基準値
# ---------------------------------------------------------------------------
THRESHOLD_UPTIME_PCT = 99.0  # 稼働率 >= 99%
THRESHOLD_FILL_RATE_PCT = 90.0  # 注文成功率 >= 90%
THRESHOLD_SEND_RATE_PCT = 95.0  # 送信率 >= 95%
THRESHOLD_P95_LATENCY_MS = 200.0  # P95 レイテンシ <= 200 ms


def _p95(values: list[float]) -> Optional[float]:
    """P95 パーセンタイルを計算する。空リストの場合は None を返す。"""
    if not values:
        return None
    sorted_vals = sorted(values)
    idx = max(math.ceil(len(sorted_vals) * 0.95) - 1, 0)
    return sorted_vals[idx]


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


def _query_system_stability(
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


def _query_order_stats(
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


def _query_risk_rejections(
    conn: sqlite3.Connection,
    from_dt: Optional[str],
    to_dt: Optional[str],
) -> int:
    """risk_logs テーブルからリスク却下数を取得する。"""
    where, params = _build_date_filter("logged_at", from_dt, to_dt)
    where_clause = f"WHERE {where}" if where else ""

    row = conn.execute(
        f"SELECT COUNT(*) FROM risk_logs {where_clause}",
        params,
    ).fetchone()
    return row[0] if row else 0


def _query_latency(
    conn: sqlite3.Connection,
    from_dt: Optional[str],
    to_dt: Optional[str],
) -> dict:
    """trade_logs テーブルからレイテンシ指標を取得する。"""
    where_parts, params = _build_date_filter("logged_at", from_dt, to_dt)
    # latency_ms IS NOT NULL の条件を追加
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
    p95_ms = _p95(latency_values)

    return {
        "avg_ms": avg_ms,
        "max_ms": max_ms,
        "p95_ms": p95_ms,
    }


def _fmt_float(value: Optional[float], decimals: int = 1, suffix: str = "") -> str:
    """数値を文字列にフォーマットする。None の場合は 'N/A' を返す。"""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}{suffix}"


def _fmt_int(value: Optional[int]) -> str:
    """整数を文字列にフォーマットする。None の場合は 'N/A' を返す。"""
    if value is None:
        return "N/A"
    return str(value)


def generate_report(
    db_path: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    monitoring_db_path: Optional[str] = None,
) -> None:
    """検証レポートを生成して標準出力に印字する。

    Args:
        db_path: SQLite DBファイルパス
        from_date: フィルタ開始日 (YYYY-MM-DD 形式)
        to_date: フィルタ終了日 (YYYY-MM-DD 形式)
    """
    # 日付フィルタを ISO8601 UTC 文字列に変換
    from_dt: Optional[str] = None
    to_dt: Optional[str] = None
    if from_date:
        from_dt = f"{from_date}T00:00:00+00:00"
    if to_date:
        to_dt = f"{to_date}T23:59:59.999999+00:00"

    # DB 存在チェック
    if not Path(db_path).exists():
        print(f"エラー: DB ファイルが見つかりません: {db_path}")
        print(
            "PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで正しいパスを指定してください。"
        )
        return

    stability_db_path = monitoring_db_path or db_path
    if not Path(stability_db_path).exists():
        stability_db_path = db_path

    stability_conn = sqlite3.connect(stability_db_path)
    try:
        try:
            stability = _query_system_stability(stability_conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            stability = {"total_polls": 0, "error_count": 0, "uptime_pct": None}
    finally:
        stability_conn.close()

    # DB 接続
    conn = sqlite3.connect(db_path)
    try:
        try:
            orders = _query_order_stats(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            orders = {
                "created_count": 0,
                "filled_count": 0,
                "sent_count": 0,
                "fill_rate_pct": None,
                "send_rate_pct": None,
            }
        try:
            risk_rejections = _query_risk_rejections(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            risk_rejections = 0
        try:
            latency = _query_latency(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            latency = {"avg_ms": None, "max_ms": None, "p95_ms": None}
    finally:
        conn.close()

    # 期間表示
    period_from = from_date if from_date else "----"
    period_to = to_date if to_date else "----"

    # Pass/Fail 判定
    failures: list[str] = []

    uptime_pct = stability["uptime_pct"]
    if uptime_pct is None:
        failures.append("稼働率: N/A (データなし)")
    elif uptime_pct < THRESHOLD_UPTIME_PCT:
        failures.append(f"稼働率: {uptime_pct:.1f}% < {THRESHOLD_UPTIME_PCT}%")

    if orders["created_count"] == 0:
        failures.append("注文データなし（対象期間に Created イベントが存在しない）")

    fill_rate_pct = orders["fill_rate_pct"]
    if fill_rate_pct is not None and fill_rate_pct < THRESHOLD_FILL_RATE_PCT:
        failures.append(f"注文成功率: {fill_rate_pct:.1f}% < {THRESHOLD_FILL_RATE_PCT}%")

    send_rate_pct = orders["send_rate_pct"]
    if send_rate_pct is not None and send_rate_pct < THRESHOLD_SEND_RATE_PCT:
        failures.append(f"送信率: {send_rate_pct:.1f}% < {THRESHOLD_SEND_RATE_PCT}%")

    p95_ms = latency["p95_ms"]
    if p95_ms is not None and p95_ms > THRESHOLD_P95_LATENCY_MS:
        failures.append(f"P95レイテンシ: {p95_ms:.1f} ms > {THRESHOLD_P95_LATENCY_MS} ms")

    passed = len(failures) == 0
    verdict = "PASS (全指標が基準値を満たしています)" if passed else f"FAIL ({'; '.join(failures)})"

    # レポート出力
    print("========================================")
    print(" Paper Trading 検証レポート")
    print(f" 期間: {period_from} ~ {period_to}")
    print("========================================")
    print("[システム安定性]")
    print(f"  総ポーリング数:   {_fmt_int(stability['total_polls'])}")
    print(f"  エラー発生数:     {_fmt_int(stability['error_count'])}")
    print(f"  稼働率:           {_fmt_float(uptime_pct, 1, '%')}")
    print()
    print("[注文成功率]")
    print(f"  総注文数:         {_fmt_int(orders['created_count'])}")
    print(f"  成立数(Filled):   {_fmt_int(orders['filled_count'])}")
    print(f"  成功率:           {_fmt_float(fill_rate_pct, 1, '%')}")
    print()
    print("[シグナル精度]")
    print(f"  Created 注文数:   {_fmt_int(orders['created_count'])}")
    print(f"  Sent 注文数:      {_fmt_int(orders['sent_count'])}")
    print(f"  送信率:           {_fmt_float(send_rate_pct, 1, '%')}")
    print(f"  リスク却下数:     {risk_rejections} 件  (risk_logs 参照)")
    print()
    print("[APIレイテンシ]")
    print(f"  平均レイテンシ:    {_fmt_float(latency['avg_ms'], 1, ' ms')}")
    print(f"  最大レイテンシ:    {_fmt_float(latency['max_ms'], 1, ' ms')}")
    print(f"  P95レイテンシ:     {_fmt_float(p95_ms, 1, ' ms')}")
    print()
    print(f"判定: {verdict}")
    print("========================================")


def main() -> None:
    """コマンドラインエントリポイント。"""
    parser = argparse.ArgumentParser(description="Paper Trading 検証レポートを生成します。")
    parser.add_argument(
        "--from",
        dest="from_date",
        metavar="YYYY-MM-DD",
        help="レポート期間の開始日 (例: 2026-04-01)",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        metavar="YYYY-MM-DD",
        help="レポート期間の終了日 (例: 2026-04-11)",
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        metavar="PATH",
        help="SQLite DBファイルパス (環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能)",
    )
    parser.add_argument(
        "--monitoring-db",
        dest="monitoring_db_path",
        metavar="PATH",
        help="system_status を読む SQLite DB パス (既定: SQLITE_PATH または data/monitoring.db)",
    )
    args = parser.parse_args()

    # DB パスの解決: --db > 環境変数 > デフォルト
    db_path = args.db_path or os.environ.get("PAPER_TRADING_SQLITE_PATH") or "data/paper_trading.db"
    monitoring_db_path = (
        args.monitoring_db_path or os.environ.get("SQLITE_PATH") or "data/monitoring.db"
    )

    generate_report(
        db_path=db_path,
        from_date=args.from_date,
        to_date=args.to_date,
        monitoring_db_path=monitoring_db_path,
    )


if __name__ == "__main__":
    main()
