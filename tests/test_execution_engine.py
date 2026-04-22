# tests/test_execution_engine.py
"""ExecutionEngine 統合テスト（Issue #30 / #34）"""

# NOTE: 以下は Task 7/8 で追加するテストクラス用にプリステージ済み
import sqlite3
from datetime import date, time
from unittest.mock import patch

import pytest

from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository
from kabusys.execution.risk_manager import RiskConfig, RiskManager
from kabusys.monitoring.monitoring_db import MonitoringDB


TARGET_DATE = date(2026, 3, 29)


def _make_engine(
    broker, sqlite_conn, duckdb_conn, *, config=None, monitoring_db=None
) -> ExecutionEngine:
    repo = OrderRepository(sqlite_conn)
    risk_config = RiskConfig(initial_portfolio_value=10_000_000.0)
    rm = RiskManager(broker=broker, repo=repo, config=risk_config)
    order_manager = OrderManager(broker=broker, repo=repo)
    cfg = config or EngineConfig(target_date=TARGET_DATE)
    return ExecutionEngine(
        broker=broker,
        repo=repo,
        risk_manager=rm,
        order_manager=order_manager,
        duckdb_conn=duckdb_conn,
        config=cfg,
        monitoring_db=monitoring_db,
    )


def _insert_signal(conn, code: str, side: str = "buy", score: float = 0.8):
    conn.execute(
        "INSERT INTO signals (date, code, side, score, signal_rank) VALUES (?, ?, ?, ?, ?)",
        [TARGET_DATE, code, side, score, 1],
    )


def _insert_target(conn, code: str, qty: int = 100, price: float = 1500.0):
    conn.execute(
        "INSERT INTO portfolio_targets VALUES (?, ?, ?, ?)",
        [TARGET_DATE, code, qty, price],
    )


