# Streamlit 運用フロー拡張（Issue #260）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Streamlit ダッシュボードを 8 ページ構成に拡張し、KabuSys の日次運用フロー全体（初期構築→朝の確認→執行→ザラ場→障害対応）を UI から確認できるようにする。

**Architecture:** 新ページ用 DB クエリを `operations_data.py` に集約（`dashboard_data.py` は監視エンジン系のまま）。`validate_config.py` に `ValidationResult` + `run_checks()` を追加。既存 4 ページをリナンバリングして運用フロー順サイドバーを実現。Streamlit ページ自体のテストは行わず、データ層（`operations_data.py`・`validate_config.run_checks()`）のみ自動テスト。

**Tech Stack:** Streamlit, DuckDB (read-only), SQLite (read-only), Python dataclasses

---

## ファイル構成

**新規作成:**
- `src/kabusys/monitoring/operations_data.py`
- `src/kabusys/monitoring/pages/2_Initial_Setup.py`
- `src/kabusys/monitoring/pages/3_Pre_Market.py`
- `src/kabusys/monitoring/pages/4_Execution_Startup.py`
- `src/kabusys/monitoring/pages/5_Intraday_Monitor.py`
- `src/kabusys/monitoring/pages/8_Failure_Recovery.py`
- `tests/test_operations_data.py`

**リネーム（内容変更なし）:**
- `pages/1_WebManual.py` → `pages/9_WebManual.py`
- `pages/2_Signal_Queue.py` → `pages/6_Signal_Queue.py`
- `pages/3_Performance.py` → `pages/7_Performance.py`
- `pages/4_Strategy_Lab.py` → `pages/10_Strategy_Lab.py`

**変更:**
- `src/kabusys/validate_config.py` — `ValidationResult` dataclass + `run_checks()` 追加
- `src/kabusys/monitoring/pages/7_Performance.py` — Paper Verification タブ追加
- `src/kabusys/monitoring/streamlit_dashboard.py` — Home Overview を簡略化
- `tests/test_validate_config.py` — `run_checks()` テスト追加
- `.gitignore` — `.superpowers/` 追加

---

### Task 1: `validate_config.py` に `ValidationResult` + `run_checks()` を追加

**Files:**
- Modify: `src/kabusys/validate_config.py`
- Test: `tests/test_validate_config.py`

**背景:** `validate_config.py` にはすでに `validate() -> tuple[list, list, list]` が実装されている（line 498）。`ValidationResult` dataclass と `run_checks()` ラッパーを追加することで、Streamlit ページから型安全に呼び出せるようにする。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_validate_config.py` の末尾に追加する:

```python
class TestRunChecks:
    def test_returns_validation_result_type(self, tmp_path, monkeypatch):
        from kabusys.validate_config import ValidationResult, run_checks
        monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
        monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
        monkeypatch.setenv("KABUSYS_ENV", "development")
        monkeypatch.chdir(tmp_path)
        result = run_checks()
        assert isinstance(result, ValidationResult)

    def test_status_ok_when_no_errors_no_warnings(self, tmp_path, monkeypatch):
        from kabusys.validate_config import run_checks
        monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
        monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
        monkeypatch.setenv("KABUSYS_ENV", "development")
        monkeypatch.chdir(tmp_path)
        result = run_checks()
        assert result.status in ("OK", "WARNING")  # warnings ok, errors not

    def test_status_error_when_required_var_missing(self, monkeypatch):
        from kabusys.validate_config import run_checks
        monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
        monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
        result = run_checks()
        assert result.status == "ERROR"
        assert len(result.errors) >= 1

    def test_two_consecutive_calls_are_independent(self, monkeypatch):
        from kabusys.validate_config import run_checks
        monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
        monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
        r1 = run_checks()
        monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
        monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
        monkeypatch.setenv("KABUSYS_ENV", "development")
        r2 = run_checks()
        assert r1.status == "ERROR"
        assert r2.status in ("OK", "WARNING")
```

- [ ] **Step 2: テストを実行して失敗することを確認**

```bash
pytest tests/test_validate_config.py::TestRunChecks -v
```

Expected: `ImportError: cannot import name 'ValidationResult'`

- [ ] **Step 3: `ValidationResult` と `run_checks()` を実装する**

`src/kabusys/validate_config.py` の import セクション直下（`_PROJECT_ROOT = ...` より前）に追加:

```python
from dataclasses import dataclass
```

`_errors: list[str] = []` の手前に追加:

```python
@dataclass
class ValidationResult:
    """設定検証の結果を保持するデータクラス。"""

    errors: list[str]
    warnings: list[str]
    infos: list[str]

    @property
    def status(self) -> str:
        """OK / WARNING / ERROR を返す。"""
        if self.errors:
            return "ERROR"
        if self.warnings:
            return "WARNING"
        return "OK"
```

`validate()` 関数の直後（`main()` の前）に追加:

```python
def run_checks() -> ValidationResult:
    """全チェックを実行して ValidationResult を返す。

    validate() のラッパー。Streamlit 等から型安全に呼び出せる。
    """
    errors, warnings, infos = validate()
    return ValidationResult(errors=errors, warnings=warnings, infos=infos)
```

- [ ] **Step 4: テストを実行して合格することを確認**

```bash
pytest tests/test_validate_config.py::TestRunChecks -v
```

Expected: 4 tests PASS

- [ ] **Step 5: 全テストを実行して既存テストが壊れていないことを確認**

```bash
pytest tests/test_validate_config.py -v
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/validate_config.py tests/test_validate_config.py
git commit -m "feat: validate_config に ValidationResult + run_checks() を追加 (Issue #260)"
```

---

### Task 2: `operations_data.py` を作成する（運用系データ層）

**Files:**
- Create: `src/kabusys/monitoring/operations_data.py`
- Create: `tests/test_operations_data.py`

**背景:** 新ページ用の DB クエリ・ドメイン関数呼び出しをまとめる。`dashboard_data.py`（監視エンジン系）と責務を分離する。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_operations_data.py` を作成する:

