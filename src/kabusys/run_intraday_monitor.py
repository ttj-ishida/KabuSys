"""run_intraday_monitor.py — ザラ場中監視 CLI エントリーポイント。

使用例:
    python -m kabusys.run_intraday_monitor
    python -m kabusys.run_intraday_monitor --watch
    python -m kabusys.run_intraday_monitor --watch --interval 60
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from kabusys.config import Settings
from kabusys.operations.intraday_collector import (
    IntradaySnapshot,
    collect_intraday_snapshot,
)

_JST = ZoneInfo("Asia/Tokyo")

STATUS_OK = "OK"
STATUS_WARNING = "WARNING"
STATUS_CRITICAL = "CRITICAL"


def _determine_status(snap: IntradaySnapshot) -> str:
    if snap.kill_switch_active or not snap.execution_pid_ok:
        return STATUS_CRITICAL
    if (
        (snap.drawdown_pct is not None and snap.drawdown_pct <= -0.10)
        or snap.order_error_count > 0
        or snap.stale_order_count > 0
        or not snap.monitoring_pid_ok
    ):
        return STATUS_WARNING
    return STATUS_OK


def format_cli_summary(snap: IntradaySnapshot, interval: int | None = None) -> str:
    status = _determine_status(snap)
    now_jst = datetime.now(tz=_JST).strftime("%Y-%m-%d %H:%M:%S JST")

    if status == STATUS_OK:
        status_label = f"✅ {STATUS_OK}"
    elif status == STATUS_WARNING:
        status_label = f"⚠️  {STATUS_WARNING}"
    else:
        status_label = f"🚫 {STATUS_CRITICAL}"

    lines = [
        "====================================================",
        f"  KabuSys Intraday Monitor  {now_jst}",
        f"  Status : {status_label}",
        "====================================================",
        "  プロセス:",
    ]

    if snap.execution_pid_ok:
        lines.append("    [ok  ] execution.pid    稼働中")
    else:
        lines.append("    [CRIT] execution.pid    停止（PID ファイルなし）")

    if snap.monitoring_pid_ok:
        lines.append("    [ok  ] monitoring.pid   稼働中")
    else:
        lines.append("    [WARN] monitoring.pid   停止（PID ファイルなし）")

    if snap.kill_switch_active:
        lines.append(f"    [CRIT] Kill Switch      発動中: {snap.kill_switch_reason}")
    else:
        lines.append("    [ok  ] Kill Switch      発動なし")

    lines.append("----------------------------------------------------")
    lines.append("  リスク:")

    if snap.drawdown_pct is None:
        lines.append("    [ok  ] ドローダウン      データなし")
    elif snap.drawdown_pct <= -0.10:
        lines.append(
            f"    [WARN] ドローダウン      {snap.drawdown_pct * 100:.1f}%（閾値 -10% 超過）"
        )
    else:
        lines.append(f"    [ok  ] ドローダウン      {snap.drawdown_pct * 100:.1f}%")

    if snap.order_error_count > 0:
        lines.append(
            f"    [WARN] 注文エラー        {snap.order_error_count} 件（直近1時間）"
        )
    else:
        lines.append(
            f"    [ok  ] 注文エラー        {snap.order_error_count} 件（直近1時間）"
        )

    if snap.stale_order_count > 0:
        lines.append(
            f"    [WARN] 滞留注文          {snap.stale_order_count} 件（直近1時間）"
        )
    else:
        lines.append(
            f"    [ok  ] 滞留注文          {snap.stale_order_count} 件（直近1時間）"
        )

    lines.append("----------------------------------------------------")
    lines.append("  システム:")

    if snap.process_ok:
        lines.append("    [ok  ] API 接続          正常")
    else:
        lines.append("    [WARN] API 接続          異常")

    if snap.cpu_percent is not None:
        lines.append(f"    [ok  ] CPU               {snap.cpu_percent:.1f}%")
    else:
        lines.append("    [ok  ] CPU               データなし")

    if snap.memory_percent is not None:
        lines.append(f"    [ok  ] Memory            {snap.memory_percent:.1f}%")
    else:
        lines.append("    [ok  ] Memory            データなし")

    lines.append("====================================================")
    if interval is not None:
        lines.append(f"  次回更新: {interval}秒後  Ctrl+C で終了")
        lines.append("====================================================")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="KabuSys ザラ場中監視 CLI")
    parser.add_argument("--watch", action="store_true", help="N 秒ごとに自動更新")
    parser.add_argument("--interval", type=int, default=30, help="更新間隔（秒）")
    args = parser.parse_args()

    settings = Settings()
    sqlite_uri = Path(settings.sqlite_path).resolve().as_uri() + "?mode=ro"

    try:
        conn = sqlite3.connect(sqlite_uri, uri=True)
    except Exception as exc:
        print(f"[ERROR] DB に接続できません: {exc}", file=sys.stderr)
        sys.exit(1)

    conn.row_factory = sqlite3.Row

    try:
        if args.watch:
            while True:
                snap = collect_intraday_snapshot(conn, settings)
                os.system("cls" if os.name == "nt" else "clear")
                print(format_cli_summary(snap, interval=args.interval))
                time.sleep(args.interval)
        else:
            snap = collect_intraday_snapshot(conn, settings)
            print(format_cli_summary(snap))
            status = _determine_status(snap)
            sys.exit(0 if status == STATUS_OK else 1)
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()


if __name__ == "__main__":
    main()
