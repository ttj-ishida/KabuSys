# Phase 7 監視エンジン + Streamlit ダッシュボード 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / StreamlitDashboard を実装し、Issue #38 と #35 を完了させる。

**Architecture:** 各 Monitor は `check_once()` のみを持つ純粋なチェッカーとして実装し、`MonitoringEngine` が 60 秒間隔でポーリングを管理する。Streamlit ダッシュボードは `MonitoringEngine` と独立して `monitoring.db` を直接読み取る。

**Tech Stack:** Python 3.10+, psutil, streamlit, sqlite3 (monitoring.db), duckdb (data freshness check), existing `MonitoringDB` / `OrderRepository`

---

## ファイル構成

| ファイル | 変更種別 | 責務 |
|---|---|---|
| `src/kabusys/monitoring/system_monitor.py` | 新規 | CPU/メモリ/ディスク/プロセス生存/データ鮮度チェック |
| `src/kabusys/monitoring/trade_monitor.py` | 新規 | 注文滞留・約定異常価格検出 |
| `src/kabusys/monitoring/risk_monitor.py` | 新規 | ドローダウン・ポジション上限監視 |
| `src/kabusys/monitoring/monitoring_engine.py` | 新規 | ポーリング統括（60秒間隔） |
| `src/kabusys/monitoring/streamlit_dashboard.py` | 新規 | 4タブ Streamlit 監視 UI |
| `src/kabusys/monitoring/__init__.py` | 更新 | 新クラスをエクスポート |
| `tests/test_monitoring_engine.py` | 新規 | Task 1〜4 のテスト |
| `tests/test_streamlit_dashboard.py` | 新規 | Task 5 のテスト |
| `requirements.txt` | 更新 | psutil, streamlit を追加 |

---

## Task 1: psutil / streamlit を requirements.txt に追加

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: requirements.txt に依存を追加**

`requirements.txt` の末尾に追記する:

```
psutil>=5.9,<7
streamlit>=1.32,<2
```

- [ ] **Step 2: インストール確認**

```bash
pip install -r requirements.txt
python -c "import psutil, streamlit; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add requirements.txt
git commit -m "chore: add psutil and streamlit dependencies"
```

---

## Task 2: SystemMonitor 実装

**Files:**
- Create: `src/kabusys/monitoring/system_monitor.py`
- Create (テスト追記): `tests/test_monitoring_engine.py`

### 2-A: テストを書く

- [ ] **Step 1: テストファイルを作成**

`tests/test_monitoring_engine.py` を作成:

```python
"""tests/test_monitoring_engine.py — Phase 7 監視エンジン テスト"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def mon_conn():
    """インメモリ monitoring.db。"""
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    return conn


@pytest.fixture
def mock_duckdb():
    return MagicMock()


# ─── SystemMonitor ────────────────────────────────────────────────────────────

def _make_psutil_mocks():
    """psutil の cpu/mem/disk を固定値でモックするパッチ群を返す。"""
    return [
        patch("psutil.cpu_percent", return_value=30.0),
        patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)),
        patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)),
    ]


def test_system_monitor_no_pid_file(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルなし → process_ok=False, stale_pid_detected=False"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=date.today())
        finally:
            for p in patches:
                p.stop()

    assert result.process_ok is False
    assert result.stale_pid_detected is False


def test_system_monitor_pid_alive(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルあり + プロセス生存 → process_ok=True, stale_pid_detected=False"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    pid_file = tmp_path / "execution.pid"
    pid_file.write_text("12345")
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()), \
         patch("psutil.pid_exists", return_value=True):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=date.today())
        finally:
            for p in patches:
                p.stop()

    assert result.process_ok is True
    assert result.stale_pid_detected is False
    assert pid_file.exists()  # ファイルは残る


def test_system_monitor_stale_pid(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルあり + プロセス死亡 → stale_pid_detected=True, ファイル削除, risk_log記録"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    pid_file = tmp_path / "execution.pid"
    pid_file.write_text("12345")
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()), \
         patch("psutil.pid_exists", return_value=False):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=date.today())
        finally:
            for p in patches:
                p.stop()

    assert result.process_ok is False
    assert result.stale_pid_detected is True
    assert not pid_file.exists()  # ファイルが削除される

    # risk_logs に STALE_PID が記録されているか確認
    mon_conn.row_factory = sqlite3.Row
    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='STALE_PID'").fetchall()
    assert len(rows) == 1


def test_system_monitor_data_freshness_ok(mon_conn, mock_duckdb, tmp_path):
    """株価データが 2 日前 → data_freshness_ok=True"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    today = date(2026, 4, 1)
    last_price = date(2026, 3, 30)  # 2日前
    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=last_price):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=today)
        finally:
            for p in patches:
                p.stop()

    assert result.data_freshness_ok is True


def test_system_monitor_data_freshness_ng(mon_conn, mock_duckdb, tmp_path):
    """株価データが 4 日前 → data_freshness_ok=False"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    today = date(2026, 4, 1)
    last_price = date(2026, 3, 28)  # 4日前
    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=last_price):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=today)
        finally:
            for p in patches:
                p.stop()

    assert result.data_freshness_ok is False


def test_system_monitor_data_freshness_none(mon_conn, mock_duckdb, tmp_path):
    """get_last_price_date が None（空 DuckDB）→ data_freshness_ok=False"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=None):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=date.today())
        finally:
            for p in patches:
                p.stop()

    assert result.data_freshness_ok is False
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_monitoring_engine.py -k "system_monitor" -v
```

