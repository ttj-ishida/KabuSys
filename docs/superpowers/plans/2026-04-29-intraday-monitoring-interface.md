# Intraday Monitoring Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ザラ場中（09:00〜15:00）に CLI `--watch` モードと Streamlit ダッシュボードでシステム異常を素早く検知できる監視インターフェースを提供する（Issue #203）。

**Architecture:** `intraday_collector.py` が monitoring SQLite DB を読み取り専用で問い合わせて `IntradaySnapshot` dataclass を返す。`run_intraday_monitor.py` はこれを受け取り CLI 表示する。`streamlit_dashboard.py` は既存を強化して Kill Switch・PID 状態・自動更新を追加する。`run_monitoring.py` は起動時に `monitoring.pid` を書き込み、終了時に削除するよう変更する。

**Tech Stack:** Python 3.10+, SQLite (read-only URI), psutil, Streamlit, argparse

---

## File Map

| 役割 | ファイル | 変更種別 |
|---|---|---|
| DB読み取り専用コレクター | `src/kabusys/operations/intraday_collector.py` | 新規作成 |
| CLI エントリーポイント | `src/kabusys/run_intraday_monitor.py` | 新規作成 |
| Monitoring PID 書き込み | `src/kabusys/run_monitoring.py` | 変更（2箇所） |
| Streamlit ダッシュボード強化 | `src/kabusys/monitoring/streamlit_dashboard.py` | 変更 |
| コレクターのユニットテスト | `tests/test_intraday_collector.py` | 新規作成 |

---

### Task 1: intraday_collector.py + テスト

**Files:**
- Create: `src/kabusys/operations/intraday_collector.py`
- Create: `tests/test_intraday_collector.py`

- [ ] **Step 1: テストファイルの骨格と最初の failing テストを書く**

```python
# tests/test_intraday_collector.py
"""intraday_collector のユニットテスト（インメモリ SQLite + tmp_path）"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from kabusys.monitoring.monitoring_db import init_monitoring_db
from kabusys.operations.intraday_collector import (
    check_pid_file,
    check_kill_switch,
    get_dashboard_row,
    count_recent_risk_events,
    get_latest_system_status,
    get_recent_risk_events,
    collect_intraday_snapshot,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_monitoring_db(c)
    yield c
    c.close()


# --- check_pid_file ---

def test_check_pid_file_false_when_missing(tmp_path):
    assert check_pid_file(tmp_path / "no.pid") is False


def test_check_pid_file_true_for_current_process(tmp_path):
    pid_file = tmp_path / "proc.pid"
    pid_file.write_text(str(os.getpid()))
    assert check_pid_file(pid_file) is True


def test_check_pid_file_false_when_stale_pid(tmp_path):
    pid_file = tmp_path / "stale.pid"
    pid_file.write_text("999999999")
    assert check_pid_file(pid_file) is False
```

- [ ] **Step 2: 失敗を確認する**

```
pytest tests/test_intraday_collector.py -v
```

Expected: ImportError（intraday_collector が存在しないため）

- [ ] **Step 3: `intraday_collector.py` の骨格と `check_pid_file` を実装する**

```python
# src/kabusys/operations/intraday_collector.py
"""intraday_collector.py — ザラ場中監視用 DB 読み取りコレクター（純粋関数）。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

import psutil

from kabusys.config import Settings

_MONITORING_PID = Path("data/monitoring.pid")


@dataclass
class IntradaySnapshot:
    collected_at: str
    execution_pid_ok: bool
    monitoring_pid_ok: bool
    kill_switch_active: bool
    kill_switch_reason: str
    drawdown_pct: float | None
    stale_order_count: int
    order_error_count: int
    process_ok: bool
    cpu_percent: float | None
    memory_percent: float | None
    recent_risk_events: list[dict] = field(default_factory=list)


def check_pid_file(pid_path: Path) -> bool:
    """PID ファイルが存在し、記録された PID が psutil で生存していれば True。"""
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text().strip())
        return psutil.pid_exists(pid)
    except (ValueError, OSError):
        return False
```

- [ ] **Step 4: `check_pid_file` テストを通す**