```python
"""tests/test_operations_data.py — operations_data.py の単体テスト。"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# load_execution_startup のテスト
# ---------------------------------------------------------------------------


class TestLoadExecutionStartup:
    def test_returns_none_when_file_missing(self, tmp_path):
        from kabusys.monitoring.operations_data import load_execution_startup
        result = load_execution_startup(tmp_path / "execution_startup", target_date=date(2026, 5, 8))
        assert result is None

    def test_returns_dict_when_file_exists(self, tmp_path):
        from kabusys.monitoring.operations_data import load_execution_startup
        base = tmp_path / "execution_startup"
        day_dir = base / "2026-05-08"
        day_dir.mkdir(parents=True)
        payload = {"status": "READY", "orders_synced": 3, "orders_no_status": 0,
                   "position_discrepancies": [], "warnings": [], "generated_at": "2026-05-08T08:30:00+00:00"}
        (day_dir / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
        result = load_execution_startup(base, target_date=date(2026, 5, 8))
        assert result is not None
        assert result["status"] == "READY"
        assert result["orders_synced"] == 3

    def test_defaults_to_today_when_no_date_given(self, tmp_path):
        from kabusys.monitoring.operations_data import load_execution_startup
        base = tmp_path / "execution_startup"
        today_str = date.today().isoformat()
        day_dir = base / today_str
        day_dir.mkdir(parents=True)
        (day_dir / "summary.json").write_text(
            json.dumps({"status": "BLOCKED"}), encoding="utf-8"
        )
        result = load_execution_startup(base)
        assert result is not None
        assert result["status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# load_intraday_summary のテスト
# ---------------------------------------------------------------------------


def _make_monitoring_db(tmp_path: Path) -> sqlite3.Connection:
    """テスト用の monitoring SQLite DB を作成する。"""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE risk_logs (
            id INTEGER PRIMARY KEY,
            event_type TEXT,
            message TEXT,
            logged_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE dashboard (
            id INTEGER PRIMARY KEY,
            portfolio_value REAL,
            cash REAL,
            drawdown_pct REAL,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE trade_logs (
            id INTEGER PRIMARY KEY,
            event_type TEXT,
            message TEXT,
            logged_at TEXT
        )
    """)
    conn.commit()
    return conn


class TestLoadIntradaySummary:
    def test_returns_zeros_when_no_events(self):
        from kabusys.monitoring.operations_data import load_intraday_summary
        conn = _make_monitoring_db(None)
        result = load_intraday_summary(conn, hours=1)
        assert result["order_errors"] == 0
        assert result["stale_orders"] == 0
        assert result["drawdown_pct"] == 0.0
        conn.close()

    def test_counts_order_errors_within_window(self):
        from kabusys.monitoring.operations_data import load_intraday_summary
        conn = _make_monitoring_db(None)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO risk_logs (event_type, message, logged_at) VALUES (?, ?, ?)",
            ("ORDER_ERROR", "error", now)
        )
        conn.commit()
        result = load_intraday_summary(conn, hours=1)
        assert result["order_errors"] == 1
        conn.close()

    def test_reads_drawdown_from_dashboard(self):
        from kabusys.monitoring.operations_data import load_intraday_summary
        conn = _make_monitoring_db(None)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO dashboard (portfolio_value, cash, drawdown_pct, updated_at) VALUES (?, ?, ?, ?)",
            (1000000, 300000, -0.05, now)
        )
        conn.commit()
        result = load_intraday_summary(conn)
        assert abs(result["drawdown_pct"] - (-5.0)) < 0.01
        conn.close()


# ---------------------------------------------------------------------------
# load_failure_summary のテスト
# ---------------------------------------------------------------------------


class TestLoadFailureSummary:
    def test_returns_zero_counts_when_no_events(self):
        from kabusys.monitoring.operations_data import load_failure_summary
        conn = _make_monitoring_db(None)
        result = load_failure_summary(conn)
        assert result["critical_count"] == 0
        assert result["kill_switch_count"] == 0
        assert result["order_error_count"] == 0
        assert result["recent_events"] == []
        conn.close()

    def test_counts_critical_events_within_24h(self):
        from kabusys.monitoring.operations_data import load_failure_summary
        conn = _make_monitoring_db(None)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO risk_logs (event_type, message, logged_at) VALUES (?, ?, ?)",
            ("CRITICAL", "crit", now)
        )
        conn.execute(
            "INSERT INTO risk_logs (event_type, message, logged_at) VALUES (?, ?, ?)",
            ("KILL_SWITCH", "ks", now)
        )
        conn.commit()
        result = load_failure_summary(conn)
        assert result["critical_count"] == 1
        assert result["kill_switch_count"] == 1
        assert len(result["recent_events"]) == 2
        conn.close()


# ---------------------------------------------------------------------------
# load_paper_verification_data のテスト
# ---------------------------------------------------------------------------


class TestLoadPaperVerificationData:
    def test_returns_unavailable_when_db_missing(self, tmp_path):
        from kabusys.monitoring.operations_data import load_paper_verification_data
        result = load_paper_verification_data(tmp_path / "nonexistent.db")
        assert result["available"] is False

    def test_returns_available_with_empty_db(self, tmp_path):
        from kabusys.monitoring.operations_data import load_paper_verification_data
        db_path = tmp_path / "paper.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE system_status (
                id INTEGER PRIMARY KEY, process_ok INTEGER, recorded_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE trade_logs (
                id INTEGER PRIMARY KEY, event_type TEXT, logged_at TEXT, latency_ms REAL
            )
        """)
        conn.execute("""
            CREATE TABLE risk_logs (id INTEGER PRIMARY KEY, logged_at TEXT)
        """)
        conn.commit()
        conn.close()
        result = load_paper_verification_data(db_path)
        assert result["available"] is True
        assert result["uptime_pct"] is None  # 空DB なので None
```