Expected: `ImportError` or `ModuleNotFoundError`（system_monitor.py 未作成のため）

### 2-B: 実装する

- [ ] **Step 3: system_monitor.py を作成**

`src/kabusys/monitoring/system_monitor.py`:

```python
"""system_monitor.py — システム状態・データ鮮度を監視する。"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import psutil

from kabusys.data.pipeline import get_last_price_date
from kabusys.monitoring.monitoring_db import MonitoringDB

_FRESHNESS_DAYS = 3


@dataclass
class SystemCheckResult:
    recorded_at: str          # ISO8601 UTC
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    process_ok: bool
    data_freshness_ok: bool
    stale_pid_detected: bool


class SystemMonitor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        duckdb_conn: duckdb.DuckDBPyConnection,
        pid_file: Path = Path("data/execution.pid"),
        disk_path: str = "C:\\",
    ) -> None:
        self._db = MonitoringDB(conn)
        self._duckdb_conn = duckdb_conn
        self._pid_file = pid_file
        self._disk_path = disk_path

    def check_once(self, today: date | None = None) -> SystemCheckResult:
        today = today or date.today()
        recorded_at = datetime.now(timezone.utc).isoformat()

        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage(self._disk_path).percent

        process_ok, stale_pid = self._check_process()
        data_ok = self._check_data_freshness(today)

        self._db.log_system_status(
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
        )

        if stale_pid:
            self._db.log_risk_event(
                event_type="STALE_PID",
                metric_name="process",
                metric_value=0.0,
                threshold=1.0,
                detail="stale PID file detected and removed",
            )

        return SystemCheckResult(
            recorded_at=recorded_at,
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
            data_freshness_ok=data_ok,
            stale_pid_detected=stale_pid,
        )

    def _check_process(self) -> tuple[bool, bool]:
        """(process_ok, stale_pid_detected) を返す。"""
        if not self._pid_file.exists():
            return False, False
        try:
            pid = int(self._pid_file.read_text().strip())
        except (ValueError, OSError):
            return False, False
        if psutil.pid_exists(pid):
            return True, False
        # stale PID — 削除してアラート
        self._pid_file.unlink(missing_ok=True)
        return False, True

    def _check_data_freshness(self, today: date) -> bool:
        last = get_last_price_date(self._duckdb_conn)
        if last is None:
            return False
        return (today - last).days <= _FRESHNESS_DAYS
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
pytest tests/test_monitoring_engine.py -k "system_monitor" -v
```

Expected: 6 PASS

- [ ] **Step 5: 全テストが壊れていないことを確認**

```bash
pytest --tb=short -q
```