```
pytest tests/test_intraday_collector.py::test_check_pid_file_false_when_missing tests/test_intraday_collector.py::test_check_pid_file_true_for_current_process tests/test_intraday_collector.py::test_check_pid_file_false_when_stale_pid -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: `check_kill_switch` のテストを追加する**

```python
# tests/test_intraday_collector.py に追加

# --- check_kill_switch ---

def test_check_kill_switch_inactive(tmp_path):
    active, reason = check_kill_switch(tmp_path / "kill.flag")
    assert active is False
    assert reason == ""


def test_check_kill_switch_active(tmp_path):
    flag = tmp_path / "kill.flag"
    flag.write_text("Max drawdown exceeded")
    active, reason = check_kill_switch(flag)
    assert active is True
    assert reason == "Max drawdown exceeded"
```

- [ ] **Step 6: `check_kill_switch` を実装する**

```python
# src/kabusys/operations/intraday_collector.py に追加

def check_kill_switch(flag_path: Path) -> tuple[bool, str]:
    """(active, reason) を返す。flag がなければ (False, "")。"""
    if not flag_path.exists():
        return False, ""
    try:
        reason = flag_path.read_text().strip()
    except OSError:
        reason = ""
    return True, reason
```

- [ ] **Step 7: テストを通す**

```
pytest tests/test_intraday_collector.py -v -k "kill_switch"
```

Expected: PASS (2 tests)

- [ ] **Step 8: `get_dashboard_row` のテストを追加する**

```python
# tests/test_intraday_collector.py に追加

# --- get_dashboard_row ---

def test_get_dashboard_row_none_when_empty(conn):
    from kabusys.operations.intraday_collector import get_dashboard_row
    assert get_dashboard_row(conn) is None


def test_get_dashboard_row_returns_drawdown(conn):
    from kabusys.monitoring.monitoring_db import MonitoringDB
    from kabusys.operations.intraday_collector import get_dashboard_row
    db = MonitoringDB(conn)
    db.update_dashboard(portfolio_value=1_000_000, cash=500_000, drawdown_pct=-0.05)
    row = get_dashboard_row(conn)
    assert row is not None
    assert abs(row["drawdown_pct"] - (-0.05)) < 1e-9
```

- [ ] **Step 9: `get_dashboard_row` を実装する**

```python
# src/kabusys/operations/intraday_collector.py に追加

def get_dashboard_row(conn: sqlite3.Connection) -> dict | None:
    """dashboard テーブルの最新行を dict で返す。レコードなしなら None。"""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM dashboard ORDER BY updated_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return dict(row) if row else None
```

- [ ] **Step 10: テストを通す**

```
pytest tests/test_intraday_collector.py -v -k "dashboard_row"
```

Expected: PASS (2 tests)

- [ ] **Step 11: `count_recent_risk_events` のテストを追加する**

```python
# tests/test_intraday_collector.py に追加

# --- count_recent_risk_events ---

def _insert_risk_event(conn, event_type: str, minutes_ago: int):
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    conn.execute(
        "INSERT INTO risk_logs (event_type, detail, logged_at) VALUES (?, ?, ?)",
        (event_type, "test", ts),
    )
    conn.commit()


def test_count_recent_risk_events_zero_when_empty(conn):
    from kabusys.operations.intraday_collector import count_recent_risk_events
    assert count_recent_risk_events(conn, "STALE_ORDER") == 0


def test_count_recent_risk_events_within_window(conn):
    from kabusys.operations.intraday_collector import count_recent_risk_events
    _insert_risk_event(conn, "STALE_ORDER", 30)
    _insert_risk_event(conn, "STALE_ORDER", 10)
    assert count_recent_risk_events(conn, "STALE_ORDER") == 2


def test_count_recent_risk_events_ignores_old(conn):
    from kabusys.operations.intraday_collector import count_recent_risk_events
    _insert_risk_event(conn, "STALE_ORDER", 90)
    assert count_recent_risk_events(conn, "STALE_ORDER") == 0


def test_count_recent_risk_events_ignores_other_type(conn):
    from kabusys.operations.intraday_collector import count_recent_risk_events
    _insert_risk_event(conn, "ORDER_ERROR", 5)
    assert count_recent_risk_events(conn, "STALE_ORDER") == 0
```

- [ ] **Step 12: `count_recent_risk_events` を実装する**

```python
# src/kabusys/operations/intraday_collector.py に追加