- [ ] **Step 2: テストを実行して失敗することを確認**

```bash
pytest tests/test_operations_data.py -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.monitoring.operations_data'`

- [ ] **Step 3: `operations_data.py` を実装する**

`src/kabusys/monitoring/operations_data.py` を作成する:

```python
"""operations_data.py — 運用系 Streamlit ページ用のデータ取得関数。

dashboard_data.py（監視エンジン系）と責務を分離する。
Streamlit に依存しないため単体テスト可能。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def load_premarket_data(
    duckdb_conn: Any,
    sqlite_conn: sqlite3.Connection,
    settings: Any,
) -> dict:
    """pre_market_collector.collect() を呼び出し、表示用 dict を返す。

    Returns:
        {
            "status": "READY" | "READY_WITH_WARNINGS" | "BLOCKED",
            "checks": [{"name": str, "status": str, "detail": str}, ...],
            "warnings": list[str],
            "generated_at": str,
            "signal_queue_pending": int,
            "position_count": int,
            "stop_flag_exists": bool,
            "data_freshness_ok": bool,
            "task_scheduler_ready": bool,
        }
    """
    from kabusys.operations.pre_market_collector import collect
    from kabusys.operations.pre_market_report import build_report

    today = date.today()
    data = collect(
        duckdb_conn=duckdb_conn,
        sqlite_conn=sqlite_conn,
        stop_flag_path=Path(str(settings.kill_flag_path)),
        task_name="KabuSys_ExecutionStart",
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
        "checks": [
            {"name": c.name, "status": c.status, "detail": c.detail}
            for c in report.checks
        ],
        "warnings": report.warnings,
        "generated_at": report.generated_at,
        "signal_queue_pending": data.signal_queue_pending,
        "position_count": data.position_count,
        "stop_flag_exists": data.stop_flag_exists,
        "data_freshness_ok": data.data_freshness_ok,
        "task_scheduler_ready": data.task_scheduler_ready,
    }


def load_execution_startup(
    base_dir: Path,
    target_date: date | None = None,
) -> dict | None:
    """artifacts/execution_startup/{date}/summary.json を読み込む。

    ファイルが存在しない場合は None を返す。
    """
    d = target_date or date.today()
    path = base_dir / d.isoformat() / "summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_intraday_summary(
    sqlite_conn: sqlite3.Connection,
    hours: int = 1,
) -> dict:
    """risk_logs / dashboard テーブルを集計して返す。

    Returns:
        {"order_errors": int, "stale_orders": int, "drawdown_pct": float}
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    order_errors = sqlite_conn.execute(
        "SELECT COUNT(*) FROM risk_logs WHERE event_type='ORDER_ERROR' AND logged_at > ?",
        (cutoff,),
    ).fetchone()[0]

    stale_orders = sqlite_conn.execute(
        "SELECT COUNT(*) FROM risk_logs WHERE event_type='STALE_ORDER' AND logged_at > ?",
        (cutoff,),
    ).fetchone()[0]

    dashboard_row = sqlite_conn.execute(
        "SELECT drawdown_pct FROM dashboard ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    drawdown_pct = float(dashboard_row[0]) * 100 if dashboard_row else 0.0

    return {
        "order_errors": order_errors or 0,
        "stale_orders": stale_orders or 0,
        "drawdown_pct": drawdown_pct,
    }


def load_failure_summary(sqlite_conn: sqlite3.Connection) -> dict:
    """直近 24 時間の CRITICAL/KILL_SWITCH/RISK_BREACH/ORDER_ERROR イベントを集計する。

    Returns:
        {
            "critical_count": int,
            "kill_switch_count": int,
            "risk_breach_count": int,
            "order_error_count": int,
            "recent_events": list[dict],
        }
    """
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    _TYPES = ("CRITICAL", "KILL_SWITCH", "RISK_BREACH", "ORDER_ERROR")
    placeholders = ",".join("?" * len(_TYPES))

    rows = sqlite_conn.execute(
        f"""SELECT event_type, COUNT(*) FROM risk_logs
            WHERE event_type IN ({placeholders}) AND logged_at > ?
            GROUP BY event_type""",
        (*_TYPES, cutoff_24h),
    ).fetchall()
    counts = {row[0]: row[1] for row in rows}

    recent = sqlite_conn.execute(
        f"""SELECT event_type, message, logged_at FROM risk_logs
            WHERE event_type IN ({placeholders}) AND logged_at > ?
            ORDER BY logged_at DESC LIMIT 50""",
        (*_TYPES, cutoff_24h),
    ).fetchall()

    return {
        "critical_count": counts.get("CRITICAL", 0),
        "kill_switch_count": counts.get("KILL_SWITCH", 0),
        "risk_breach_count": counts.get("RISK_BREACH", 0),
        "order_error_count": counts.get("ORDER_ERROR", 0),
        "recent_events": [
            {"event_type": r[0], "message": r[1], "logged_at": r[2]}
            for r in recent
        ],
    }


def load_paper_verification_data(
    paper_sqlite_path: Path,
    from_dt: str | None = None,
    to_dt: str | None = None,
) -> dict:
    """paper_verification_report の集計ロジックを再利用して dict を返す。

    Returns:
        {"available": False} if DB does not exist, else:
        {
            "available": True,
            "uptime_pct": float | None,
            "fill_rate_pct": float | None,
            "send_rate_pct": float | None,
            "p95_latency_ms": float | None,
            "pass_fail": "PASS" | "FAIL",
            "total_polls": int,
            "created_count": int,
        }
    """
    from kabusys.tools.paper_verification_report import (
        THRESHOLD_FILL_RATE_PCT,
        THRESHOLD_P95_LATENCY_MS,
        THRESHOLD_SEND_RATE_PCT,
        THRESHOLD_UPTIME_PCT,
        _query_latency,
        _query_order_stats,
        _query_system_stability,
    )

    if not paper_sqlite_path.exists():
        return {"available": False}

    conn = sqlite3.connect(str(paper_sqlite_path))
    try:
        try:
            stability = _query_system_stability(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            stability = {"total_polls": 0, "uptime_pct": None}
        try:
            orders = _query_order_stats(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            orders = {"created_count": 0, "fill_rate_pct": None, "send_rate_pct": None}
        try:
            latency = _query_latency(conn, from_dt, to_dt)
        except sqlite3.OperationalError:
            latency = {"p95_ms": None}
    finally:
        conn.close()

    uptime = stability.get("uptime_pct")
    fill_rate = orders.get("fill_rate_pct")
    send_rate = orders.get("send_rate_pct")
    p95 = latency.get("p95_ms")

    checks = [
        uptime is not None and uptime >= THRESHOLD_UPTIME_PCT,
        fill_rate is not None and fill_rate >= THRESHOLD_FILL_RATE_PCT,
        send_rate is not None and send_rate >= THRESHOLD_SEND_RATE_PCT,
        p95 is not None and p95 <= THRESHOLD_P95_LATENCY_MS,
    ]
    pass_fail = "PASS" if all(checks) else "FAIL"

    return {
        "available": True,
        "uptime_pct": uptime,
        "fill_rate_pct": fill_rate,
        "send_rate_pct": send_rate,
        "p95_latency_ms": p95,
        "pass_fail": pass_fail,
        "total_polls": stability.get("total_polls", 0),
        "created_count": orders.get("created_count", 0),
    }
```