Expected: 502 passed (新規6テスト追加で 508 passed)

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/system_monitor.py tests/test_monitoring_engine.py
git commit -m "feat: add SystemMonitor with psutil/PID/data-freshness checks (Issue #38)"
```

---

## Task 3: TradeMonitor 実装

**Files:**
- Create: `src/kabusys/monitoring/trade_monitor.py`
- Modify: `tests/test_monitoring_engine.py` (テスト追記)

### 3-A: テストを書く

- [ ] **Step 1: テストを test_monitoring_engine.py に追記**

`tests/test_monitoring_engine.py` の末尾に追加:

```python
# ─── TradeMonitor ─────────────────────────────────────────────────────────────

from kabusys.execution.order_record import OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository
import uuid


def _make_order(
    *,
    state: OrderState = OrderState.OrderCreated,
    price: float = 1000.0,
    avg_fill_price: float | None = None,
    created_at: datetime | None = None,
    order_type: str = "limit",
) -> OrderRecord:
    """テスト用 OrderRecord ファクトリ。"""
    return OrderRecord(
        client_order_id=str(uuid.uuid4()),
        signal_id=str(uuid.uuid4()),
        code="7203",
        side="buy",
        qty=100,
        order_type=order_type,
        price=price,
        state=state,
        created_at=created_at or datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        avg_fill_price=avg_fill_price,
    )


def test_trade_monitor_no_active_orders(mon_conn):
    """アクティブ注文なし → stale_orders/anomaly_fills ともに空"""
    from kabusys.monitoring.trade_monitor import TradeMonitor

    repo = MagicMock()
    repo.list_active.return_value = []
    monitor = TradeMonitor(mon_conn, repo)

    result = monitor.check_once()

    assert result.stale_orders == []
    assert result.anomaly_fills == []


def test_trade_monitor_fresh_order_not_stale(mon_conn):
    """作成5分後の注文 → stale 判定なし"""
    from kabusys.monitoring.trade_monitor import TradeMonitor

    now = datetime(2026, 4, 1, 9, 0, 0, tzinfo=timezone.utc)
    order = _make_order(
        state=OrderState.OrderAccepted,
        created_at=now - timedelta(minutes=5),
    )
    repo = MagicMock()
    repo.list_active.return_value = [order]
    monitor = TradeMonitor(mon_conn, repo, stale_minutes=30)

    result = monitor.check_once(now=now)

    assert result.stale_orders == []


def test_trade_monitor_stale_order_detected(mon_conn):
    """作成31分後の注文 → stale_orders に追加, risk_log 記録"""
    from kabusys.monitoring.trade_monitor import TradeMonitor

    now = datetime(2026, 4, 1, 9, 31, 0, tzinfo=timezone.utc)
    order = _make_order(
        state=OrderState.OrderAccepted,
        created_at=datetime(2026, 4, 1, 9, 0, 0, tzinfo=timezone.utc),
    )
    repo = MagicMock()
    repo.list_active.return_value = [order]
    monitor = TradeMonitor(mon_conn, repo, stale_minutes=30)

    result = monitor.check_once(now=now)

    assert order.client_order_id in result.stale_orders
    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='STALE_ORDER'").fetchall()
    assert len(rows) == 1


def test_trade_monitor_normal_fill_no_anomaly(mon_conn):
    """約定価格が発注価格の 5% 乖離 → anomaly なし"""
    from kabusys.monitoring.trade_monitor import TradeMonitor

    order = _make_order(
        state=OrderState.Filled,
        price=1000.0,
        avg_fill_price=1050.0,  # 5% 乖離
    )
    repo = MagicMock()
    repo.list_active.return_value = [order]
    monitor = TradeMonitor(mon_conn, repo, price_anomaly_pct=0.20)

    result = monitor.check_once()

    assert result.anomaly_fills == []


def test_trade_monitor_price_anomaly_detected(mon_conn):
    """約定価格が発注価格の 25% 乖離 → anomaly_fills に追加"""
    from kabusys.monitoring.trade_monitor import TradeMonitor

    order = _make_order(
        state=OrderState.Filled,
        price=1000.0,
        avg_fill_price=1300.0,  # 30% 乖離
    )
    repo = MagicMock()
    repo.list_active.return_value = [order]
    monitor = TradeMonitor(mon_conn, repo, price_anomaly_pct=0.20)

    result = monitor.check_once()

    assert order.client_order_id in result.anomaly_fills
    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='PRICE_ANOMALY'").fetchall()
    assert len(rows) == 1


