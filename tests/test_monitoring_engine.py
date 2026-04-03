"""tests/test_monitoring_engine.py — Phase 7 監視エンジン テスト"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
from kabusys.monitoring.monitoring_engine import MonitoringEngine
from kabusys.monitoring.risk_monitor import RiskMonitor
from kabusys.monitoring.system_monitor import SystemMonitor
from kabusys.monitoring.trade_monitor import TradeMonitor


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

def test_system_monitor_no_pid_file(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルなし → process_ok=False, stale_pid_detected=False"""
    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()), \
         patch("psutil.cpu_percent", return_value=30.0), \
         patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)), \
         patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
        result = monitor.check_once(today=date.today())

    assert result.process_ok is False
    assert result.stale_pid_detected is False
    assert result.cpu_percent == 30.0
    assert result.memory_percent == 50.0
    assert result.disk_percent == 40.0


def test_system_monitor_pid_alive(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルあり + プロセス生存 → process_ok=True, stale_pid_detected=False"""
    pid_file = tmp_path / "execution.pid"
    pid_file.write_text("12345")
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()), \
         patch("psutil.pid_exists", return_value=True), \
         patch("psutil.cpu_percent", return_value=30.0), \
         patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)), \
         patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
        result = monitor.check_once(today=date.today())

    assert result.process_ok is True
    assert result.stale_pid_detected is False
    assert pid_file.exists()  # ファイルは残る


def test_system_monitor_stale_pid(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルあり + プロセス死亡 → stale_pid_detected=True, ファイル削除, risk_log記録"""
    pid_file = tmp_path / "execution.pid"
    pid_file.write_text("12345")
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()), \
         patch("psutil.pid_exists", return_value=False), \
         patch("psutil.cpu_percent", return_value=30.0), \
         patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)), \
         patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
        result = monitor.check_once(today=date.today())

    assert result.process_ok is False
    assert result.stale_pid_detected is True
    assert not pid_file.exists()  # ファイルが削除される

    # risk_logs に STALE_PID が記録されているか確認
    mon_conn.row_factory = sqlite3.Row
    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='STALE_PID'").fetchall()
    assert len(rows) == 1