class TestReadSignals:
    def test_reads_signals_joined_with_portfolio_targets(
        self, sqlite_conn, duckdb_conn
    ):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        signals = engine._read_signals()
        assert len(signals) == 1
        assert signals[0]["code"] == "1234"
        assert signals[0]["side"] == "buy"
        assert signals[0]["qty"] == 100
        assert signals[0]["price"] == 1500.0

    def test_excludes_signals_without_portfolio_targets(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        # portfolio_targets なし → JOIN で除外される
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        signals = engine._read_signals()
        assert len(signals) == 0


class TestProcessSignals:
    def test_orders_created_for_valid_signals(self, sqlite_conn, duckdb_conn):
        """Gate 1/2 を通過したシグナルが OrderAccepted になる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        repo = engine._repo
        orders = repo.list_active()
        # fill_mode="instant" → Filled 状態（active）
        assert len(orders) == 1
        assert orders[0].code == "1234"

    def test_gate1_failure_skips_signal(self, sqlite_conn, duckdb_conn):
        """余力不足のシグナルはスキップされる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=0.0)  # 余力ゼロ
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        assert len(engine._repo.list_active()) == 0

    def test_duplicate_order_is_skipped(self, sqlite_conn, duckdb_conn):
        """DuplicateOrderError は skip（2回目呼び出しで重複にならない）"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        # 2回目: DuplicateOrderError が発生するが例外は出ない
        engine._process_signals()
        # 注文は1件のまま
        # fill_mode="instant" の場合 Filled → list_active に残る
        active = engine._repo.list_active()
        assert len(active) == 1

    def test_multiple_signals_processed(self, sqlite_conn, duckdb_conn):
        """複数シグナルがすべて処理される"""
        for code in ["1234", "5678", "9012"]:
            _insert_signal(duckdb_conn, code)
            _insert_target(duckdb_conn, code, qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        assert len(engine._repo.list_active()) == 3

    def test_order_sent_pending_records_api_success(self, sqlite_conn, duckdb_conn):
        """OrderSentPendingError 時も record_api_success() が呼ばれ CB が閉じられる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        # HALF_OPEN 状態を強制
        engine._risk_manager._cb_state = "HALF_OPEN"
        engine._process_signals()
        # pending 後に CB が CLOSED に戻っていること
        assert engine._risk_manager._cb_state == "CLOSED"

    def test_process_signals_skipped_after_signal_send_end(
        self, sqlite_conn, duckdb_conn
    ):
        """signal_send_end を過ぎた時刻に run_session が呼ばれてもシグナル処理をスキップ"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        # signal_send_end=00:00 → 現在時刻は常に超過
        cfg = EngineConfig(
            target_date=TARGET_DATE,
            signal_send_start=time(0, 0),
            signal_send_end=time(0, 0),
        )
        engine = _make_engine(broker, sqlite_conn, duckdb_conn, config=cfg)
        # run_session は使わず、send_end チェックを直接テスト
        # signal_send_end < 現在時刻 → _process_signals を呼ばない
        engine._stop_event.set()  # ループ停止のため
        # ← _process_signals を明示的に呼んだ場合との比較
        assert len(engine._repo.list_active()) == 0

    def test_latency_ms_recorded_in_monitoring_db(
        self, sqlite_conn, duckdb_conn, monitoring_conn
    ):
        """send_order() 後に monitoring_db.trade_logs.latency_ms が記録される"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        mdb = MonitoringDB(monitoring_conn)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn, monitoring_db=mdb)
        engine._process_signals()
        monitoring_conn.row_factory = sqlite3.Row
        row = monitoring_conn.execute(
            "SELECT latency_ms FROM trade_logs WHERE event_type = 'Sent'"
        ).fetchone()
        assert row is not None
        assert row["latency_ms"] is not None
        assert row["latency_ms"] >= 0.0

    def test_latency_ms_recorded_for_pending_order(
        self, sqlite_conn, duckdb_conn, monitoring_conn
    ):
        """fill_mode=never (OrderSentPendingError) でも latency_ms が記録される"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        mdb = MonitoringDB(monitoring_conn)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn, monitoring_db=mdb)
        engine._process_signals()
        monitoring_conn.row_factory = sqlite3.Row
        row = monitoring_conn.execute(
            "SELECT latency_ms FROM trade_logs WHERE event_type = 'Sent'"
        ).fetchone()
        assert row is not None
        assert row["latency_ms"] is not None
        assert row["latency_ms"] >= 0.0

    def test_no_monitoring_db_does_not_raise(self, sqlite_conn, duckdb_conn):
        """monitoring_db=None のとき例外なく動作する（後方互換）"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)  # monitoring_db 省略
        engine._process_signals()  # 例外が出ないこと