def count_recent_risk_events(
    conn: sqlite3.Connection, event_type: str, minutes: int = 60
) -> int:
    """指定 event_type の直近 N 分以内の件数を返す。"""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM risk_logs WHERE event_type = ? AND logged_at > ?",
        (event_type, cutoff),
    )
    return cursor.fetchone()[0]
```

- [ ] **Step 13: テストを通す**

```
pytest tests/test_intraday_collector.py -v -k "count_recent"
```

Expected: PASS (4 tests)

- [ ] **Step 14: `get_latest_system_status` と `get_recent_risk_events` のテストを追加する**

```python
# tests/test_intraday_collector.py に追加

# --- get_latest_system_status ---

def test_get_latest_system_status_none_when_empty(conn):
    from kabusys.operations.intraday_collector import get_latest_system_status
    assert get_latest_system_status(conn) is None


def test_get_latest_system_status_returns_latest(conn):
    from kabusys.monitoring.monitoring_db import MonitoringDB
    from kabusys.operations.intraday_collector import get_latest_system_status
    db = MonitoringDB(conn)
    db.log_system_status(40.0, 50.0, 60.0, True)
    db.log_system_status(80.0, 70.0, 60.0, True)
    row = get_latest_system_status(conn)
    assert row is not None
    assert abs(row["cpu_percent"] - 80.0) < 1e-9


# --- get_recent_risk_events ---

def test_get_recent_risk_events_empty(conn):
    from kabusys.operations.intraday_collector import get_recent_risk_events
    assert get_recent_risk_events(conn) == []


def test_get_recent_risk_events_limit(conn):
    from kabusys.operations.intraday_collector import get_recent_risk_events
    for i in range(5):
        _insert_risk_event(conn, "ORDER_ERROR", i)
    assert len(get_recent_risk_events(conn, limit=3)) == 3
```

- [ ] **Step 15: `get_latest_system_status` と `get_recent_risk_events` を実装する**

```python
# src/kabusys/operations/intraday_collector.py に追加

def get_latest_system_status(conn: sqlite3.Connection) -> dict | None:
    """system_status の最新1件を dict で返す。レコードなしなら None。"""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM system_status ORDER BY recorded_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_recent_risk_events(
    conn: sqlite3.Connection, limit: int = 10
) -> list[dict]:
    """risk_logs を logged_at DESC で最新 limit 件返す。"""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM risk_logs ORDER BY logged_at DESC LIMIT ?", (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 16: `collect_intraday_snapshot` の統合テストを追加する**

```python
# tests/test_intraday_collector.py に追加

# --- collect_intraday_snapshot ---

class FakeSettings:
    pid_file_path: Path = Path("data/execution.pid")
    kill_flag_path: Path = Path("data/kill.flag")
    sqlite_path: Path = Path("data/monitoring.db")


def test_collect_intraday_snapshot_all_ok(conn, tmp_path):
    from kabusys.monitoring.monitoring_db import MonitoringDB
    from kabusys.operations.intraday_collector import collect_intraday_snapshot

    pid_file = tmp_path / "execution.pid"
    pid_file.write_text(str(os.getpid()))
    kill_flag = tmp_path / "kill.flag"

    settings = FakeSettings()
    settings.pid_file_path = pid_file
    settings.kill_flag_path = kill_flag

    db = MonitoringDB(conn)
    db.update_dashboard(portfolio_value=1_000_000, cash=500_000, drawdown_pct=-0.02)
    db.log_system_status(30.0, 50.0, 60.0, True)

    snap = collect_intraday_snapshot(conn, settings)
    assert snap.execution_pid_ok is True
    assert snap.kill_switch_active is False
    assert snap.kill_switch_reason == ""
    assert snap.drawdown_pct is not None
    assert snap.process_ok is True


def test_collect_intraday_snapshot_kill_switch_active(conn, tmp_path):
    from kabusys.operations.intraday_collector import collect_intraday_snapshot

    pid_file = tmp_path / "execution.pid"
    kill_flag = tmp_path / "kill.flag"
    kill_flag.write_text("Max drawdown exceeded")

    settings = FakeSettings()
    settings.pid_file_path = pid_file
    settings.kill_flag_path = kill_flag

    snap = collect_intraday_snapshot(conn, settings)
    assert snap.kill_switch_active is True
    assert snap.kill_switch_reason == "Max drawdown exceeded"


def test_collect_intraday_snapshot_no_db_data(conn, tmp_path):
    from kabusys.operations.intraday_collector import collect_intraday_snapshot

    settings = FakeSettings()
    settings.pid_file_path = tmp_path / "no.pid"
    settings.kill_flag_path = tmp_path / "no.flag"

    snap = collect_intraday_snapshot(conn, settings)
    assert snap.drawdown_pct is None
    assert snap.process_ok is True
```