- [ ] **Step 4: テストを実行して合格することを確認**

```bash
pytest tests/test_operations_data.py -v
```

Expected: 10 tests PASS

- [ ] **Step 5: 全テストを実行してリグレッションがないことを確認**

```bash
pytest --tb=short -q
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/operations_data.py tests/test_operations_data.py
git commit -m "feat: operations_data.py を新設（運用系ページ用データ層）(Issue #260)"
```

---

### Task 3: ファイルリネーム + `.gitignore` 更新 + Home 簡略化

**Files:**
- Rename: `pages/1_WebManual.py` → `pages/9_WebManual.py`
- Rename: `pages/2_Signal_Queue.py` → `pages/6_Signal_Queue.py`
- Rename: `pages/3_Performance.py` → `pages/7_Performance.py`
- Rename: `pages/4_Strategy_Lab.py` → `pages/10_Strategy_Lab.py`
- Modify: `src/kabusys/monitoring/streamlit_dashboard.py`
- Modify: `.gitignore`

**背景:** `pages/` 配下のファイル名プレフィックス数字が Streamlit のサイドバー表示順を決める。運用フロー順（Initial Setup→Pre-Market→...）に合わせてリナンバリングする。

- [ ] **Step 1: 既存ページファイルをリネームする**

```bash
cd src/kabusys/monitoring/pages
git mv 1_WebManual.py 9_WebManual.py
git mv 2_Signal_Queue.py 6_Signal_Queue.py
git mv 3_Performance.py 7_Performance.py
git mv 4_Strategy_Lab.py 10_Strategy_Lab.py
```

- [ ] **Step 2: `.gitignore` に `.superpowers/` を追加する**

`.gitignore` を開き、末尾に以下を追加する:

```
# Visual companion brainstorming files
.superpowers/
```

- [ ] **Step 3: Home ページから Intraday Monitor 相当の情報を削除・リンク追加**

`src/kabusys/monitoring/streamlit_dashboard.py` の `with tab_overview:` ブロックを以下の変更を加えて編集する。

削除する部分（`tab_overview` 内から削除）:

```python
# 以下3つのブロックを削除する:
# 1. order_error_count / stale_order_count の計算（cutoff = ... から col5.metric まで）
# 2. st.divider() と st.subheader("🚨 直近の ERROR / CRITICAL イベント") のブロック全体
# 3. error_logs ローディングと dataframe 表示
```

削除した場所に追加する:

```python
st.info("📡 ザラ場監視の詳細は **Intraday Monitor** ページを確認してください。")
```

変更後の `with tab_overview:` ブロック（全体）:

```python
with tab_overview:
    # --- システム状態サマリ ---
    kill_active, kill_reason = check_kill_switch(Path(settings.kill_flag_path))
    exec_ok = check_pid_file(Path(settings.pid_file_path))
    mon_ok = check_pid_file(_MONITORING_PID)

    col_k, col_e, col_m = st.columns(3)
    if kill_active:
        col_k.error(f"🚫 Kill Switch: {kill_reason}")
    else:
        col_k.success("✅ Kill Switch: 発動なし")
    col_e.metric("Execution Engine", "🟢 UP" if exec_ok else "🔴 DOWN")
    col_m.metric("Monitoring", "🟢 UP" if mon_ok else "🔴 DOWN")

    st.divider()

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
    else:
        st.info("No dashboard data yet.")

    st.info("📡 ザラ場監視の詳細は **Intraday Monitor** ページを確認してください。")
```

- [ ] **Step 4: テストがまだ通ることを確認する**

```bash
pytest tests/test_streamlit_dashboard.py tests/test_dashboard_pages.py -v --tb=short
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/pages/ src/kabusys/monitoring/streamlit_dashboard.py .gitignore
git commit -m "refactor: Streamlit ページを運用フロー順にリナンバリング + Home 簡略化 (Issue #260)"
```

---

### Task 4: `2_Initial_Setup.py` を作成する

**Files:**
- Create: `src/kabusys/monitoring/pages/2_Initial_Setup.py`

**背景:** `validate_config.run_checks()` の結果と DB ファイルの存在・Task Scheduler の状態を Streamlit ページで表示する。Streamlit ページ自体のテストは書かない（データ層は Task 1・2 でカバー済み）。

- [ ] **Step 1: `2_Initial_Setup.py` を作成する**