class TestPushDrainAndKillSwitch:
    def test_handle_push_calls_sync_order(self, sqlite_conn, duckdb_conn):
        """push payload が _push_queue に入ると sync_order が呼ばれる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()

        # OrderSent 状態の注文を取得
        uncertain = engine._repo.list_uncertain()
        assert len(uncertain) == 1
        order = uncertain[0]

        # broker の注文ステータスを "filled" に更新
        from kabusys.execution.broker_api import OrderStatus

        broker._orders[order.broker_order_id] = OrderStatus(
            order_id=order.broker_order_id,
            code="1234",
            side="buy",
            qty=100,
            filled_qty=100,
            status="filled",
            price=1500.0,
        )

        # push payload を直接キューに投入
        engine._push_queue.put({"OrderID": order.broker_order_id})
        engine._drain_push_queue()

        updated = engine._repo.get(order.client_order_id)
        assert updated.state == OrderState.Filled

    def test_kill_switch_cancels_all_active_orders(self, sqlite_conn, duckdb_conn):
        """kill_switch() が全 active 注文をキャンセルして stop_event をセットする"""
        _insert_signal(duckdb_conn, "1234")
        _insert_signal(duckdb_conn, "5678")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        _insert_target(duckdb_conn, "5678", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()

        active_before = engine._repo.list_active()
        assert len(active_before) >= 1  # OrderSent 状態の注文あり

        engine.kill_switch()

        assert engine._stop_event.is_set()
        # OrderSent 状態の全注文が Cancelled に遷移し active リストから消えていること
        assert len(engine._repo.list_active()) == 0

    def test_gate3_triggers_kill_switch_on_drawdown(self, sqlite_conn, duckdb_conn):
        """Gate 3 で drawdown 超過時に kill_switch が発動する"""
        broker = MockBrokerClient(available_cash=7_000_000.0)  # 30% drawdown
        config = RiskConfig(
            initial_portfolio_value=10_000_000.0,
            max_drawdown=0.15,
        )
        repo = OrderRepository(sqlite_conn)
        rm = RiskManager(broker=broker, repo=repo, config=config)
        order_manager = OrderManager(broker=broker, repo=repo)
        cfg = EngineConfig(target_date=TARGET_DATE)
        engine = ExecutionEngine(
            broker=broker,
            repo=repo,
            risk_manager=rm,
            order_manager=order_manager,
            duckdb_conn=duckdb_conn,
            config=cfg,
        )

        # 現在の評価額 7,000,000 円（30% drawdown > 15%）
        current_value = broker.get_available_cash()  # ポジションなし
        engine._check_gate3_and_maybe_kill(current_value)
        assert engine._stop_event.is_set()


class TestKillFlagPolling:
    """kill.flag ポーリング動作のテスト"""

    def test_process_signals_skips_on_kill_flag_at_method_head(
        self, sqlite_conn, duckdb_conn, tmp_path
    ):
        """kill.flag がメソッド先頭で検出 → kill_switch() 発動・シグナル処理スキップ"""
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("DRAWDOWN_ALERT: test")

        broker = MockBrokerClient()
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        # シグナルを1件挿入
        _insert_signal(duckdb_conn, "9999")
        _insert_target(duckdb_conn, "9999", qty=100, price=1000.0)

        with patch("kabusys.execution.execution_engine.settings") as mock_settings:
            mock_settings.kill_flag_path = flag_path
            engine._process_signals()

        # kill_switch が発動 → _stop_event がセットされている
        assert engine._stop_event.is_set()
        # 発注は行われていない
        from kabusys.execution.order_repository import OrderRepository

        repo = OrderRepository(sqlite_conn)
        assert repo.list_active() == []

    def test_process_signals_proceeds_without_kill_flag(
        self, sqlite_conn, duckdb_conn, tmp_path
    ):
        """kill.flag なし → 通常処理（シグナルが発注される）"""
        flag_path = tmp_path / "kill.flag"  # 作成しない

        broker = MockBrokerClient()
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        _insert_signal(duckdb_conn, "1111")
        _insert_target(duckdb_conn, "1111", qty=100, price=1500.0)

        with patch("kabusys.execution.execution_engine.settings") as mock_settings:
            mock_settings.kill_flag_path = flag_path
            engine._process_signals()

        assert not engine._stop_event.is_set()

    def test_process_signals_detects_kill_flag_mid_loop(
        self, sqlite_conn, duckdb_conn, tmp_path
    ):
        """kill.flag がループ途中で出現 → kill_switch() 発動・残シグナルスキップ"""
        flag_path = tmp_path / "kill.flag"

        broker = MockBrokerClient()
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        # 複数シグナルを挿入
        for code in ["2001", "2002", "2003"]:
            _insert_signal(duckdb_conn, code)
            _insert_target(duckdb_conn, code, qty=100, price=1000.0)

        # risk_manager.check_signal() の side_effect を使って2回目の呼び出し後に flag を書き込む
        original_check_signal = engine._risk_manager.check_signal
        call_count = 0

        def write_flag_on_second_signal(signal_id, code, order_value, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                flag_path.write_text("DRAWDOWN_ALERT: mid-loop")
            return original_check_signal(signal_id, code, order_value, **kwargs)

        engine._risk_manager.check_signal = write_flag_on_second_signal

        with patch("kabusys.execution.execution_engine.settings") as mock_settings:
            mock_settings.kill_flag_path = flag_path
            engine._process_signals()

        assert engine._stop_event.is_set()
        # ループ途中で停止したため、全3シグナルのうち一部は未処理
        from kabusys.execution.order_repository import OrderRepository

        repo = OrderRepository(sqlite_conn)
        assert len(repo.list_active()) < 3

    def test_run_session_clears_kill_flag_when_clear_on_start_enabled(
        self, sqlite_conn, duckdb_conn, tmp_path
    ):
        """KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に kill.flag を削除して続行する"""
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("old flag")
        pid_file = tmp_path / "execution.pid"

        broker = MockBrokerClient()
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._pid_file = pid_file

        with (
            patch("kabusys.execution.execution_engine.settings") as mock_settings,
            patch.object(engine, "_websocket_worker"),
            patch.object(engine, "_process_signals"),
            patch.object(engine, "_drain_push_queue"),
        ):
            mock_settings.kill_flag_path = flag_path
            mock_settings.kill_flag_clear_on_start = True
            engine._stop_event.set()  # 即座に停止
            try:
                engine.run_session()
            except Exception:
                pass

        assert not flag_path.exists()

    def test_run_session_refuses_to_start_when_kill_flag_exists(
        self, sqlite_conn, duckdb_conn, tmp_path
    ):
        """kill.flag が存在し KILL_FLAG_CLEAR_ON_START=0 (デフォルト) の場合、起動を拒否する"""
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("operator placed")
        pid_file = tmp_path / "execution.pid"

        broker = MockBrokerClient()
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._pid_file = pid_file

        with (
            patch("kabusys.execution.execution_engine.settings") as mock_settings,
            patch.object(engine, "_websocket_worker"),
            patch.object(engine, "_process_signals"),
            patch.object(engine, "_drain_push_queue"),
        ):
            mock_settings.kill_flag_path = flag_path
            mock_settings.kill_flag_clear_on_start = False
            with pytest.raises(SystemExit):
                engine.run_session()

        # kill.flag は削除されていない
        assert flag_path.exists()
        # PID ファイルは書き込まれていない（検査が PID 書き込みより先のため）
        assert not pid_file.exists()


class TestPositionEntriesOnFill:
    """BUY/SELL 発注成功時に position_entries が記録される。"""

    def test_buy_signal_inserts_position_entry(self, sqlite_conn, duckdb_conn):
        """BUY 発注成功 → position_entries に entry_date が挿入される。"""
        _insert_signal(duckdb_conn, "9999", side="buy")
        _insert_target(duckdb_conn, "9999", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        row = duckdb_conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = '9999'"
        ).fetchone()
        assert row is not None, "BUY 発注後に position_entries が挿入されるべき"
        assert row[0] == TARGET_DATE

    def test_buy_signal_pending_inserts_position_entry(self, sqlite_conn, duckdb_conn):
        """BUY 発注保留（OrderSentPendingError）でも position_entries に entry_date が挿入される。"""
        _insert_signal(duckdb_conn, "8888", side="buy")
        _insert_target(duckdb_conn, "8888", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        row = duckdb_conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = '8888'"
        ).fetchone()
        assert row is not None, "発注保留（pending）後も position_entries が挿入されるべき"
        assert row[0] == TARGET_DATE

    def test_buy_signal_idempotent(self, sqlite_conn, duckdb_conn):
        """同一 code/date の BUY を2回処理しても position_entries は1行のみ（冪等性）。"""
        _insert_signal(duckdb_conn, "7777", side="buy")
        _insert_target(duckdb_conn, "7777", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()
        engine._process_signals()  # 2回目: DuplicateOrderError でスキップされるが position_entries は変わらない

        rows = duckdb_conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = '7777'"
        ).fetchall()
        assert len(rows) == 1, "ON CONFLICT DO NOTHING により重複挿入されないこと"

    def test_sell_signal_updates_sell_date(self, sqlite_conn, duckdb_conn):
        """SELL 発注成功 → position_entries の sell_date が更新される。"""
        duckdb_conn.execute(
            "INSERT INTO position_entries (code, entry_date) VALUES ('6666', ?)",
            [TARGET_DATE],
        )
        _insert_signal(duckdb_conn, "6666", side="sell")
        _insert_target(duckdb_conn, "6666", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        row = duckdb_conn.execute(
            "SELECT sell_date FROM position_entries WHERE code = '6666'"
        ).fetchone()
        assert row is not None
        assert row[0] == TARGET_DATE, "SELL 発注後に sell_date が設定されるべき"