def test_trade_monitor_market_order_excluded(mon_conn):
    """成行注文（price=0.0）は約定異常チェック対象外"""
    from kabusys.monitoring.trade_monitor import TradeMonitor

    order = _make_order(
        state=OrderState.Filled,
        price=0.0,
        avg_fill_price=1500.0,
        order_type="market",
    )
    repo = MagicMock()
    repo.list_active.return_value = [order]
    monitor = TradeMonitor(mon_conn, repo, price_anomaly_pct=0.20)

    result = monitor.check_once()

    assert result.anomaly_fills == []
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_monitoring_engine.py -k "trade_monitor" -v
```

Expected: `ImportError`

### 3-B: 実装する

- [ ] **Step 3: trade_monitor.py を作成**

`src/kabusys/monitoring/trade_monitor.py`:

```python
"""trade_monitor.py — 注文滞留・約定異常価格を監視する。"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository
from kabusys.monitoring.monitoring_db import MonitoringDB


@dataclass
class TradeCheckResult:
    logged_at: str
    stale_orders: list[str] = field(default_factory=list)
    anomaly_fills: list[str] = field(default_factory=list)


class TradeMonitor:
    def __init__(
        self,
        monitoring_conn: sqlite3.Connection,
        order_repo: OrderRepository,
        stale_minutes: int = 30,
        price_anomaly_pct: float = 0.20,
    ) -> None:
        self._db = MonitoringDB(monitoring_conn)
        self._repo = order_repo
        self._stale_minutes = stale_minutes
        self._price_anomaly_pct = price_anomaly_pct

    def check_once(self, now: datetime | None = None) -> TradeCheckResult:
        now = now or datetime.now(timezone.utc)
        stale_orders: list[str] = []
        anomaly_fills: list[str] = []

        for order in self._repo.list_active():
            created = order.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            # 注文滞留チェック
            age = now - created
            if age >= timedelta(minutes=self._stale_minutes):
                stale_orders.append(order.client_order_id)
                self._db.log_risk_event(
                    event_type="STALE_ORDER",
                    metric_name="order_age_minutes",
                    metric_value=age.total_seconds() / 60,
                    threshold=float(self._stale_minutes),
                    detail=order.client_order_id,
                )

            # 約定異常価格チェック（成行は除外）
            if (
                order.state in (OrderState.PartialFill, OrderState.Filled)
                and order.price != 0.0
                and order.avg_fill_price is not None
            ):
                deviation = abs(order.avg_fill_price - order.price) / order.price
                if deviation > self._price_anomaly_pct:
                    anomaly_fills.append(order.client_order_id)
                    self._db.log_risk_event(
                        event_type="PRICE_ANOMALY",
                        metric_name="fill_price_deviation",
                        metric_value=deviation,
                        threshold=self._price_anomaly_pct,
                        detail=order.client_order_id,
                    )

        return TradeCheckResult(
            logged_at=now.isoformat(),
            stale_orders=stale_orders,
            anomaly_fills=anomaly_fills,
        )
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
pytest tests/test_monitoring_engine.py -k "trade_monitor" -v
```

Expected: 6 PASS

- [ ] **Step 5: 全テスト確認**

```bash
pytest --tb=short -q
```

Expected: 514 passed

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/trade_monitor.py tests/test_monitoring_engine.py
git commit -m "feat: add TradeMonitor for stale-order and price-anomaly detection (Issue #38)"
```

---

## Task 4: RiskMonitor 実装

**Files:**
- Create: `src/kabusys/monitoring/risk_monitor.py`
- Modify: `tests/test_monitoring_engine.py` (テスト追記)

### 4-A: テストを書く

- [ ] **Step 1: テストを追記**

```python
# ─── RiskMonitor ─────────────────────────────────────────────────────────────

def _setup_dashboard(conn: sqlite3.Connection, portfolio_value: float, cash: float = 0.0) -> None:
    """dashboard テーブルに1行セットアップ。"""
    db = MonitoringDB(conn)
    db.upsert_dashboard(
        portfolio_value=portfolio_value,
        cash=cash,
        drawdown_pct=0.0,
        open_order_count=0,
        position_count=0,
    )


def test_risk_monitor_empty_dashboard(mon_conn):
    """dashboard テーブルが空 → drawdown=0, アラートなし"""
    from kabusys.monitoring.risk_monitor import RiskMonitor

    monitor = RiskMonitor(mon_conn)
    result = monitor.check_once()

    assert result.drawdown_pct == 0.0
    assert result.drawdown_alert is False
    assert result.position_count == 0
    assert result.position_limit_alert is False


def test_risk_monitor_no_drawdown(mon_conn):
    """portfolio_value が peak 以上 → drawdown=0, アラートなし"""
    from kabusys.monitoring.risk_monitor import RiskMonitor

    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    monitor = RiskMonitor(mon_conn, dd_threshold=0.10)

    result = monitor.check_once()

    assert result.drawdown_pct == pytest.approx(0.0)
    assert result.drawdown_alert is False


def test_risk_monitor_drawdown_alert(mon_conn):
    """DD が閾値（10%）超 → drawdown_alert=True, risk_log 記録"""
    from kabusys.monitoring.risk_monitor import RiskMonitor

    # 最初に peak を設定
    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
    monitor.check_once()  # peak = 1,000,000

    # portfolio が 15% 下落
    _setup_dashboard(mon_conn, portfolio_value=850_000)
    result = monitor.check_once()

    assert result.drawdown_pct == pytest.approx(0.15)
    assert result.drawdown_alert is True

    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='DRAWDOWN_ALERT'").fetchall()
    assert len(rows) == 1


def test_risk_monitor_high_watermark_update(mon_conn):
    """portfolio_value が peak を上回った場合に peak が更新される"""
    from kabusys.monitoring.risk_monitor import RiskMonitor

    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
    monitor.check_once()  # peak = 1,000,000

    # 価値上昇 → peak が更新される
    _setup_dashboard(mon_conn, portfolio_value=1_200_000)
    monitor.check_once()  # peak = 1,200,000

    # 10% 下落（1,200,000 → 1,080,000）は閾値未満
    _setup_dashboard(mon_conn, portfolio_value=1_080_000)
    result = monitor.check_once()

    assert result.drawdown_pct == pytest.approx(0.10)
    assert result.drawdown_alert is False  # 10% ちょうどはアラートなし（> 閾値）


def test_risk_monitor_position_limit_alert(mon_conn):
    """ポジション数が max_positions 超 → position_limit_alert=True"""
    from kabusys.monitoring.risk_monitor import RiskMonitor

    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    # 11銘柄のポジションを追加
    db = MonitoringDB(mon_conn)
    for i in range(11):
        db.upsert_position(code=f"{7000+i}", qty=100, avg_price=1000.0)

    monitor = RiskMonitor(mon_conn, max_positions=10)
    result = monitor.check_once()

    assert result.position_count == 11
    assert result.position_limit_alert is True

    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='POSITION_LIMIT'").fetchall()
    assert len(rows) == 1


def test_risk_monitor_qty_zero_excluded(mon_conn):
    """qty=0 のポジションは銘柄数カウントから除外"""
    from kabusys.monitoring.risk_monitor import RiskMonitor

    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    db = MonitoringDB(mon_conn)
    db.upsert_position(code="7203", qty=0, avg_price=1000.0)  # 閉じたポジション

    monitor = RiskMonitor(mon_conn, max_positions=10)
    result = monitor.check_once()

    assert result.position_count == 0
    assert result.position_limit_alert is False
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_monitoring_engine.py -k "risk_monitor" -v
```

Expected: `ImportError`

### 4-B: 実装する

- [ ] **Step 3: risk_monitor.py を作成**

`src/kabusys/monitoring/risk_monitor.py`:

```python
"""risk_monitor.py — ドローダウン・ポジション上限を監視する。"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from kabusys.monitoring.monitoring_db import MonitoringDB


