# src/kabusys/run_process_monitor.py
"""CLI プロセス監視: 実行中・直近のプロセス一覧を表示する。

使い方:
    python -m kabusys.run_process_monitor
    python -m kabusys.run_process_monitor --hours 48
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from kabusys.operations.process_registry import is_pid_alive, list_processes


def _elapsed(started_at_iso: str, finished_at_iso: str | None = None) -> str:
    """開始〜終了（または現在）の経過時間を文字列で返す。"""
    try:
        start = datetime.fromisoformat(started_at_iso)
        end = (
            datetime.fromisoformat(finished_at_iso)
            if finished_at_iso
            else datetime.now(timezone.utc)
        )
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        secs = int((end - start).total_seconds())
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        if h:
            return f"{h}h{m:02d}m{s:02d}s"
        elif m:
            return f"{m}m{s:02d}s"
        return f"{s}s"
    except Exception:
        return "?"


def main() -> None:
    parser = argparse.ArgumentParser(description="プロセス実行状況を表示する")
    parser.add_argument("--hours", type=int, default=24, help="取得範囲（時間、デフォルト 24）")
    args = parser.parse_args()

    rows = list_processes(hours=args.hours)

    running = [r for r in rows if r["finished_at"] is None]
    completed = [r for r in rows if r["finished_at"] is not None]

    alive_running = []
    orphaned = []
    for r in running:
        pid = r.get("pid")
        if pid is not None and not is_pid_alive(pid):
            orphaned.append(r)
        else:
            alive_running.append(r)

    print("=== 実行中プロセス ===")
    if alive_running:
        for r in alive_running:
            elapsed = _elapsed(r["started_at"])
            print(
                f"  {r['job_name']:<32} PID={str(r['pid'] or '-'):<8}"
                f" 開始={r['started_at'][:19]}  経過={elapsed}"
            )
    else:
        print("  (なし)")

    if orphaned:
        print("\n=== 孤立プロセス（クラッシュ検知） ===")
        for r in orphaned:
            elapsed = _elapsed(r["started_at"])
            print(
                f"  {r['job_name']:<32} PID={str(r['pid'] or '-'):<8}"
                f" 開始={r['started_at'][:19]}  経過={elapsed}  ⚠️ PID 生存なし"
            )

    print(f"\n=== 直近の完了プロセス（過去 {args.hours} 時間） ===")
    if completed:
        _STATUS_ICON = {"success": "✅", "warning": "⚠️ ", "failed": "❌"}
        for r in completed:
            elapsed = _elapsed(r["started_at"], r["finished_at"])
            icon = _STATUS_ICON.get(r["status"], "❓")
            fin = r["finished_at"][:19] if r["finished_at"] else "?"
            print(
                f"  {r['job_name']:<32} {icon} {r['status']:<10}"
                f" {r['started_at'][:19]} → {fin}  ({elapsed})"
            )
    else:
        print("  (なし)")


if __name__ == "__main__":
    main()