`src/kabusys/monitoring/pages/2_Initial_Setup.py`:

```python
"""pages/2_Initial_Setup.py — 環境設定・DB・Task Scheduler 確認ページ。"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.operations.pre_market_collector import check_task_scheduler
from kabusys.validate_config import run_checks

st.set_page_config(page_title="Initial Setup", layout="wide", page_icon="⚙️")
st.title("⚙️ Initial Setup — 環境確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    result = run_checks()
except Exception as e:
    st.error(f"設定検証の実行に失敗しました: {e}")
    st.stop()

if result.status == "OK":
    st.success("✅ OK — すべての設定が正常です")
elif result.status == "WARNING":
    st.warning(f"⚠️ WARNING — 警告 {len(result.warnings)} 件")
else:
    st.error(f"🚫 ERROR — エラー {len(result.errors)} 件")

tab_env, tab_yaml, tab_db, tab_scheduler = st.tabs(
    ["環境変数", "設定ファイル", "DB ファイル", "Task Scheduler"]
)

_REQUIRED = {"JQUANTS_REFRESH_TOKEN", "KABU_API_PASSWORD"}
_OPTIONAL = {
    "KABUSYS_ENV", "DUCKDB_PATH", "SQLITE_PATH", "LOG_LEVEL",
    "KABU_API_BASE_URL", "LINE_CHANNEL_ACCESS_TOKEN", "LINE_USER_ID",
    "ENABLE_YAHOONEWS", "KABU_USE_SANDBOX", "KABU_SANDBOX_API_PASSWORD",
    "PAPER_TRADING_INITIAL_CASH",
}

with tab_env:
    st.subheader("必須環境変数")
    for var in sorted(_REQUIRED):
        if os.environ.get(var, ""):
            st.success(f"✅ {var}: 設定済み")
        else:
            st.error(f"❌ {var}: 未設定")
    st.subheader("オプション環境変数")
    for var in sorted(_OPTIONAL):
        if os.environ.get(var, ""):
            st.info(f"✅ {var}: 設定済み")
        else:
            st.caption(f"　{var}: 未設定（デフォルト値を使用）")

_CONFIG_FILES = [
    "system_config.yaml", "data_config.yaml", "strategy_config.yaml",
    "risk_config.yaml", "execution_config.yaml", "monitoring_config.yaml",
]

with tab_yaml:
    st.subheader("設定ファイル (config/*.yaml)")
    for f in _CONFIG_FILES:
        if (Path("config") / f).exists():
            st.success(f"✅ {f}")
        else:
            st.warning(f"⚠️ {f}: 見つかりません（python scripts/generate_config.py で生成）")
    if result.errors or result.warnings:
        st.divider()
        for msg in result.errors:
            st.error(msg)
        for msg in result.warnings:
            st.warning(msg)

with tab_db:
    st.subheader("DB ファイル")
    _db_checks = [
        (Path(str(settings.duckdb_path)), "DuckDB (kabusys.duckdb)", True),
        (Path(str(settings.sqlite_path)), "SQLite monitoring (monitoring.db)", False),
        (Path(str(settings.paper_trading_sqlite_path)), "SQLite paper (paper_trading.db)", False),
    ]
    for p, label, required in _db_checks:
        if p.exists():
            size_kb = p.stat().st_size // 1024
            st.success(f"✅ {label}: {size_kb} KB")
        elif required:
            st.error(f"❌ {label}: 見つかりません")
        else:
            st.warning(f"⚠️ {label}: 見つかりません（paper_trading 環境以外は不要な場合あり）")

with tab_scheduler:
    st.subheader("Task Scheduler")
    try:
        ready = check_task_scheduler("KabuSys_ExecutionStart")
        if ready:
            st.success("✅ KabuSys_ExecutionStart: Ready")
        else:
            st.error("❌ KabuSys_ExecutionStart: Ready ではありません（要確認）")
    except Exception as e:
        st.warning(f"Task Scheduler の確認に失敗しました（Windows 環境外では利用不可）: {e}")
```

- [ ] **Step 2: Streamlit の構文エラーがないことを確認**

```bash
python -c "import ast; ast.parse(open('src/kabusys/monitoring/pages/2_Initial_Setup.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/monitoring/pages/2_Initial_Setup.py
git commit -m "feat: 2_Initial_Setup ページを追加 (Issue #260)"
```

---

### Task 5: `3_Pre_Market.py` を作成する

**Files:**
- Create: `src/kabusys/monitoring/pages/3_Pre_Market.py`

- [ ] **Step 1: `3_Pre_Market.py` を作成する**