@dataclass
class RiskCheckResult:
    logged_at: str
    drawdown_pct: float
    drawdown_alert: bool
    position_count: int
    position_limit_alert: bool


class RiskMonitor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        max_positions: int = 10,
        dd_threshold: float = 0.10,
    ) -> None:
        self._db = MonitoringDB(conn)
        self._conn = conn
        self._max_positions = max_positions
        self._dd_threshold = dd_threshold
        self._peak_value: float | None = None

    def check_once(self, now: datetime | None = None) -> RiskCheckResult:
        now = now or datetime.now(timezone.utc)
        logged_at = now.isoformat()

        dashboard = self._db.get_dashboard()
        if dashboard is None:
            return RiskCheckResult(
                logged_at=logged_at,
                drawdown_pct=0.0,
                drawdown_alert=False,
                position_count=0,
                position_limit_alert=False,
            )

        portfolio_value = dashboard["portfolio_value"]

        # ハイウォーターマーク更新
        if self._peak_value is None or portfolio_value > self._peak_value:
            self._peak_value = portfolio_value

        drawdown_pct = (
            (self._peak_value - portfolio_value) / self._peak_value
            if self._peak_value > 0
            else 0.0
        )
        drawdown_alert = drawdown_pct > self._dd_threshold

        # ポジション数（qty != 0 のみ）
        row = self._conn.execute(
            "SELECT COUNT(*) FROM positions WHERE qty != 0"
        ).fetchone()
        position_count = row[0]
        position_limit_alert = position_count > self._max_positions

        if drawdown_alert:
            self._db.log_risk_event(
                event_type="DRAWDOWN_ALERT",
                metric_name="drawdown_pct",
                metric_value=drawdown_pct,
                threshold=self._dd_threshold,
            )

        if position_limit_alert:
            self._db.log_risk_event(
                event_type="POSITION_LIMIT",
                metric_name="position_count",
                metric_value=float(position_count),
                threshold=float(self._max_positions),
            )

        return RiskCheckResult(
            logged_at=logged_at,
            drawdown_pct=drawdown_pct,
            drawdown_alert=drawdown_alert,
            position_count=position_count,
            position_limit_alert=position_limit_alert,
        )
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
pytest tests/test_monitoring_engine.py -k "risk_monitor" -v
```

Expected: 6 PASS

- [ ] **Step 5: 全テスト確認**

```bash
pytest --tb=short -q
```

Expected: 526 passed

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/risk_monitor.py tests/test_monitoring_engine.py
git commit -m "feat: add RiskMonitor for drawdown and position-limit monitoring (Issue #38)"
```

