"""Paper Trading 検証レポート出力スクリプト。

稼働後の paper_trading.db を集計し、ゴーライブ判断に必要な4指標を表示する。

Usage:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import date
from pathlib import Path

# 合格基準
UPTIME_THRESHOLD = 99.0        # 稼働率 ≥ 99%
SUCCESS_RATE_THRESHOLD = 90.0  # 注文成功率（Filled/Created） ≥ 90%
SEND_RATE_THRESHOLD = 95.0     # 送信率（Sent/Created） ≥ 95%
LATENCY_P95_THRESHOLD = 200.0  # P95レイテンシ ≤ 200ms

DEFAULT_DB_PATH = Path("data/paper_trading.db")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Paper Trading 検証レポート")
    parser.add_argument(
        "--from",
        dest="date_from",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
    )
    parser.add_argument(
        "--to",
        dest="date_to",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
    )
    return parser.parse_args()


def _date_filter(
    date_from: date | None, date_to: date | None, col: str = "logged_at"
) -> tuple[str, list]:
    """WHERE 句に付加できる AND 条件文字列と引数リストを返す。"""
    conds, params = [], []
    if date_from:
        conds.append(f"{col} >= ?")
        params.append(date_from.isoformat())
    if date_to:
        conds.append(f"{col} <= ?")
        # UTC タイムスタンプと正しく比較するため +00:00 必須
        params.append(date_to.isoformat() + "T23:59:59+00:00")
    return ("AND " + " AND ".join(conds) if conds else ""), params


def _uptime(
    conn: sqlite3.Connection, date_from: date | None, date_to: date | None
) -> dict:
    suf, params = _date_filter(date_from, date_to, col="recorded_at")
    row = conn.execute(
        f"SELECT COUNT(*), SUM(process_ok) FROM system_status WHERE 1=1 {suf}",
        params,
    ).fetchone()
    total = row[0] or 0
    ok = int(row[1] or 0)
    return {
        "total": total,
        "errors": total - ok,
        "rate": (ok / total * 100) if total > 0 else 0.0,
    }


def _order_success(
    conn: sqlite3.Connection, date_from: date | None, date_to: date | None
) -> dict:
    suf, params = _date_filter(date_from, date_to)
    created = conn.execute(
        f"SELECT COUNT(*) FROM trade_logs WHERE event_type='Created' {suf}", params
    ).fetchone()[0]
    filled = conn.execute(
        f"SELECT COUNT(*) FROM trade_logs WHERE event_type='Filled' {suf}", params
    ).fetchone()[0]
    return {
        "total": created,
        "filled": filled,
        "rate": (filled / created * 100) if created > 0 else 0.0,
    }


def _signal_accuracy(
    conn: sqlite3.Connection, date_from: date | None, date_to: date | None
) -> dict:
    suf, params = _date_filter(date_from, date_to)
    created = conn.execute(
        f"SELECT COUNT(*) FROM trade_logs WHERE event_type='Created' {suf}", params
    ).fetchone()[0]
    sent = conn.execute(
        f"SELECT COUNT(*) FROM trade_logs WHERE event_type='Sent' {suf}", params
    ).fetchone()[0]
    risk_rejections = conn.execute(
        f"SELECT COUNT(*) FROM risk_logs WHERE 1=1 {suf}", params
    ).fetchone()[0]
    return {
        "created": created,
        "sent": sent,
        "rate": (sent / created * 100) if created > 0 else 0.0,
        "risk_rejections": risk_rejections,
    }


def _latency(
    conn: sqlite3.Connection, date_from: date | None, date_to: date | None
) -> dict:
    suf, params = _date_filter(date_from, date_to)
    rows = conn.execute(
        f"SELECT latency_ms FROM trade_logs WHERE latency_ms IS NOT NULL {suf}",
        params,
    ).fetchall()
    values = sorted(r[0] for r in rows)
    if not values:
        return {"avg": None, "max": None, "p95": None}
    avg = sum(values) / len(values)
    max_ = values[-1]
    # statistics.quantiles() は len>=2 必須かつ単一要素で StatisticsError が発生するため
    # 手動インデックス計算を使用（len==1 でも正しく values[0] を返す）
    idx = max(0, int(len(values) * 0.95) - 1)
    p95 = values[idx]
    return {"avg": avg, "max": max_, "p95": p95}


def _verdict(
    uptime_rate: float,
    success_rate: float,
    send_rate: float,
    p95: float | None,
) -> str:
    ok = (
        uptime_rate >= UPTIME_THRESHOLD
        and success_rate >= SUCCESS_RATE_THRESHOLD
        and send_rate >= SEND_RATE_THRESHOLD
        and (p95 is None or p95 <= LATENCY_P95_THRESHOLD)
    )
    return "PASS" if ok else "FAIL"


def generate_report(
    db_path: Path, date_from: date | None = None, date_to: date | None = None
) -> str:
    """レポート文字列を生成して返す（テスト・CLI 共用）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        u = _uptime(conn, date_from, date_to)
        s = _order_success(conn, date_from, date_to)
        sig = _signal_accuracy(conn, date_from, date_to)
        lat = _latency(conn, date_from, date_to)
    finally:
        conn.close()

    period = f"{date_from or '(全期間)'} ~ {date_to or '(全期間)'}"
    v = _verdict(u["rate"], s["rate"], sig["rate"], lat["p95"])

    lat_lines = ["[APIレイテンシ]"]
    if lat["avg"] is not None:
        lat_lines += [
            f"  平均レイテンシ:    {lat['avg']:.1f} ms",
            f"  最大レイテンシ:    {lat['max']:.1f} ms",
            f"  P95レイテンシ:     {lat['p95']:.1f} ms",
        ]
    else:
        lat_lines.append("  データなし")

    lines = [
        "=" * 40,
        " Paper Trading 検証レポート",
        f" 期間: {period}",
        "=" * 40,
        "[システム安定性]",
        f"  総ポーリング数:   {u['total']}",
        f"  エラー発生数:     {u['errors']}",
        f"  稼働率:           {u['rate']:.1f}%",
        "",
        "[注文成功率]",
        f"  総注文数:         {s['total']}",
        f"  成立数(Filled):   {s['filled']}",
        f"  成功率:           {s['rate']:.1f}%",
        "",
        "[シグナル精度]",
        f"  Created 注文数:   {sig['created']}",
        f"  Sent 注文数:      {sig['sent']}",
        f"  送信率:           {sig['rate']:.1f}%",
        f"  リスク却下数:     {sig['risk_rejections']} 件  (risk_logs 参照)",
        "",
        *lat_lines,
        "",
        f"判定: {v} {'(全指標が基準値を満たしています)' if v == 'PASS' else '(基準値を満たさない指標があります)'}",
        "=" * 40,
    ]
    return "\n".join(lines)


def main() -> None:
    args = _parse_args()
    db_path = Path(os.environ.get("PAPER_TRADING_SQLITE_PATH", str(DEFAULT_DB_PATH)))
    if not db_path.exists():
        print(f"[ERROR] DB が見つかりません: {db_path}")
        return
    print(generate_report(db_path, args.date_from, args.date_to))


if __name__ == "__main__":
    main()