- [ ] **Step 17: `collect_intraday_snapshot` を実装する**

```python
# src/kabusys/operations/intraday_collector.py に追加

def collect_intraday_snapshot(
    conn: sqlite3.Connection, settings: Settings
) -> IntradaySnapshot:
    """全チェック関数を呼び出して IntradaySnapshot を返す。"""
    now = datetime.now(timezone.utc).isoformat()

    execution_pid_ok = check_pid_file(Path(settings.pid_file_path))
    monitoring_pid_ok = check_pid_file(_MONITORING_PID)
    kill_switch_active, kill_switch_reason = check_kill_switch(
        Path(settings.kill_flag_path)
    )

    dashboard = get_dashboard_row(conn)
    drawdown_pct = dashboard["drawdown_pct"] if dashboard else None

    stale_order_count = count_recent_risk_events(conn, "STALE_ORDER")
    order_error_count = count_recent_risk_events(conn, "ORDER_ERROR")

    sys_status = get_latest_system_status(conn)
    process_ok = sys_status["process_ok"] if sys_status else True
    cpu_percent = sys_status["cpu_percent"] if sys_status else None
    memory_percent = sys_status["memory_percent"] if sys_status else None

    recent_risk_events = get_recent_risk_events(conn)

    return IntradaySnapshot(
        collected_at=now,
        execution_pid_ok=execution_pid_ok,
        monitoring_pid_ok=monitoring_pid_ok,
        kill_switch_active=kill_switch_active,
        kill_switch_reason=kill_switch_reason,
        drawdown_pct=drawdown_pct,
        stale_order_count=stale_order_count,
        order_error_count=order_error_count,
        process_ok=process_ok,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        recent_risk_events=recent_risk_events,
    )
```

- [ ] **Step 18: 全テストを通す**

```
pytest tests/test_intraday_collector.py -v
```

Expected: PASS (18 tests)

- [ ] **Step 19: ruff でフォーマット・lint を確認する**

```
ruff format src/kabusys/operations/intraday_collector.py tests/test_intraday_collector.py
ruff check src/kabusys/operations/intraday_collector.py tests/test_intraday_collector.py
```

Expected: エラーなし

- [ ] **Step 20: コミット**

```bash
git add src/kabusys/operations/intraday_collector.py tests/test_intraday_collector.py
git commit -m "feat: add intraday_collector for ザラ場中監視スナップショット収集 (Issue #203)"
```

---

### Task 2: run_monitoring.py — monitoring.pid 管理追加

**Files:**
- Modify: `src/kabusys/run_monitoring.py`
- Test: `tests/test_run_monitoring.py`（既存テストが壊れないことを確認）

- [ ] **Step 1: 既存テストを確認して baseline を記録する**

```
pytest tests/test_run_monitoring.py -v
```

Expected: 全テスト PASS（件数を記録しておく）

- [ ] **Step 2: `run_monitoring.py` に `_MONITORING_PID` 定数と PID 管理を追加する**

`src/kabusys/run_monitoring.py` の変更箇所（2箇所）:

**変更前（line 20 付近）:**
```python
_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"
```

**変更後:**
```python
_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"
_MONITORING_PID = Path(__file__).resolve().parents[2] / "data" / "monitoring.pid"
```

**変更前（`main()` 内 polling loop 開始前 — `poll_interval = _get_poll_interval()` の後）:**
```python
    poll_interval = _get_poll_interval()
    logger.info("監視ループ開始（ポーリング間隔: %d 秒）", poll_interval)
    try:
        while True:
```