---

## Task 5: MonitoringEngine 実装

**Files:**
- Create: `src/kabusys/monitoring/monitoring_engine.py`
- Modify: `tests/test_monitoring_engine.py` (テスト追記)

### 5-A: テストを書く

- [ ] **Step 1: テストを追記**

```python
# ─── MonitoringEngine ─────────────────────────────────────────────────────────

def test_monitoring_engine_run_once_calls_all_monitors():
    """run_once() が 3 つの Monitor の check_once() をすべて呼び出す"""
    from kabusys.monitoring.monitoring_engine import MonitoringEngine

    sys_mon = MagicMock()
    trade_mon = MagicMock()
    risk_mon = MagicMock()

    engine = MonitoringEngine(sys_mon, trade_mon, risk_mon)
    engine.run_once()

    sys_mon.check_once.assert_called_once()
    trade_mon.check_once.assert_called_once()
    risk_mon.check_once.assert_called_once()


def test_monitoring_engine_exception_does_not_stop_other_monitors():
    """1つの Monitor が例外を投げても残りの Monitor は実行される"""
    from kabusys.monitoring.monitoring_engine import MonitoringEngine

    sys_mon = MagicMock()
    sys_mon.check_once.side_effect = RuntimeError("system check failed")
    trade_mon = MagicMock()
    risk_mon = MagicMock()

    engine = MonitoringEngine(sys_mon, trade_mon, risk_mon)
    engine.run_once()  # 例外が伝播しないこと

    trade_mon.check_once.assert_called_once()
    risk_mon.check_once.assert_called_once()
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_monitoring_engine.py -k "monitoring_engine" -v
```