```python
"""pages/3_Pre_Market.py — 朝の READY/BLOCKED 判定ページ。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.operations_data import load_premarket_data
from kabusys.operations.pre_market_report import (
    STATUS_BLOCKED,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
)

st.set_page_config(page_title="Pre-Market", layout="wide", page_icon="🌅")
st.title("🌅 Pre-Market — 朝の確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
except Exception as e:
    st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    uri = Path(str(settings.sqlite_path)).resolve().as_uri() + "?mode=ro"
    sqlite_conn = sqlite3.connect(uri, uri=True)
except Exception as e:
    st.error(f"SQLite 接続失敗: {e}")
    duckdb_conn.close()
    st.stop()

try:
    result = load_premarket_data(duckdb_conn, sqlite_conn, settings)
except Exception as e:
    st.error(f"データ取得失敗: {e}")
    st.exception(e)
    duckdb_conn.close()
    sqlite_conn.close()
    st.stop()

status = result["status"]
if status == STATUS_READY:
    st.success("✅ READY — 執行開始可能")
elif status == STATUS_READY_WITH_WARNINGS:
    st.warning("⚠️ READY_WITH_WARNINGS — 警告を確認してください")
else:
    st.error("🚫 BLOCKED — 自動執行を開始しないでください")

st.divider()

checks = {c["name"]: c for c in result["checks"]}

def _icon(chk_status: str) -> str:
    return "✅" if chk_status == "ok" else ("⚠️" if chk_status == "warning" else "❌")

col1, col2, col3 = st.columns(3)
with col1:
    c = checks.get("data_freshness", {})
    st.metric("データ鮮度", f"{_icon(c.get('status','failed'))} {'OK' if c.get('status') == 'ok' else '古い'}")
with col2:
    c = checks.get("signal_queue", {})
    st.metric("Signal Queue", f"{_icon(c.get('status','failed'))} pending {result['signal_queue_pending']}件")
with col3:
    c = checks.get("task_scheduler", {})
    st.metric("Task Scheduler", f"{_icon(c.get('status','failed'))} {'Ready' if c.get('status') == 'ok' else 'NG'}")

col4, col5, col6 = st.columns(3)
with col4:
    c = checks.get("stop_flag", {})
    st.metric("停止フラグ", f"{_icon(c.get('status','ok'))} {'あり' if result['stop_flag_exists'] else 'なし'}")
with col5:
    st.metric("保有ポジション", f"📊 {result['position_count']}銘柄")
with col6:
    st.caption(f"生成: {result['generated_at']}")

if result["warnings"]:
    st.divider()
    st.subheader("⚠️ Warnings")
    for w in result["warnings"]:
        st.warning(w)

duckdb_conn.close()
sqlite_conn.close()
```

- [ ] **Step 2: 構文チェック**

```bash
python -c "import ast; ast.parse(open('src/kabusys/monitoring/pages/3_Pre_Market.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/monitoring/pages/3_Pre_Market.py
git commit -m "feat: 3_Pre_Market ページを追加 (Issue #260)"
```

---

### Task 6: `4_Execution_Startup.py` を作成する

**Files:**
- Create: `src/kabusys/monitoring/pages/4_Execution_Startup.py`

- [ ] **Step 1: `4_Execution_Startup.py` を作成する**

```python
"""pages/4_Execution_Startup.py — 起動直後の差分確認ページ。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.operations_data import load_execution_startup
from kabusys.operations.execution_startup_report import (
    STATUS_BLOCKED,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
)

st.set_page_config(page_title="Execution Startup", layout="wide", page_icon="🚀")
st.title("🚀 Execution Startup — 起動確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    selected_date = st.date_input("対象日", value=date.today())
    if st.button("🔄 Refresh"):
        st.rerun()

base_dir = Path("artifacts/execution_startup")
report_data = load_execution_startup(base_dir, target_date=selected_date)

if report_data is None:
    st.info(f"📋 {selected_date} の Execution はまだ起動していません。")
    st.caption("Execution を起動すると `artifacts/execution_startup/{date}/summary.json` が自動生成されます。")
    st.stop()

status = report_data.get("status", "BLOCKED")
if status == STATUS_READY:
    st.success("✅ READY — 執行開始可能")
elif status == STATUS_READY_WITH_WARNINGS:
    st.warning("⚠️ READY_WITH_WARNINGS — ポジション差分あり。確認してください")
else:
    st.error("🚫 BLOCKED — ステータス不明注文あり。手動確認が必要です")

st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("注文同期数", report_data.get("orders_synced", 0))
col2.metric("ステータス不明注文", report_data.get("orders_no_status", 0))
col3.metric("ポジション差分件数", len(report_data.get("position_discrepancies", [])))

discrepancies = report_data.get("position_discrepancies", [])
if discrepancies:
    st.subheader("ポジション差分")
    st.dataframe(discrepancies, use_container_width=True)

warnings = report_data.get("warnings", [])
if warnings:
    st.divider()
    st.subheader("⚠️ Warnings")
    for w in warnings:
        st.warning(w)

st.caption(f"生成: {report_data.get('generated_at', 'N/A')}")
```

- [ ] **Step 2: 構文チェック**

```bash
python -c "import ast; ast.parse(open('src/kabusys/monitoring/pages/4_Execution_Startup.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/monitoring/pages/4_Execution_Startup.py
git commit -m "feat: 4_Execution_Startup ページを追加 (Issue #260)"
```

---

### Task 7: `5_Intraday_Monitor.py` を作成する

**Files:**
- Create: `src/kabusys/monitoring/pages/5_Intraday_Monitor.py`

- [ ] **Step 1: `5_Intraday_Monitor.py` を作成する**

```python
"""pages/5_Intraday_Monitor.py — ザラ場監視ページ（自動更新付き）。"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.operations_data import load_intraday_summary
from kabusys.operations.intraday_collector import (
    _MONITORING_PID,
    check_kill_switch,
    check_pid_file,
)

st.set_page_config(page_title="Intraday Monitor", layout="wide", page_icon="📡")
st.title("📡 Intraday Monitor — ザラ場監視")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    refresh_interval = st.selectbox("自動更新間隔（秒）", [30, 60, 120], index=0)
    if st.button("🔄 今すぐ更新"):
        st.rerun()

try:
    uri = Path(str(settings.sqlite_path)).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
except sqlite3.OperationalError:
    st.error(
        f"Database not found or cannot open: {settings.sqlite_path}. "
        "Start MonitoringEngine first."
    )
    st.stop()

try:
    kill_active, kill_reason = check_kill_switch(Path(settings.kill_flag_path))
    exec_ok = check_pid_file(Path(settings.pid_file_path))
    mon_ok = check_pid_file(_MONITORING_PID)

    col_k, col_e, col_m = st.columns(3)
    if kill_active:
        col_k.error(f"🚫 Kill Switch: {kill_reason}")
    else:
        col_k.success("✅ Kill Switch: 発動なし")
    col_e.metric("Execution Engine", "🟢 UP" if exec_ok else "🔴 DOWN")
    col_m.metric("Monitoring", "🟢 UP" if mon_ok else "🔴 DOWN")

    st.divider()

    summary = load_intraday_summary(conn, hours=1)
    col1, col2, col3 = st.columns(3)
    dd = summary["drawdown_pct"]
    col1.metric("ドローダウン", f"{dd:.2f}%", delta_color="inverse")
    col2.metric("注文エラー（直近1h）", summary["order_errors"])
    col3.metric("滞留注文（直近1h）", summary["stale_orders"])

    if dd <= -10.0:
        st.warning(f"⚠️ ドローダウン {dd:.2f}% — 閾値 -10% 超過")

    st.divider()

    tab_risk, tab_trade = st.tabs(["Risk Logs", "Trade Logs"])

    with tab_risk:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_type, message, logged_at FROM risk_logs "
            "ORDER BY logged_at DESC LIMIT 50"
        ).fetchall()
        if rows:
            st.dataframe([dict(r) for r in rows], use_container_width=True)
        else:
            st.success("リスクイベントはありません。")
        conn.row_factory = None

    with tab_trade:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_type, message, logged_at FROM trade_logs "
            "ORDER BY logged_at DESC LIMIT 50"
        ).fetchall()
        if rows:
            st.dataframe([dict(r) for r in rows], use_container_width=True)
        else:
            st.info("取引ログはありません。")
        conn.row_factory = None

    time.sleep(refresh_interval)
    st.rerun()

finally:
    conn.close()
```