**変更後:**
```python
    poll_interval = _get_poll_interval()
    logger.info("監視ループ開始（ポーリング間隔: %d 秒）", poll_interval)

    _MONITORING_PID.parent.mkdir(parents=True, exist_ok=True)
    _MONITORING_PID.write_text(str(os.getpid()))

    try:
        while True:
```

**変更前（`finally` ブロック）:**
```python
    finally:
        sqlite_conn.close()
        duckdb_conn.close()
```

**変更後:**
```python
    finally:
        sqlite_conn.close()
        duckdb_conn.close()
        _MONITORING_PID.unlink(missing_ok=True)
```

- [ ] **Step 3: 既存テストが壊れていないことを確認する**

```
pytest tests/test_run_monitoring.py -v
```

Expected: Step 1 と同じ件数が PASS

- [ ] **Step 4: ruff チェック**

```
ruff format src/kabusys/run_monitoring.py
ruff check src/kabusys/run_monitoring.py
```

Expected: エラーなし

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/run_monitoring.py
git commit -m "feat: write monitoring.pid on startup and remove on exit (Issue #203)"
```

---

### Task 3: run_intraday_monitor.py — CLI エントリーポイント

**Files:**
- Create: `src/kabusys/run_intraday_monitor.py`

- [ ] **Step 1: `run_intraday_monitor.py` の全体を実装する**

```python
# src/kabusys/run_intraday_monitor.py
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
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from kabusys.config import Settings
from kabusys.operations.intraday_collector import IntradaySnapshot, collect_intraday_snapshot

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

    # execution.pid
    if snap.execution_pid_ok:
        lines.append("    [ok  ] execution.pid    稼働中")
    else:
        lines.append("    [CRIT] execution.pid    停止（PID ファイルなし）")

    # monitoring.pid
    if snap.monitoring_pid_ok:
        lines.append("    [ok  ] monitoring.pid   稼働中")
    else:
        lines.append("    [WARN] monitoring.pid   停止（PID ファイルなし）")

    # Kill Switch
    if snap.kill_switch_active:
        lines.append(f"    [CRIT] Kill Switch      発動中: {snap.kill_switch_reason}")
    else:
        lines.append("    [ok  ] Kill Switch      発動なし")

    lines.append("----------------------------------------------------")
    lines.append("  リスク:")

    # Drawdown
    if snap.drawdown_pct is None:
        lines.append("    [ok  ] ドローダウン      データなし")
    elif snap.drawdown_pct <= -0.10:
        lines.append(
            f"    [WARN] ドローダウン      {snap.drawdown_pct * 100:.1f}%（閾値 -10% 超過）"
        )
    else:
        lines.append(f"    [ok  ] ドローダウン      {snap.drawdown_pct * 100:.1f}%")

    # Order errors
    if snap.order_error_count > 0:
        lines.append(f"    [WARN] 注文エラー        {snap.order_error_count} 件（直近1時間）")
    else:
        lines.append(f"    [ok  ] 注文エラー        {snap.order_error_count} 件（直近1時間）")

    # Stale orders
    if snap.stale_order_count > 0:
        lines.append(f"    [WARN] 滞留注文          {snap.stale_order_count} 件（直近1時間）")
    else:
        lines.append(f"    [ok  ] 滞留注文          {snap.stale_order_count} 件（直近1時間）")

    lines.append("----------------------------------------------------")
    lines.append("  システム:")

    # API / process_ok
    if snap.process_ok:
        lines.append("    [ok  ] API 接続          正常")
    else:
        lines.append("    [WARN] API 接続          異常")

    # CPU
    if snap.cpu_percent is not None:
        lines.append(f"    [ok  ] CPU               {snap.cpu_percent:.1f}%")
    else:
        lines.append("    [ok  ] CPU               データなし")

    # Memory
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
                os.system("cls")
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
```

- [ ] **Step 2: `format_cli_summary` の単体テストを追加する**

`tests/test_intraday_collector.py` の末尾に追加:

```python
# --- format_cli_summary / _determine_status ---

from kabusys.run_intraday_monitor import format_cli_summary, _determine_status
from kabusys.operations.intraday_collector import IntradaySnapshot