def test_system_monitor_invalid_pid_file(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルが不正内容 → ファイル削除・stale_pid_detected=True・risk_log記録"""
    pid_file = tmp_path / "execution.pid"
    pid_file.write_text("not-a-number")
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()), \
         patch("psutil.cpu_percent", return_value=30.0), \
         patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)), \
         patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
        result = monitor.check_once(today=date.today())

    assert result.process_ok is False
    assert result.stale_pid_detected is True
    assert not pid_file.exists()

    mon_conn.row_factory = sqlite3.Row
    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='STALE_PID'").fetchall()
    assert len(rows) == 1


def test_system_monitor_data_freshness_ok(mon_conn, mock_duckdb, tmp_path):
    """株価データが 2 日前 → data_freshness_ok=True"""
    today = date(2026, 4, 1)
    last_price = date(2026, 3, 30)  # 2日前
    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=last_price), \
         patch("psutil.cpu_percent", return_value=30.0), \
         patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)), \
         patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
        result = monitor.check_once(today=today)

    assert result.data_freshness_ok is True


def test_system_monitor_data_freshness_ng(mon_conn, mock_duckdb, tmp_path):
    """株価データが 4 日前 → data_freshness_ok=False"""
    today = date(2026, 4, 1)
    last_price = date(2026, 3, 28)  # 4日前
    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=last_price), \
         patch("psutil.cpu_percent", return_value=30.0), \
         patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)), \
         patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
        result = monitor.check_once(today=today)

    assert result.data_freshness_ok is False


def test_system_monitor_data_freshness_none(mon_conn, mock_duckdb, tmp_path):
    """get_last_price_date が None（空 DuckDB）→ data_freshness_ok=False"""
    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=None), \
         patch("psutil.cpu_percent", return_value=30.0), \
         patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)), \
         patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
        result = monitor.check_once(today=date.today())

    assert result.data_freshness_ok is False


# ─── TradeMonitor ─────────────────────────────────────────────────────────────

from kabusys.execution.order_record import OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository


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
    repo = MagicMock()
    repo.list_active.return_value = []
    monitor = TradeMonitor(mon_conn, repo)

    result = monitor.check_once()

    assert result.stale_orders == []
    assert result.anomaly_fills == []


def test_trade_monitor_fresh_order_not_stale(mon_conn):
    """作成5分後の注文 → stale 判定なし"""
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
    """約定価格が発注価格の 30% 乖離 → anomaly_fills に追加"""
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
    monitor = RiskMonitor(mon_conn)
    result = monitor.check_once()

    assert result.drawdown_pct == 0.0
    assert result.drawdown_alert is False
    assert result.position_count == 0
    assert result.position_limit_alert is False


def test_risk_monitor_no_drawdown(mon_conn):
    """portfolio_value が peak 以上 → drawdown=0, アラートなし"""
    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    monitor = RiskMonitor(mon_conn, dd_threshold=0.10)

    result = monitor.check_once()

    assert result.drawdown_pct == pytest.approx(0.0)
    assert result.drawdown_alert is False


def test_risk_monitor_drawdown_alert(mon_conn):
    """DD が閾値（10%）超 → drawdown_alert=True, risk_log 記録"""
    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
    monitor.check_once()  # peak = 1,000,000

    _setup_dashboard(mon_conn, portfolio_value=850_000)
    result = monitor.check_once()

    assert result.drawdown_pct == pytest.approx(0.15)
    assert result.drawdown_alert is True

    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='DRAWDOWN_ALERT'").fetchall()
    assert len(rows) == 1


def test_risk_monitor_high_watermark_update(mon_conn):
    """portfolio_value が peak を上回った場合に peak が更新される"""
    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
    monitor.check_once()  # peak = 1,000,000

    _setup_dashboard(mon_conn, portfolio_value=1_200_000)
    monitor.check_once()  # peak = 1,200,000

    # ちょうど10%下落はアラートなし（> 閾値のため）
    _setup_dashboard(mon_conn, portfolio_value=1_080_000)
    result = monitor.check_once()

    assert result.drawdown_pct == pytest.approx(0.10)
    assert result.drawdown_alert is False  # 10% ちょうどはアラートなし（> 閾値）


def test_risk_monitor_position_limit_alert(mon_conn):
    """ポジション数が max_positions 超 → position_limit_alert=True"""
    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
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
    _setup_dashboard(mon_conn, portfolio_value=1_000_000)
    db = MonitoringDB(mon_conn)
    db.upsert_position(code="7203", qty=0, avg_price=1000.0)

    monitor = RiskMonitor(mon_conn, max_positions=10)
    result = monitor.check_once()

    assert result.position_count == 0
    assert result.position_limit_alert is False


# ─── MonitoringEngine ─────────────────────────────────────────────────────────

def test_monitoring_engine_run_once_calls_all_monitors():
    """run_once() が 3 つの Monitor の check_once() をすべて呼び出す"""
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
    sys_mon = MagicMock()
    sys_mon.check_once.side_effect = RuntimeError("system check failed")
    trade_mon = MagicMock()
    risk_mon = MagicMock()

    engine = MonitoringEngine(sys_mon, trade_mon, risk_mon)
    engine.run_once()  # 例外が伝播しないこと

    trade_mon.check_once.assert_called_once()
    risk_mon.check_once.assert_called_once()


# ─── MonitoringEngine + KillSwitch / AlertManager ────────────────────────────

from kabusys.monitoring.kill_switch import KillSwitch
from kabusys.monitoring.alert_manager import AlertManager


def test_monitoring_engine_calls_kill_switch_when_all_results_available():
    """全 Monitor が成功した場合 KillSwitch.evaluate() が呼ばれる"""
    sys_mon = MagicMock()
    trade_mon = MagicMock()
    risk_mon = MagicMock()
    kill_switch = MagicMock(spec=KillSwitch)
    kill_switch.evaluate.return_value = None

    engine = MonitoringEngine(sys_mon, trade_mon, risk_mon, kill_switch=kill_switch)
    engine.run_once()

    kill_switch.evaluate.assert_called_once_with(
        sys_mon.check_once.return_value,
        trade_mon.check_once.return_value,
        risk_mon.check_once.return_value,
    )


def test_monitoring_engine_skips_kill_switch_when_monitor_fails():
    """Monitor が例外を投げた場合 KillSwitch.evaluate() は呼ばれない"""
    sys_mon = MagicMock()
    sys_mon.check_once.side_effect = RuntimeError("boom")
    trade_mon = MagicMock()
    risk_mon = MagicMock()
    kill_switch = MagicMock(spec=KillSwitch)

    engine = MonitoringEngine(sys_mon, trade_mon, risk_mon, kill_switch=kill_switch)
    engine.run_once()

    kill_switch.evaluate.assert_not_called()


def test_monitoring_engine_notifies_alert_manager_on_kill_switch_trigger():
    """KillSwitch が reason を返した場合 AlertManager.notify() が CRITICAL で呼ばれる"""
    sys_mon = MagicMock()
    trade_mon = MagicMock()
    risk_mon = MagicMock()
    # Prevent individual alert conditions from triggering (only test kill-switch path)
    sys_mon.check_once.return_value.process_ok = True
    sys_mon.check_once.return_value.data_freshness_ok = True
    trade_mon.check_once.return_value.stale_orders = []
    trade_mon.check_once.return_value.anomaly_fills = []
    risk_mon.check_once.return_value.drawdown_alert = False
    risk_mon.check_once.return_value.position_limit_alert = False
    kill_switch = MagicMock(spec=KillSwitch)
    kill_switch.evaluate.return_value = "DRAWDOWN_ALERT: DD 12.3%"
    alert_manager = MagicMock(spec=AlertManager)

    engine = MonitoringEngine(
        sys_mon, trade_mon, risk_mon,
        kill_switch=kill_switch,
        alert_manager=alert_manager,
    )
    engine.run_once()

    alert_manager.notify.assert_any_call(
        "Kill Switch 発動: DRAWDOWN_ALERT: DD 12.3%", "CRITICAL", category="KILL_SWITCH"
    )


def test_monitoring_engine_without_kill_switch_still_works():
    """kill_switch=None でも run_once() が正常動作する（既存テストの互換性確認）"""
    sys_mon = MagicMock()
    trade_mon = MagicMock()
    risk_mon = MagicMock()

    engine = MonitoringEngine(sys_mon, trade_mon, risk_mon)
    engine.run_once()

    sys_mon.check_once.assert_called_once()
    trade_mon.check_once.assert_called_once()
    risk_mon.check_once.assert_called_once()


# ─── Issue #141: log_risk_event デデュープ ────────────────────────────────────

class TestLogRiskEventDedup:
    """log_risk_event() の dedup_minutes 引数のテスト。"""

    def test_dedup_skips_within_window(self, mon_conn):
        """同一 (event_type, detail=None) を 30 分以内に再呼び出し → 2件目はスキップ。"""
        db = MonitoringDB(mon_conn)
        now = datetime.now(timezone.utc)

        r1 = db.log_risk_event(
            "DRAWDOWN_ALERT", "drawdown_pct", 0.15, 0.10,
            logged_at=now, dedup_minutes=30,
        )
        r2 = db.log_risk_event(
            "DRAWDOWN_ALERT", "drawdown_pct", 0.16, 0.10,
            logged_at=now + timedelta(minutes=10), dedup_minutes=30,
        )

        assert r1 is True
        assert r2 is False
        rows = mon_conn.execute("SELECT * FROM risk_logs").fetchall()
        assert len(rows) == 1

    def test_dedup_records_after_window(self, mon_conn):
        """直前レコードが 31 分前なら記録される。"""
        db = MonitoringDB(mon_conn)
        past = datetime.now(timezone.utc) - timedelta(minutes=31)
        now = datetime.now(timezone.utc)

        db.log_risk_event(
            "DRAWDOWN_ALERT", "drawdown_pct", 0.15, 0.10,
            logged_at=past, dedup_minutes=30,
        )
        r2 = db.log_risk_event(
            "DRAWDOWN_ALERT", "drawdown_pct", 0.16, 0.10,
            logged_at=now, dedup_minutes=30,
        )

        assert r2 is True
        rows = mon_conn.execute("SELECT * FROM risk_logs").fetchall()
        assert len(rows) == 2

    def test_no_dedup_when_none(self, mon_conn):
        """`dedup_minutes=None`（デフォルト）では毎回記録される。"""
        db = MonitoringDB(mon_conn)
        now = datetime.now(timezone.utc)

        db.log_risk_event("DRAWDOWN_ALERT", "drawdown_pct", 0.15, 0.10, logged_at=now)
        db.log_risk_event("DRAWDOWN_ALERT", "drawdown_pct", 0.16, 0.10, logged_at=now)

        rows = mon_conn.execute("SELECT * FROM risk_logs").fetchall()
        assert len(rows) == 2

    def test_dedup_different_detail_records_both(self, mon_conn):
        """`detail` が異なれば別イベントとして記録される。"""
        db = MonitoringDB(mon_conn)
        now = datetime.now(timezone.utc)

        db.log_risk_event(
            "STALE_ORDER", "order_age_minutes", 35.0, 30.0,
            detail="order-001", logged_at=now, dedup_minutes=30,
        )
        db.log_risk_event(
            "STALE_ORDER", "order_age_minutes", 35.0, 30.0,
            detail="order-002", logged_at=now, dedup_minutes=30,
        )

        rows = mon_conn.execute("SELECT * FROM risk_logs").fetchall()
        assert len(rows) == 2


# ─── Issue #142: dashboard peak_value カラム ──────────────────────────────────

class TestDashboardPeakValue:
    """dashboard テーブルの peak_value カラム追加テスト。"""

    def test_migration_adds_peak_value_column(self):
        """既存 DB（peak_value カラムなし）に init_monitoring_db() を再実行してもエラーなし。"""
        conn = sqlite3.connect(":memory:")
        # peak_value なしで旧スキーマを作成
        conn.execute("""
            CREATE TABLE dashboard (
                id               INTEGER PRIMARY KEY CHECK (id = 1),
                updated_at       TEXT    NOT NULL,
                portfolio_value  REAL    NOT NULL,
                cash             REAL    NOT NULL,
                drawdown_pct     REAL    NOT NULL,
                open_order_count INTEGER NOT NULL,
                position_count   INTEGER NOT NULL
            )
        """)
        conn.commit()
        # init_monitoring_db を再実行 → エラーなし
        init_monitoring_db(conn)
        # peak_value カラムが存在することを確認
        cols = [row[1] for row in conn.execute("PRAGMA table_info(dashboard)").fetchall()]
        assert "peak_value" in cols

    def test_upsert_dashboard_sets_peak_value(self, mon_conn):
        """peak_value を指定すると dashboard に保存される。"""
        db = MonitoringDB(mon_conn)
        db.upsert_dashboard(
            portfolio_value=1_000_000, cash=500_000, drawdown_pct=0.0,
            open_order_count=0, position_count=0, peak_value=1_200_000,
        )
        row = db.get_dashboard()
        assert row["peak_value"] == 1_200_000

    def test_upsert_dashboard_preserves_peak_value_when_none(self, mon_conn):
        """peak_value=None で呼ぶと既存の peak_value が保護される。"""
        db = MonitoringDB(mon_conn)
        db.upsert_dashboard(
            portfolio_value=1_000_000, cash=500_000, drawdown_pct=0.0,
            open_order_count=0, position_count=0, peak_value=1_200_000,
        )
        # peak_value=None（デフォルト）で再呼び出し
        db.upsert_dashboard(
            portfolio_value=900_000, cash=400_000, drawdown_pct=0.1,
            open_order_count=0, position_count=0,
        )
        row = db.get_dashboard()
        assert row["peak_value"] == 1_200_000  # 保護されていること
        assert row["portfolio_value"] == 900_000  # 他フィールドは更新

    def test_peak_value_persisted_on_new_high(self, mon_conn):
        """新しい高値で upsert_dashboard() を呼ぶと peak_value が更新される。"""
        db = MonitoringDB(mon_conn)
        db.upsert_dashboard(
            portfolio_value=1_000_000, cash=500_000, drawdown_pct=0.0,
            open_order_count=0, position_count=0, peak_value=1_000_000.0,
        )
        db.upsert_dashboard(
            portfolio_value=1_100_000, cash=500_000, drawdown_pct=0.0,
            open_order_count=0, position_count=0, peak_value=1_100_000.0,
        )
        row = db.get_dashboard()
        assert row["peak_value"] == 1_100_000.0


# ─── Issue #142: RiskMonitor peak_value DB 永続化 ─────────────────────────────

class TestRiskMonitorPeakValuePersistence:
    """RiskMonitor が _peak_value を dashboard DB に読み書きするテスト。"""

    def test_peak_value_persisted_on_new_high(self, mon_conn):
        """新高値で check_once() した後、DB の peak_value が更新される。"""
        _setup_dashboard(mon_conn, portfolio_value=1_000_000)
        monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
        monitor.check_once()  # peak = 1,000,000 → DB に保存されるはず

        db = MonitoringDB(mon_conn)
        row = db.get_dashboard()
        assert row["peak_value"] == 1_000_000

        # 新高値
        _setup_dashboard(mon_conn, portfolio_value=1_200_000)
        monitor.check_once()

        row = db.get_dashboard()
        assert row["peak_value"] == 1_200_000

    def test_peak_value_restored_on_restart(self, mon_conn):
        """再起動（新インスタンス）後に check_once() を呼ぶと DB から peak_value が復元される。"""
        db = MonitoringDB(mon_conn)
        # peak_value=1_500_000 を DB にセット
        db.upsert_dashboard(
            portfolio_value=1_200_000,
            cash=500_000,
            drawdown_pct=0.0,
            open_order_count=0,
            position_count=0,
            peak_value=1_500_000,
        )

        # 新インスタンスで check_once() → DB から peak_value を復元
        new_monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
        new_monitor.check_once()

        assert new_monitor._peak_value == 1_500_000

    def test_drawdown_correct_after_restart(self, mon_conn):
        """DB に peak_value=2_000_000 をセット後、ポートフォリオ 1_800_000 に下落した場合、
        drawdown=10% が正しく計算される。"""
        db = MonitoringDB(mon_conn)
        db.upsert_dashboard(
            portfolio_value=1_800_000,
            cash=500_000,
            drawdown_pct=0.0,
            open_order_count=0,
            position_count=0,
            peak_value=2_000_000,
        )

        monitor = RiskMonitor(mon_conn, dd_threshold=0.05)
        result = monitor.check_once()

        assert result.drawdown_pct == pytest.approx(0.10)
        assert result.drawdown_alert is True