- [ ] **Step 2: 構文チェック**

```bash
python -c "import ast; ast.parse(open('src/kabusys/monitoring/pages/5_Intraday_Monitor.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/monitoring/pages/5_Intraday_Monitor.py
git commit -m "feat: 5_Intraday_Monitor ページを追加（自動更新付き）(Issue #260)"
```

---

### Task 8: `8_Failure_Recovery.py` を作成する

**Files:**
- Create: `src/kabusys/monitoring/pages/8_Failure_Recovery.py`

- [ ] **Step 1: `8_Failure_Recovery.py` を作成する**

```python
"""pages/8_Failure_Recovery.py — 障害対応集約ビュー。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.operations_data import load_failure_summary
from kabusys.operations.intraday_collector import (
    _MONITORING_PID,
    check_kill_switch,
    check_pid_file,
)

st.set_page_config(page_title="Failure Recovery", layout="wide", page_icon="🚨")
st.title("🚨 Failure Recovery — 障害対応")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    uri = Path(str(settings.sqlite_path)).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
except sqlite3.OperationalError:
    st.error(f"Database not found: {settings.sqlite_path}. Start MonitoringEngine first.")
    st.stop()

try:
    kill_active, kill_reason = check_kill_switch(Path(settings.kill_flag_path))
    exec_ok = check_pid_file(Path(settings.pid_file_path))
    mon_ok = check_pid_file(_MONITORING_PID)

    if kill_active:
        st.error(f"🚫 Kill Switch 発動中: {kill_reason}")
    else:
        st.success("✅ Kill Switch: 発動なし")

    col1, col2 = st.columns(2)
    col1.metric("Execution Engine", "🟢 UP" if exec_ok else "🔴 DOWN")
    col2.metric("Monitoring", "🟢 UP" if mon_ok else "🔴 DOWN")

    st.divider()

    summary = load_failure_summary(conn)
    col3, col4, col5, col6 = st.columns(4)
    col3.metric("CRITICAL（直近24h）", summary["critical_count"])
    col4.metric("KILL_SWITCH（直近24h）", summary["kill_switch_count"])
    col5.metric("RISK_BREACH（直近24h）", summary["risk_breach_count"])
    col6.metric("ORDER_ERROR（直近24h）", summary["order_error_count"])

    st.subheader("直近イベント（直近24時間）")
    events = summary["recent_events"]
    if events:
        st.dataframe(events, use_container_width=True)
    else:
        st.success("直近24時間の障害イベントはありません。")

    st.divider()
    st.subheader("🔗 復旧手順ガイド")
    st.markdown("""
| 状況 | 参照先 |
|------|--------|
| Kill Switch が発動した | WebManual → Failure Recovery を参照 |
| 注文エラーが多い | `documents/08_Operations/TradingRunbook.md` を参照 |
| ポジション差分あり | Execution Startup ページで詳細確認 → `python -m kabusys.run_position_reconciliation_report` |
| データ更新失敗 | Pre-Market ページでデータ鮮度確認 → `python scripts/run_data_update.py` |
""")

finally:
    conn.close()
```

- [ ] **Step 2: 構文チェック**

```bash
python -c "import ast; ast.parse(open('src/kabusys/monitoring/pages/8_Failure_Recovery.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/monitoring/pages/8_Failure_Recovery.py
git commit -m "feat: 8_Failure_Recovery ページを追加 (Issue #260)"
```

---

### Task 9: `7_Performance.py` に Paper Verification タブを追加する

**Files:**
- Modify: `src/kabusys/monitoring/pages/7_Performance.py`（Task 3 でリネーム済み）

**背景:** 既存の Performance ページ（旧 `3_Performance.py`、Task 3 でリネーム）に Paper Verification タブを追加する。`KABUSYS_ENV != "paper_trading"` の場合は案内メッセージのみ表示する。

- [ ] **Step 1: `7_Performance.py` の import と接続部分を確認する**

```bash
head -30 src/kabusys/monitoring/pages/7_Performance.py
```

現在の先頭部分（Task 3 リネーム後、内容は変更なし）:
```python
"""pages/3_Performance.py — 運用成績・ポジション・取引履歴ビュー。"""
import duckdb
import pandas as pd
import streamlit as st
from kabusys.config import Settings
from kabusys.monitoring.dashboard_data import (
    load_open_positions, load_portfolio_performance, load_recent_trades,
)
```

- [ ] **Step 2: import を更新してタブを追加する**