Expected: `ImportError`

### 5-B: 実装する

- [ ] **Step 3: monitoring_engine.py を作成**

`src/kabusys/monitoring/monitoring_engine.py`:

```python
"""monitoring_engine.py — 各 Monitor を束ねてポーリングする。"""
from __future__ import annotations

import logging
import time

from kabusys.monitoring.risk_monitor import RiskMonitor
from kabusys.monitoring.system_monitor import SystemMonitor
from kabusys.monitoring.trade_monitor import TradeMonitor

logger = logging.getLogger(__name__)


class MonitoringEngine:
    def __init__(
        self,
        system_monitor: SystemMonitor,
        trade_monitor: TradeMonitor,
        risk_monitor: RiskMonitor,
        interval_sec: int = 60,
    ) -> None:
        self._monitors = [system_monitor, trade_monitor, risk_monitor]
        self._interval_sec = interval_sec

    def run_once(self) -> None:
        """テスト用: 各 Monitor を1回だけ呼び出す。"""
        for monitor in self._monitors:
            try:
                monitor.check_once()
            except Exception:
                logger.exception("Monitor %s failed", type(monitor).__name__)

    def run(self) -> None:
        """本番用: KeyboardInterrupt まで interval_sec 間隔でポーリング。"""
        logger.info("MonitoringEngine starting (interval=%ds)", self._interval_sec)
        while True:
            self.run_once()
            time.sleep(self._interval_sec)
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
pytest tests/test_monitoring_engine.py -k "monitoring_engine" -v
```

Expected: 2 PASS

- [ ] **Step 5: 全テスト確認**

```bash
pytest --tb=short -q
```

Expected: 528 passed

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/monitoring_engine.py tests/test_monitoring_engine.py
git commit -m "feat: add MonitoringEngine with 60s polling loop (Issue #38)"
```

---

## Task 6: StreamlitDashboard 実装

**Files:**
- Create: `src/kabusys/monitoring/streamlit_dashboard.py`
- Create: `tests/test_streamlit_dashboard.py`

### 6-A: テストを書く

- [ ] **Step 1: テストファイルを作成**

`tests/test_streamlit_dashboard.py`:

```python
"""tests/test_streamlit_dashboard.py — Streamlit ダッシュボード テスト"""
from __future__ import annotations

import sqlite3

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


@pytest.fixture
def mon_conn():
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    return conn


def test_load_positions_empty(mon_conn):
    """positions が空の場合は空リストを返す"""
    from kabusys.monitoring.streamlit_dashboard import load_positions

    result = load_positions(mon_conn)
    assert result == []


def test_load_positions_returns_nonzero_qty_only(mon_conn):
    """qty != 0 のみ返す"""
    from kabusys.monitoring.streamlit_dashboard import load_positions

    db = MonitoringDB(mon_conn)
    db.upsert_position(code="7203", qty=100, avg_price=1000.0)
    db.upsert_position(code="6758", qty=0, avg_price=2000.0)  # 除外

    result = load_positions(mon_conn)

    assert len(result) == 1
    assert result[0]["code"] == "7203"


def test_load_recent_orders_empty(mon_conn):
    """trade_logs が空の場合は空リストを返す"""
    from kabusys.monitoring.streamlit_dashboard import load_recent_orders

    result = load_recent_orders(mon_conn)
    assert result == []


def test_load_recent_orders_limit(mon_conn):
    """limit=3 を指定すると最大3件返す"""
    from kabusys.monitoring.streamlit_dashboard import load_recent_orders

    db = MonitoringDB(mon_conn)
    for i in range(5):
        db.log_trade_event(
            event_type="ORDER_CREATED",
            client_order_id=f"order-{i}",
            code="7203",
            side="buy",
            qty=100,
            price=1000.0,
        )

    result = load_recent_orders(mon_conn, limit=3)
    assert len(result) == 3


def test_load_latest_system_status_none(mon_conn):
    """system_status が空の場合は None を返す"""
    from kabusys.monitoring.streamlit_dashboard import load_latest_system_status

    result = load_latest_system_status(mon_conn)
    assert result is None