def _make_snap(**kwargs) -> IntradaySnapshot:
    defaults = dict(
        collected_at="2026-04-29T01:35:00+00:00",
        execution_pid_ok=True,
        monitoring_pid_ok=True,
        kill_switch_active=False,
        kill_switch_reason="",
        drawdown_pct=-0.02,
        stale_order_count=0,
        order_error_count=0,
        process_ok=True,
        cpu_percent=30.0,
        memory_percent=50.0,
        recent_risk_events=[],
    )
    defaults.update(kwargs)
    return IntradaySnapshot(**defaults)


def test_determine_status_ok():
    snap = _make_snap()
    assert _determine_status(snap) == "OK"


def test_determine_status_critical_kill_switch():
    snap = _make_snap(kill_switch_active=True, kill_switch_reason="drawdown")
    assert _determine_status(snap) == "CRITICAL"


def test_determine_status_critical_execution_down():
    snap = _make_snap(execution_pid_ok=False)
    assert _determine_status(snap) == "CRITICAL"


def test_determine_status_warning_drawdown():
    snap = _make_snap(drawdown_pct=-0.11)
    assert _determine_status(snap) == "WARNING"


def test_determine_status_warning_order_error():
    snap = _make_snap(order_error_count=2)
    assert _determine_status(snap) == "WARNING"


def test_format_cli_summary_ok_contains_ok():
    snap = _make_snap()
    output = format_cli_summary(snap)
    assert "✅ OK" in output


def test_format_cli_summary_critical_contains_crit():
    snap = _make_snap(execution_pid_ok=False)
    output = format_cli_summary(snap)
    assert "🚫 CRITICAL" in output


def test_format_cli_summary_shows_interval():
    snap = _make_snap()
    output = format_cli_summary(snap, interval=30)
    assert "30秒後" in output
```

- [ ] **Step 3: テストを通す**

```
pytest tests/test_intraday_collector.py -v -k "determine_status or format_cli"
```

Expected: PASS (8 tests)

- [ ] **Step 4: 全テストを通す**

```
pytest tests/test_intraday_collector.py -v
```

Expected: PASS (全テスト)

- [ ] **Step 5: ruff チェック**

```
ruff format src/kabusys/run_intraday_monitor.py
ruff check src/kabusys/run_intraday_monitor.py
```

Expected: エラーなし

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/run_intraday_monitor.py tests/test_intraday_collector.py
git commit -m "feat: add run_intraday_monitor CLI with --watch mode (Issue #203)"
```

---

### Task 4: streamlit_dashboard.py — Kill Switch・PID・自動更新を追加

**Files:**
- Modify: `src/kabusys/monitoring/streamlit_dashboard.py`
- Test: `tests/test_streamlit_dashboard.py`（既存テストが壊れないことを確認）

- [ ] **Step 1: 既存テストを確認する**

```
pytest tests/test_streamlit_dashboard.py -v
```

Expected: 全テスト PASS（件数を記録しておく）

- [ ] **Step 2: `streamlit_dashboard.py` を全面置換する**

以下の完全なファイル内容で置き換える:

```python
"""streamlit_dashboard.py — KabuSys 監視ダッシュボード。

起動方法:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.monitoring_db import MonitoringDB
from kabusys.operations.intraday_collector import check_pid_file, check_kill_switch


def _get_db_path() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/monitoring.db")
    args, _ = parser.parse_known_args()
    return args.db


def load_positions(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM positions WHERE qty != 0 ORDER BY updated_at DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def load_recent_orders(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM trade_logs ORDER BY logged_at DESC LIMIT ?", (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]


def load_latest_system_status(conn: sqlite3.Connection) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM system_status ORDER BY recorded_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def load_recent_risk_logs(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM risk_logs ORDER BY logged_at DESC LIMIT ?", (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]


def main(db_path: str) -> None:
    st.set_page_config(page_title="KabuSys Monitor", layout="wide")
    st.title("KabuSys 監視ダッシュボード")

    settings = Settings()

    with st.sidebar:
        if st.button("Refresh"):
            st.rerun()
        refresh_interval = st.selectbox("自動更新間隔", [30, 60, 120], index=0)
        st.caption(f"{refresh_interval}秒ごとに自動更新")

    try:
        uri = Path(db_path).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        st.error(
            f"Database not found or cannot open (read-only): {db_path}. Start MonitoringEngine first."
        )
        return
    db = MonitoringDB(conn)

    tab_overview, tab_positions, tab_orders, tab_system = st.tabs(
        ["Overview", "Positions", "Orders", "System"]
    )

    with tab_overview:
        # Kill Switch バナー
        kill_flag = Path(settings.kill_flag_path)
        kill_active, kill_reason = check_kill_switch(kill_flag)
        if kill_active:
            st.error(f"🚫 Kill Switch 発動中: {kill_reason}")
        else:
            st.success("✅ Kill Switch: 発動なし")

        dashboard = db.get_dashboard()
        if dashboard:
            col1, col2, col3 = st.columns(3)
            col1.metric("Portfolio Value", f"¥{dashboard['portfolio_value']:,.0f}")
            col2.metric("Cash", f"¥{dashboard['cash']:,.0f}")
            dd = dashboard["drawdown_pct"] * 100
            col3.metric("Drawdown", f"{dd:.2f}%", delta_color="inverse")
            if dd <= -10.0:
                st.warning(f"⚠️ ドローダウン {dd:.2f}% — 閾値 -10% 超過")
            st.caption(f"Updated: {dashboard['updated_at']}")

            # 注文エラー・滞留注文
            from datetime import datetime, timezone, timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            conn.row_factory = None
            order_error_count = conn.execute(
                "SELECT COUNT(*) FROM risk_logs WHERE event_type='ORDER_ERROR' AND logged_at > ?",
                (cutoff,),
            ).fetchone()[0]
            stale_order_count = conn.execute(
                "SELECT COUNT(*) FROM risk_logs WHERE event_type='STALE_ORDER' AND logged_at > ?",
                (cutoff,),
            ).fetchone()[0]

            col4, col5 = st.columns(2)
            col4.metric("注文エラー（直近1時間）", order_error_count)
            col5.metric("滞留注文（直近1時間）", stale_order_count)
        else:
            st.info("No dashboard data yet.")

    with tab_positions:
        positions = load_positions(conn)
        if positions:
            st.dataframe(positions, use_container_width=True)
        else:
            st.info("No open positions.")

    with tab_orders:
        orders = load_recent_orders(conn)
        if orders:
            st.dataframe(orders, use_container_width=True)
        else:
            st.info("No trade events yet.")

    with tab_system:
        # PID 状態
        exec_ok = check_pid_file(Path(settings.pid_file_path))
        mon_ok = check_pid_file(Path("data/monitoring.pid"))
        pid_col1, pid_col2 = st.columns(2)
        pid_col1.metric("Execution", "OK" if exec_ok else "DOWN")
        pid_col2.metric("Monitoring", "OK" if mon_ok else "DOWN")

        status = load_latest_system_status(conn)
        if status:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("CPU", f"{status['cpu_percent']:.1f}%")
            col2.metric("Memory", f"{status['memory_percent']:.1f}%")
            col3.metric("Disk", f"{status['disk_percent']:.1f}%")
            col4.metric("Process", "OK" if status["process_ok"] else "DOWN")
            st.caption(f"Recorded: {status['recorded_at']}")
        else:
            st.info("No system status yet.")

        risk_logs = load_recent_risk_logs(conn)
        if risk_logs:
            st.subheader("Recent Risk Events")
            st.dataframe(risk_logs, use_container_width=True)

    time.sleep(refresh_interval)
    st.rerun()


if __name__ == "__main__":
    main(_get_db_path())
```

- [ ] **Step 3: 既存テストを通す**

```
pytest tests/test_streamlit_dashboard.py -v
```

Expected: Step 1 と同じ件数が PASS

- [ ] **Step 4: 全テストが通ることを確認する**

```
pytest --tb=short -q
```

Expected: 全テスト PASS（既存テストが壊れていないこと）

- [ ] **Step 5: ruff チェック**

```
ruff format src/kabusys/monitoring/streamlit_dashboard.py
ruff check src/kabusys/monitoring/streamlit_dashboard.py
```

Expected: エラーなし

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/streamlit_dashboard.py
git commit -m "feat: enhance streamlit_dashboard with kill switch, PID status, and auto-refresh (Issue #203)"
```

---

## 完了後の確認

```
pytest --tb=short -q
```

Expected: 全テスト PASS

実動作確認（オプション）:
```
python -m kabusys.run_intraday_monitor
python -m kabusys.run_intraday_monitor --watch --interval 10
```