`src/kabusys/monitoring/pages/7_Performance.py` を以下の内容で上書きする。変更点は:
1. docstring を更新
2. `load_paper_verification_data` を import 追加
3. `datetime` を import 追加
4. `tab_perf, tab_pos, tab_trades` を `tab_perf, tab_pos, tab_trades, tab_paper` に変更
5. `tab_paper` ブロックを追加

```python
"""pages/7_Performance.py — 運用成績・ポジション・取引履歴・Paper Verification ビュー。"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.dashboard_data import (
    load_open_positions,
    load_portfolio_performance,
    load_recent_trades,
)
from kabusys.monitoring.operations_data import load_paper_verification_data

st.set_page_config(page_title="Performance", layout="wide", page_icon="📈")
st.title("📈 Performance — 運用成績")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    days = st.selectbox("表示期間", [30, 60, 90, 180], index=2)
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
except Exception as e:
    st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    tab_perf, tab_pos, tab_trades, tab_paper = st.tabs(
        ["エクイティカーブ", "ポジション", "取引履歴", "Paper Verification"]
    )

    with tab_perf:
        df = load_portfolio_performance(conn, env=settings.env, days=days)
        if df.empty:
            st.info("パフォーマンスデータがありません。")
        else:
            latest = df.iloc[-1]
            col1, col2, col3 = st.columns(3)
            col1.metric("Equity", f"¥{float(latest['equity']):,.0f}")
            col2.metric("Cash", f"¥{float(latest['cash']):,.0f}")
            dd_val = latest.get("drawdown")
            dd = 0.0 if pd.isna(dd_val) else float(dd_val) * 100
            col3.metric("Drawdown", f"{dd:.2f}%")

            st.subheader("エクイティカーブ")
            st.line_chart(df.set_index("date")["equity"])

            ret_df = df.set_index("date")["daily_return"].dropna()
            if not ret_df.empty:
                st.subheader("日次リターン (%)")
                st.bar_chart(ret_df * 100)

            dd_df = df.set_index("date")["drawdown"].dropna() * 100
            if not dd_df.empty:
                st.subheader("ドローダウン推移 (%)")
                st.line_chart(dd_df)

    with tab_pos:
        st.subheader("保有ポジション（最新日）")
        df = load_open_positions(conn)
        if df.empty:
            st.info("保有ポジションはありません。")
        else:
            st.caption(f"基準日: {df['date'].iloc[0]}")
            total_mv = float(
                pd.to_numeric(df["market_value"], errors="coerce").fillna(0).sum()
            )
            st.metric("時価総額合計", f"¥{total_mv:,.0f}")
            st.dataframe(df, use_container_width=True)

    with tab_trades:
        st.subheader("直近50件の取引履歴")
        df = load_recent_trades(conn)
        if df.empty:
            st.info("取引履歴がありません。")
        else:
            st.dataframe(df, use_container_width=True)

    with tab_paper:
        st.subheader("Paper Verification")
        if settings.env != "paper_trading":
            st.info(
                "📋 Paper Verification は `KABUSYS_ENV=paper_trading` 環境でのみ表示されます。"
            )
        else:
            col_from, col_to = st.columns(2)
            with col_from:
                from_date = st.date_input("開始日", value=date.today() - timedelta(days=30))
            with col_to:
                to_date = st.date_input("終了日", value=date.today())

            from_dt = f"{from_date}T00:00:00+00:00"
            to_dt = f"{to_date}T23:59:59.999999+00:00"

            paper_path = Path(str(settings.paper_trading_sqlite_path))
            data = load_paper_verification_data(paper_path, from_dt=from_dt, to_dt=to_dt)

            if not data.get("available"):
                st.warning(
                    f"Paper Trading DB が見つかりません: {paper_path}\n"
                    "Paper Trading を起動して実行してください。"
                )
            else:
                if data["pass_fail"] == "PASS":
                    st.success("✅ PASS — すべての閾値をクリア")
                else:
                    st.error("❌ FAIL — 一部の指標が閾値未達")

                col1, col2, col3, col4 = st.columns(4)
                uptime = data["uptime_pct"]
                fill = data["fill_rate_pct"]
                send = data["send_rate_pct"]
                p95 = data["p95_latency_ms"]

                col1.metric(
                    "稼働率",
                    f"{uptime:.1f}%" if uptime is not None else "N/A",
                    help="閾値: ≥99%",
                )
                col2.metric(
                    "約定率",
                    f"{fill:.1f}%" if fill is not None else "N/A",
                    help="閾値: ≥90%",
                )
                col3.metric(
                    "送信率",
                    f"{send:.1f}%" if send is not None else "N/A",
                    help="閾値: ≥95%",
                )
                col4.metric(
                    "P95 レイテンシ",
                    f"{p95:.0f} ms" if p95 is not None else "N/A",
                    help="閾値: ≤200ms",
                )

                st.caption(
                    f"集計対象: {from_date} ～ {to_date} / "
                    f"総ポーリング数: {data['total_polls']} / "
                    f"注文数: {data['created_count']}"
                )

finally:
    conn.close()
```

- [ ] **Step 3: 構文チェック**

```bash
python -c "import ast; ast.parse(open('src/kabusys/monitoring/pages/7_Performance.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 全テストを実行する**

```bash
pytest --tb=short -q
```

Expected: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/pages/7_Performance.py
git commit -m "feat: 7_Performance ページに Paper Verification タブを追加 (Issue #260)"
```

---

## 完了確認

全タスク完了後、以下で動作確認する:

```bash
# 1. テスト全通過
pytest --tb=short -q

# 2. Streamlit を起動して 8 ページが表示されること
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

サイドバーに以下の順番で表示されることを確認する:
- 🏠 Home
- ⚙️ 2 Initial Setup
- 🌅 3 Pre Market
- 🚀 4 Execution Startup
- 📡 5 Intraday Monitor
- 📋 6 Signal Queue
- 📈 7 Performance
- 🚨 8 Failure Recovery
- 📖 9 WebManual
- 🔬 10 Strategy Lab