def test_load_latest_system_status_returns_latest(mon_conn):
    """system_status が複数行あっても最新の1件のみ返す"""
    from kabusys.monitoring.streamlit_dashboard import load_latest_system_status
    from datetime import datetime, timezone, timedelta

    db = MonitoringDB(mon_conn)
    older = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 4, 1, 9, 1, tzinfo=timezone.utc)
    db.log_system_status(10.0, 50.0, 40.0, True, recorded_at=older)
    db.log_system_status(90.0, 80.0, 70.0, False, recorded_at=newer)

    result = load_latest_system_status(mon_conn)

    assert result is not None
    assert result["cpu_percent"] == pytest.approx(90.0)


def test_load_recent_risk_logs_empty(mon_conn):
    """risk_logs が空の場合は空リストを返す"""
    from kabusys.monitoring.streamlit_dashboard import load_recent_risk_logs

    result = load_recent_risk_logs(mon_conn)
    assert result == []
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_streamlit_dashboard.py -v
```

Expected: `ImportError`

### 6-B: 実装する

- [ ] **Step 3: streamlit_dashboard.py を作成**

`src/kabusys/monitoring/streamlit_dashboard.py`:

```python
"""streamlit_dashboard.py — KabuSys 監視ダッシュボード。

起動方法:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
"""
from __future__ import annotations

import argparse
import sqlite3

import streamlit as st

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


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

    conn = sqlite3.connect(db_path)
    init_monitoring_db(conn)
    db = MonitoringDB(conn)

    tab_overview, tab_positions, tab_orders, tab_system = st.tabs(
        ["Overview", "Positions", "Orders", "System"]
    )

    with tab_overview:
        dashboard = db.get_dashboard()
        if dashboard:
            col1, col2, col3 = st.columns(3)
            col1.metric("Portfolio Value", f"¥{dashboard['portfolio_value']:,.0f}")
            col2.metric("Cash", f"¥{dashboard['cash']:,.0f}")
            col3.metric("Drawdown", f"{dashboard['drawdown_pct'] * 100:.2f}%")
            st.caption(f"Updated: {dashboard['updated_at']}")
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

    st.rerun(every=30)


if __name__ == "__main__":
    main(_get_db_path())
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
pytest tests/test_streamlit_dashboard.py -v
```

Expected: 7 PASS

- [ ] **Step 5: 全テスト確認**

```bash
pytest --tb=short -q
```

Expected: 535 passed

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/streamlit_dashboard.py tests/test_streamlit_dashboard.py
git commit -m "feat: add Streamlit monitoring dashboard with 4-tab UI (Issue #35)"
```

---

## Task 7: __init__.py 更新 + Issue クローズ

**Files:**
- Modify: `src/kabusys/monitoring/__init__.py`

- [ ] **Step 1: __init__.py に新クラスをエクスポート追加**

`src/kabusys/monitoring/__init__.py`:

```python
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
from kabusys.monitoring.monitoring_engine import MonitoringEngine
from kabusys.monitoring.risk_monitor import RiskCheckResult, RiskMonitor
from kabusys.monitoring.system_monitor import SystemCheckResult, SystemMonitor
from kabusys.monitoring.trade_monitor import TradeCheckResult, TradeMonitor

__all__ = [
    "MonitoringDB",
    "init_monitoring_db",
    "SystemMonitor",
    "SystemCheckResult",
    "TradeMonitor",
    "TradeCheckResult",
    "RiskMonitor",
    "RiskCheckResult",
    "MonitoringEngine",
]
```

- [ ] **Step 2: インポートが通ることを確認**

```bash
python -c "from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 全テスト最終確認**

```bash
pytest --tb=short -q
```

Expected: 535 passed（追加テスト数は実装中に確定）

- [ ] **Step 4: コミット + Issue クローズ**

```bash
git add src/kabusys/monitoring/__init__.py
git commit -m "feat: export Phase 7 monitoring classes from __init__.py (Close #38, #35)"
```

---

## 完了チェックリスト

- [ ] `pytest` が全 PASS
- [ ] `from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine` が通る
- [ ] `streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db` が起動する（手動確認）
- [ ] Issue #38・#35 がクローズされている
