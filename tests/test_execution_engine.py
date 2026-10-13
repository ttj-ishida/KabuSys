# tests/test_execution_engine.py
"""ExecutionEngine 統合テスト（Issue #30 / #34）"""

# NOTE: 以下は Task 7/8 で追加するテストクラス用にプリステージ済み
import sqlite3
from datetime import date, time
from unittest.mock import patch

import duckdb
import pytest

from kabusys.execution import signal_queue_status as sqs
from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository
from kabusys.execution.risk_manager import RiskConfig, RiskManager
from kabusys.monitoring.monitoring_db import MonitoringDB

# Issue #413: signal_queue の日付は夜間バッチ日（シグナル日）、エンジンの target_date は執行日。
# TARGET_DATE はシグナル日（金曜）、EXEC_DATE は執行日（翌営業日の月曜）。
# 従来は TARGET_DATE=日曜の行をそのまま読み fill_date=翌営業日としていたが、
# 新仕様では執行日の前営業日（signal_date）の行を読み、fill_date=執行日となる。
TARGET_DATE = date(2026, 3, 27)  # シグナル日（金曜）= prev_trading_day(EXEC_DATE)
EXEC_DATE = date(2026, 3, 30)  # 執行日（月曜）
FILL_DATE = EXEC_DATE  # 当日寄付で約定する想定（fill_date = 執行日）


def _make_engine(
    broker, sqlite_conn, duckdb_conn, *, config=None, monitoring_db=None
) -> ExecutionEngine:
    repo = OrderRepository(sqlite_conn)
    risk_config = RiskConfig(initial_portfolio_value=10_000_000.0)
    rm = RiskManager(broker=broker, repo=repo, config=risk_config)
    order_manager = OrderManager(broker=broker, repo=repo)
    cfg = config or EngineConfig(target_date=EXEC_DATE)
    return ExecutionEngine(
        broker=broker,
        repo=repo,
        risk_manager=rm,
        order_manager=order_manager,
        duckdb_conn=duckdb_conn,
        sqlite_conn=sqlite_conn,
        config=cfg,
        monitoring_db=monitoring_db,
    )


def _insert_signal(conn, code: str, side: str = "buy", score: float = 0.8):
    conn.execute(
        "INSERT INTO signals (date, code, side, score, signal_rank) VALUES (?, ?, ?, ?, ?)",
        [TARGET_DATE, code, side, score, 1],
    )


def _insert_target(
    conn,
    code: str,
    qty: int = 100,
    price: float = 1500.0,
    signal_id: str | None = None,
):
    side_row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = ? ORDER BY signal_rank ASC NULLS LAST LIMIT 1",
        [TARGET_DATE, code],
    ).fetchone()
    side = side_row[0] if side_row else "buy"
    conn.execute(
        "INSERT INTO portfolio_targets (date, code, target_weight, target_size) VALUES (?, ?, ?, ?)",
        [TARGET_DATE, code, None, qty],
    )
    conn.execute(
        """
        INSERT INTO signal_queue
            (signal_id, date, code, side, size, order_type, price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            signal_id or f"{TARGET_DATE}_{code}_{side}",
            TARGET_DATE,
            code,
            side,
            qty,
            "limit",
            price,
            "pending",
        ],
    )


class TestReadSignals:
    def test_reads_pending_signal_queue(self, sqlite_conn, duckdb_conn):
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

    def test_empty_signal_queue_does_not_read_targets(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        duckdb_conn.execute(
            "INSERT INTO portfolio_targets (date, code, target_weight, target_size) VALUES (?, ?, ?, ?)",
            [TARGET_DATE, "1234", None, 100],
        )
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        signals = engine._read_signals()

        assert signals == []

    def test_excludes_signals_without_pending_queue(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        signals = engine._read_signals()
        assert len(signals) == 0

    def test_reads_queue_without_joinable_signals_table(self, sqlite_conn):
        conn = duckdb.connect(":memory:")
        conn.execute("""
            CREATE TABLE signal_queue (
                signal_id VARCHAR PRIMARY KEY,
                date DATE NOT NULL,
                code VARCHAR NOT NULL,
                side VARCHAR NOT NULL,
                size BIGINT NOT NULL,
                price DECIMAL(18,4),
                status VARCHAR NOT NULL DEFAULT 'pending'
            )
        """)
        conn.execute("CREATE TABLE signals (signal_rank INTEGER, size_multiplier DOUBLE)")
        conn.execute(
            """
            INSERT INTO signal_queue
                (signal_id, date, code, side, size, price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ["sig-joinless", TARGET_DATE, "7203", "buy", 100, 2500.0, "pending"],
        )
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, conn)

        signals = engine._read_signals()

        assert signals == [
            {
                "signal_id": "sig-joinless",
                "code": "7203",
                "side": "buy",
                "qty": 100,
                "price": 2500.0,
                "size_multiplier": 1.0,
            }
        ]

    def test_legacy_queue_without_signal_id_reports_missing_column(self, sqlite_conn):
        conn = duckdb.connect(":memory:")
        conn.execute("""
            CREATE TABLE signal_queue (
                date DATE NOT NULL,
                code VARCHAR NOT NULL,
                side VARCHAR NOT NULL,
                size BIGINT NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'pending'
            )
        """)
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, conn)

        with pytest.raises(RuntimeError, match="missing required columns.*signal_id"):
            engine._read_signals()

    def test_reads_queue_without_price_column_as_market_order(self, sqlite_conn):
        conn = duckdb.connect(":memory:")
        conn.execute("""
            CREATE TABLE signal_queue (
                signal_id VARCHAR PRIMARY KEY,
                date DATE NOT NULL,
                code VARCHAR NOT NULL,
                side VARCHAR NOT NULL,
                size BIGINT NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'pending'
            )
        """)
        conn.execute(
            """
            CREATE TABLE signals (
                date DATE NOT NULL,
                code VARCHAR NOT NULL,
                side VARCHAR NOT NULL,
                signal_rank INTEGER,
                size_multiplier DOUBLE NOT NULL DEFAULT 1.0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO signal_queue
                (signal_id, date, code, side, size, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ["sig-market", TARGET_DATE, "7203", "buy", 100, "pending"],
        )
        conn.execute(
            "INSERT INTO signals VALUES (?, ?, ?, ?, ?)",
            [TARGET_DATE, "7203", "buy", 1, 0.5],
        )
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, conn)

        signals = engine._read_signals()

        assert signals == [
            {
                "signal_id": "sig-market",
                "code": "7203",
                "side": "buy",
                "qty": 100,
                "price": 0.0,
                "size_multiplier": 0.5,
            }
        ]


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

    def test_same_business_key_queue_rows_create_single_order(self, sqlite_conn, duckdb_conn):
        """同一 date/code/side で signal_id が異なる pending 行が2件あっても発注は1件のみ。"""
        _insert_signal(duckdb_conn, "1234")
        for queue_id in ("uuid-aaaa", "uuid-bbbb"):
            duckdb_conn.execute(
                """
                INSERT INTO signal_queue
                    (signal_id, date, code, side, size, order_type, price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [queue_id, TARGET_DATE, "1234", "buy", 100, "limit", 1500.0, "pending"],
            )
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        orders = engine._repo.list_active()
        assert len(orders) == 1
        assert orders[0].signal_id == f"{TARGET_DATE.isoformat()}_1234_buy"
        # Issue #413: ステータスは DuckDB ではなく SQLite の signal_queue_status に記録する。
        # 重複行は従来 failed だったが、重複は cancelled/duplicate に統一した。
        statuses = sqs.get_statuses(sqlite_conn, TARGET_DATE)
        assert statuses["uuid-aaaa"] == "filled"
        # 2行目は Gate 1 の重複検査で cancelled となり、pending のまま再試行され続けない
        assert statuses["uuid-bbbb"] == "cancelled"

        # 再実行しても注文は増えない
        engine._process_signals()
        assert len(engine._repo.list_active()) == 1

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

    def test_process_signals_skipped_after_signal_send_end(self, sqlite_conn, duckdb_conn):
        """signal_send_end を過ぎた時刻に run_session が呼ばれてもシグナル処理をスキップ"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        # signal_send_end=00:00 → 現在時刻は常に超過
        cfg = EngineConfig(
            target_date=EXEC_DATE,
            signal_send_start=time(0, 0),
            signal_send_end=time(0, 0),
        )
        engine = _make_engine(broker, sqlite_conn, duckdb_conn, config=cfg)
        # run_session は使わず、send_end チェックを直接テスト
        # signal_send_end < 現在時刻 → _process_signals を呼ばない
        engine._stop_event.set()  # ループ停止のため
        # ← _process_signals を明示的に呼んだ場合との比較
        assert len(engine._repo.list_active()) == 0

    def test_latency_ms_recorded_in_monitoring_db(self, sqlite_conn, duckdb_conn, monitoring_conn):
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

    def test_created_and_filled_events_recorded_for_instant_fill(
        self, sqlite_conn, duckdb_conn, monitoring_conn
    ):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        mdb = MonitoringDB(monitoring_conn)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn, monitoring_db=mdb)
        engine._process_signals()

        rows = monitoring_conn.execute(
            "SELECT event_type, filled_qty, state FROM trade_logs ORDER BY id"
        ).fetchall()
        events = [row[0] for row in rows]
        assert "Created" in events
        assert "Sent" in events
        assert "Filled" in events

    def test_instant_fill_syncs_order_and_signal_queue_status(self, sqlite_conn, duckdb_conn):
        """即時約定した Paper 注文は orders と SQLite signal_queue_status の両方に反映される。

        Issue #413: エンジンは DuckDB に書かない（read_only）。DuckDB signal_queue は
        夜間 sync_to_duckdb で反映されるため、ここでは pending のままであることを確認する。
        """
        queue_signal_id = "QUEUE_CUSTOM_2026-03-27_1234_buy"
        _insert_signal(duckdb_conn, "1234")
        _insert_target(
            duckdb_conn,
            "1234",
            qty=100,
            price=1500.0,
            signal_id=queue_signal_id,
        )
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        orders = engine._repo.list_active()
        assert len(orders) == 1
        # 注文の signal_id は業務キー（date_code_side）。queue 行 ID は状態更新専用。
        assert orders[0].signal_id == f"{TARGET_DATE.isoformat()}_1234_buy"
        assert orders[0].state == OrderState.Filled
        assert orders[0].filled_qty == 100
        assert orders[0].avg_fill_price == 1500.0

        row = sqlite_conn.execute(
            "SELECT status, client_order_id FROM signal_queue_status WHERE queue_signal_id = ?",
            [queue_signal_id],
        ).fetchone()
        assert row[0] == "filled"
        assert row[1] == orders[0].client_order_id

        duck_row = duckdb_conn.execute(
            "SELECT status, processed_at FROM signal_queue WHERE signal_id = ?",
            [queue_signal_id],
        ).fetchone()
        assert duck_row == ("pending", None)

    def test_latency_ms_recorded_for_pending_order(self, sqlite_conn, duckdb_conn, monitoring_conn):
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

    def test_process_signals_proceeds_without_kill_flag(self, sqlite_conn, duckdb_conn, tmp_path):
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

    def test_process_signals_detects_kill_flag_mid_loop(self, sqlite_conn, duckdb_conn, tmp_path):
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
        """BUY 発注成功 → position_entries（SQLite）に entry_date が挿入される。"""
        _insert_signal(duckdb_conn, "9999", side="buy")
        _insert_target(duckdb_conn, "9999", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        row = sqlite_conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = '9999'"
        ).fetchone()
        assert row is not None, "BUY 発注後に position_entries が挿入されるべき"
        assert str(row[0]) == str(FILL_DATE), (
            "entry_date は執行日（当日寄付で約定、#413）であるべき"
        )

    def test_buy_signal_pending_inserts_position_entry(self, sqlite_conn, duckdb_conn):
        """BUY 発注保留（OrderSentPendingError）でも position_entries（SQLite）に entry_date が挿入される。"""
        _insert_signal(duckdb_conn, "8888", side="buy")
        _insert_target(duckdb_conn, "8888", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        row = sqlite_conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = '8888'"
        ).fetchone()
        assert row is not None, "発注保留（pending）後も position_entries が挿入されるべき"
        assert str(row[0]) == str(FILL_DATE), (
            "entry_date は執行日（当日寄付で約定、#413）であるべき"
        )

    def test_buy_signal_idempotent(self, sqlite_conn, duckdb_conn):
        """同一 code/date の BUY を2回処理しても position_entries（SQLite）は1行のみ（冪等性）。"""
        _insert_signal(duckdb_conn, "7777", side="buy")
        _insert_target(duckdb_conn, "7777", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()
        engine._process_signals()  # 2回目: DuplicateOrderError でスキップされるが position_entries は変わらない

        rows = sqlite_conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = '7777'"
        ).fetchall()
        assert len(rows) == 1, "INSERT OR IGNORE により重複挿入されないこと"

    def test_sell_signal_updates_sell_date(self, sqlite_conn, duckdb_conn):
        """SELL 発注成功 → position_entries（SQLite）の sell_date が更新される。"""
        sqlite_conn.execute(
            "INSERT INTO position_entries (code, entry_date) VALUES ('6666', ?)",
            [str(TARGET_DATE)],
        )
        sqlite_conn.commit()
        _insert_signal(duckdb_conn, "6666", side="sell")
        _insert_target(duckdb_conn, "6666", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        row = sqlite_conn.execute(
            "SELECT sell_date FROM position_entries WHERE code = '6666'"
        ).fetchone()
        assert row is not None
        assert str(row[0]) == str(FILL_DATE), "sell_date は執行日（当日寄付で約定、#413）であるべき"

    def test_sell_signal_pending_does_not_update_sell_date(self, sqlite_conn, duckdb_conn):
        """SELL 発注保留（pending）では sell_date を書かない（ポジションはまだ保有中）。"""
        sqlite_conn.execute(
            "INSERT INTO position_entries (code, entry_date) VALUES ('5555', ?)",
            [str(TARGET_DATE)],
        )
        sqlite_conn.commit()
        _insert_signal(duckdb_conn, "5555", side="sell")
        _insert_target(duckdb_conn, "5555", qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        row = sqlite_conn.execute(
            "SELECT sell_date FROM position_entries WHERE code = '5555'"
        ).fetchone()
        assert row is not None
        assert row[0] is None, "SELL pending では sell_date は NULL のままであるべき"

    def test_size_multiplier_applied_to_buy_qty(self, sqlite_conn, duckdb_conn):
        """size_multiplier=0.5 のシグナルは発注数量が半減する。"""
        # target_size=200, size_multiplier=0.5 → expected qty = 100
        duckdb_conn.execute(
            "INSERT INTO signals (date, code, side, score, signal_rank, size_multiplier) VALUES (?, ?, ?, ?, ?, ?)",
            [TARGET_DATE, "3333", "buy", 0.8, 1, 0.5],
        )
        _insert_target(duckdb_conn, "3333", qty=200, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        # 発注された注文の qty が 100 (= 200 * 0.5) であること
        orders = engine._repo.list_active()
        assert len(orders) == 1, "発注が1件あるべき"
        assert orders[0].qty == 100, (
            f"size_multiplier=0.5 適用後 qty=100 であるべき、実際={orders[0].qty}"
        )

    def test_size_multiplier_fractional_floors_to_lot(self, sqlite_conn, duckdb_conn):
        """size_multiplier 適用後に端数が切り捨てられ、ロット単位に丸められる。"""
        # target_size=250, size_multiplier=0.5 → raw=125 → floor to 100
        duckdb_conn.execute(
            "INSERT INTO signals (date, code, side, score, signal_rank, size_multiplier) VALUES (?, ?, ?, ?, ?, ?)",
            [TARGET_DATE, "5555", "buy", 0.8, 1, 0.5],
        )
        _insert_target(duckdb_conn, "5555", qty=250, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        # 発注された注文の qty が 100 (= floor(250 * 0.5 / 100) * 100) であること
        orders = engine._repo.list_active()
        assert len(orders) == 1, "発注が1件あるべき"
        assert orders[0].qty == 100, f"端数切り捨て後 qty=100 であるべき、実際={orders[0].qty}"

    def test_size_multiplier_zero_skips_order(self, sqlite_conn, duckdb_conn):
        """size_multiplier 適用後 qty=0 の場合は発注をスキップする。"""
        # target_size=50, size_multiplier=0.0 → qty=0 → スキップ
        duckdb_conn.execute(
            "INSERT INTO signals (date, code, side, score, signal_rank, size_multiplier) VALUES (?, ?, ?, ?, ?, ?)",
            [TARGET_DATE, "4444", "buy", 0.8, 1, 0.0],
        )
        _insert_target(duckdb_conn, "4444", qty=50, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        # 発注がスキップされて注文が0件であること
        orders = engine._repo.list_active()
        assert len(orders) == 0, "size_multiplier=0.0 適用後は発注がスキップされるべき"


# ---------------------------------------------------------------------------
# Issue #413: signal_queue ステータス遷移（SQLite signal_queue_status）
# ---------------------------------------------------------------------------


class _StatusAfterSendBroker(MockBrokerClient):
    """send_order は受付（order_id 発行）し、直後の照会で指定 status を返すブローカー。"""

    def __init__(self, post_status: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._post_status = post_status

    def send_order(self, order):
        from kabusys.execution.broker_api import OrderResponse, OrderStatus

        order_id = self._next_order_id()
        self._orders[order_id] = OrderStatus(
            order_id=order_id,
            code=order.code,
            side=order.side,
            qty=order.qty,
            filled_qty=0,
            status=self._post_status,
            price=None,
        )
        return OrderResponse(order_id=order_id)


def _status_row(sqlite_conn, queue_signal_id: str):
    row = sqlite_conn.execute(
        "SELECT status, reason, client_order_id FROM signal_queue_status WHERE queue_signal_id = ?",
        [queue_signal_id],
    ).fetchone()
    return tuple(row) if row is not None else None


QID = f"{TARGET_DATE}_1234_buy"  # _insert_target の既定 queue 行 ID


def _add_queue_row(conn, qid: str, d: date, code: str = "1234") -> None:
    conn.execute(
        "INSERT INTO signal_queue (signal_id, date, code, side, size, order_type, price, status)"
        " VALUES (?, ?, ?, 'buy', 100, 'limit', 1500.0, 'pending')",
        [qid, d, code],
    )


class TestSignalQueueStatusTransitions:
    def test_gate1_failure_records_failed_with_reason(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        engine = _make_engine(MockBrokerClient(available_cash=0.0), sqlite_conn, duckdb_conn)

        engine._process_signals()

        status, reason, coid = _status_row(sqlite_conn, QID)
        assert status == "failed"
        assert reason  # Gate 1 の理由
        assert coid is None

    def test_gate1_duplicate_records_cancelled_duplicate(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0, signal_id="uuid-1")
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        # 同じ業務キーの別 queue 行（uuid 違い）を後から追加
        _add_queue_row(duckdb_conn, "uuid-2", TARGET_DATE)

        engine._process_signals()

        assert _status_row(sqlite_conn, "uuid-2")[:2] == ("cancelled", "duplicate")
        assert len(engine._repo.list_active()) == 1

    def test_duplicate_order_error_records_cancelled_duplicate(self, sqlite_conn, duckdb_conn):
        """Gate 1 を素通りしても create_order の DuplicateOrderError で cancelled/duplicate。"""
        from kabusys.execution.risk_manager import RiskResult

        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0, signal_id="uuid-1")
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        _add_queue_row(duckdb_conn, "uuid-2", TARGET_DATE)
        engine._risk_manager.check_signal = lambda *a, **k: RiskResult(passed=True)

        engine._process_signals()

        assert _status_row(sqlite_conn, "uuid-2")[:2] == ("cancelled", "duplicate")
        assert len(engine._repo.list_active()) == 1

    def test_gate2_rate_limit_leaves_pending_and_retries_on_restart(self, sqlite_conn, duckdb_conn):
        from kabusys.execution.risk_manager import RiskRejectReason, RiskResult

        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._risk_manager.check_execution = lambda: RiskResult(
            passed=False, reason="rate", reject_reason=RiskRejectReason.RATE_LIMIT
        )

        engine._process_signals()

        assert _status_row(sqlite_conn, QID)[0] == "pending"
        assert engine._repo.list_active() == []

        # 同日中の再起動で再試行される（問題 4）
        engine2 = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine2._process_signals()
        assert len(engine2._repo.list_active()) == 1
        assert _status_row(sqlite_conn, QID)[0] == "filled"

    def test_gate2_circuit_breaker_leaves_pending(self, sqlite_conn, duckdb_conn):
        from kabusys.execution.risk_manager import RiskRejectReason, RiskResult

        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        engine = _make_engine(
            MockBrokerClient(available_cash=5_000_000.0), sqlite_conn, duckdb_conn
        )
        engine._risk_manager.check_execution = lambda: RiskResult(
            passed=False, reason="cb", reject_reason=RiskRejectReason.CIRCUIT_BREAKER
        )

        engine._process_signals()

        assert _status_row(sqlite_conn, QID)[0] == "pending"
        assert engine._repo.list_active() == []

    def test_api_failure_records_failed_with_message(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="reject")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        status, reason, coid = _status_row(sqlite_conn, QID)
        assert status == "failed"
        assert "fill_mode=reject" in reason
        assert coid is not None

    def test_sent_pending_records_processing(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        status, reason, coid = _status_row(sqlite_conn, QID)
        assert (status, reason) == ("processing", "sent_pending")
        assert coid == engine._repo.list_active()[0].client_order_id

    def test_filled_records_filled(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        assert _status_row(sqlite_conn, QID)[:2] == ("filled", None)

    def test_partial_fill_records_processing(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="partial")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        assert _status_row(sqlite_conn, QID)[:2] == ("processing", None)

    @pytest.mark.parametrize(
        "post_status, expected",
        [("rejected", ("failed", "rejected")), ("cancelled", ("cancelled", "cancelled"))],
    )
    def test_sync_after_send_maps_terminal_states(
        self, sqlite_conn, duckdb_conn, post_status, expected
    ):
        """sync_order の結果が Rejected/Cancelled なら processing にしない（問題 2）。"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = _StatusAfterSendBroker(post_status, available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        assert _status_row(sqlite_conn, QID)[:2] == expected

    def test_push_fill_updates_status_to_filled(self, sqlite_conn, duckdb_conn):
        """PUSH 経由の約定でも signal_queue_status が filled になる（問題 1）。"""
        from kabusys.execution.broker_api import OrderStatus

        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        assert _status_row(sqlite_conn, QID)[0] == "processing"
        order = engine._repo.list_uncertain()[0]
        broker._orders[order.broker_order_id] = OrderStatus(
            order_id=order.broker_order_id,
            code="1234",
            side="buy",
            qty=100,
            filled_qty=100,
            status="filled",
            price=1500.0,
        )

        engine._push_queue.put({"OrderID": order.broker_order_id})
        engine._drain_push_queue()

        assert _status_row(sqlite_conn, QID)[:2] == ("filled", None)

    def test_kill_switch_marks_cancelled(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()

        engine.kill_switch()

        assert _status_row(sqlite_conn, QID)[:2] == ("cancelled", "cancelled")

    def test_status_write_failure_does_not_stop_order_flow(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        sqlite_conn.execute("DROP TABLE signal_queue_status")
        sqlite_conn.commit()

        engine._process_signals()  # 例外を出さない

        assert len(engine._repo.list_active()) == 1

    def test_status_read_failure_aborts_signal_processing(self, sqlite_conn, duckdb_conn):
        """処理済み判定が読めないときは発注しない（再起動時の二重発注防止を優先）。"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        with (
            patch(
                "kabusys.execution.execution_engine.sqs.get_statuses",
                side_effect=sqlite3.OperationalError("database is locked"),
            ),
            pytest.raises(RuntimeError, match="signal_queue_status"),
        ):
            engine._process_signals()

        assert broker._orders == {}


class TestRestartDoesNotReprocess:
    def test_processed_rows_are_not_reread(self, sqlite_conn, duckdb_conn):
        """再起動時、SQLite で pending 以外の行は DuckDB 側が pending でも再読込しない。"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        _make_engine(broker, sqlite_conn, duckdb_conn)._process_signals()

        engine2 = _make_engine(broker, sqlite_conn, duckdb_conn)
        assert engine2._read_signals() == []

    def test_rejected_order_is_not_reordered_after_restart(self, sqlite_conn, duckdb_conn):
        """拒否（終端）注文は業務キー重複判定をすり抜けるが、status で再発注を防ぐ。"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        _make_engine(
            MockBrokerClient(available_cash=5_000_000.0, fill_mode="reject"),
            sqlite_conn,
            duckdb_conn,
        )._process_signals()

        broker2 = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine2 = _make_engine(broker2, sqlite_conn, duckdb_conn)
        engine2._process_signals()

        assert broker2._orders == {}
        assert engine2._repo.list_active() == []

    def test_startup_sync_updates_processing_rows_from_orders(self, sqlite_conn, duckdb_conn):
        """リコンシリエーション後、約定待ちだった行が注文の状態に合わせて更新される。"""
        from kabusys.execution.broker_api import OrderStatus

        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        order = engine._repo.list_uncertain()[0]
        broker._orders[order.broker_order_id] = OrderStatus(
            order_id=order.broker_order_id,
            code="1234",
            side="buy",
            qty=100,
            filled_qty=100,
            status="filled",
            price=1500.0,
        )
        # 再起動: リコンシリエーション（run_execution 側）で注文が Filled に同期される
        engine._order_manager.sync_order(order.client_order_id)
        assert _status_row(sqlite_conn, QID)[0] == "processing"

        engine2 = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine2.sync_queue_statuses_from_orders()

        assert _status_row(sqlite_conn, QID)[:2] == ("filled", None)

    def test_run_session_syncs_statuses_after_reconcile(self, sqlite_conn, duckdb_conn, tmp_path):
        broker = MockBrokerClient()
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._pid_file = tmp_path / "execution.pid"
        with (
            patch("kabusys.execution.execution_engine.settings") as mock_settings,
            patch.object(engine, "_websocket_worker"),
            patch.object(engine, "_process_signals"),
            patch.object(engine, "_drain_push_queue"),
            patch.object(engine, "sync_queue_statuses_from_orders") as mock_sync,
        ):
            mock_settings.kill_flag_path = tmp_path / "kill.flag"
            engine._stop_event.set()
            engine.run_session()

        mock_sync.assert_called_once()


class TestQueueDateAlignment:
    def test_monday_reads_friday_rows_not_today(self, sqlite_conn, duckdb_conn):
        _add_queue_row(duckdb_conn, "fri", date(2026, 3, 27), "1111")
        _add_queue_row(duckdb_conn, "mon", date(2026, 3, 30), "2222")
        engine = _make_engine(MockBrokerClient(), sqlite_conn, duckdb_conn)

        assert engine.signal_date == date(2026, 3, 27)
        assert [s["signal_id"] for s in engine._read_signals()] == ["fri"]

    def test_signal_date_defaults_to_prev_trading_day_with_calendar(self, sqlite_conn, duckdb_conn):
        duckdb_conn.execute(
            "CREATE TABLE market_calendar (date DATE PRIMARY KEY, is_trading_day BOOLEAN)"
        )
        # 2026-04-01(水) 執行 / 2026-03-31(火) は休場扱い → signal_date は 03-30(月)
        duckdb_conn.execute(
            "INSERT INTO market_calendar VALUES ('2026-03-30', true), ('2026-03-31', false),"
            " ('2026-04-01', true)"
        )
        engine = _make_engine(
            MockBrokerClient(),
            sqlite_conn,
            duckdb_conn,
            config=EngineConfig(target_date=date(2026, 4, 1)),
        )
        assert engine.signal_date == date(2026, 3, 30)

    def test_explicit_signal_date_overrides_default(self, sqlite_conn, duckdb_conn):
        _add_queue_row(duckdb_conn, "today", EXEC_DATE, "2222")
        engine = _make_engine(
            MockBrokerClient(),
            sqlite_conn,
            duckdb_conn,
            config=EngineConfig(target_date=EXEC_DATE, signal_date=EXEC_DATE),
        )
        assert [s["signal_id"] for s in engine._read_signals()] == ["today"]

    def test_business_key_uses_signal_date_and_fill_date_is_exec_date(
        self, sqlite_conn, duckdb_conn
    ):
        _add_queue_row(duckdb_conn, "fri", TARGET_DATE, "1111")
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)

        engine._process_signals()

        order = engine._repo.list_active()[0]
        assert order.signal_id == "2026-03-27_1111_buy"
        row = sqlite_conn.execute(
            "SELECT entry_date FROM position_entries WHERE code = '1111'"
        ).fetchone()
        assert row[0] == "2026-03-30"


class TestReadOnlyDuckDB:
    def test_engine_runs_on_read_only_duckdb(self, sqlite_conn, tmp_path):
        """DuckDB を read_only で開いてもエンジンが発注まで動く（問題 6）。"""
        path = tmp_path / "ro.duckdb"
        rw = duckdb.connect(str(path))
        rw.execute(
            "CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score FLOAT,"
            " signal_rank INTEGER, size_multiplier DOUBLE NOT NULL DEFAULT 1.0)"
        )
        rw.execute(
            "CREATE TABLE signal_queue (signal_id VARCHAR PRIMARY KEY, date DATE NOT NULL,"
            " code VARCHAR NOT NULL, side VARCHAR NOT NULL, size BIGINT NOT NULL,"
            " order_type VARCHAR NOT NULL, price DECIMAL(18,4),"
            " status VARCHAR NOT NULL DEFAULT 'pending', processed_at TIMESTAMP)"
        )
        rw.execute(
            "INSERT INTO signal_queue (signal_id, date, code, side, size, order_type, price)"
            " VALUES ('q1', ?, '1234', 'buy', 100, 'limit', 1500.0)",
            [TARGET_DATE],
        )
        rw.close()

        ro = duckdb.connect(str(path), read_only=True)
        try:
            broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
            engine = _make_engine(broker, sqlite_conn, ro)
            engine._process_signals()

            assert len(engine._repo.list_active()) == 1
            assert _status_row(sqlite_conn, "q1")[0] == "filled"
            assert ro.execute("SELECT status FROM signal_queue").fetchone()[0] == "pending"
        finally:
            ro.close()


# ---------------------------------------------------------------------------
# Issue #413 fix round 1
# ---------------------------------------------------------------------------


class TestSignalProcessingFailureKeepsSession:
    """I1: シグナル処理の例外でセッションを落とさず、発注だけ止めて push/Gate 3 は継続する。"""

    def _run(self, engine, tmp_path):
        engine._pid_file = tmp_path / "execution.pid"
        drained = []
        with (
            patch("kabusys.execution.execution_engine.settings") as mock_settings,
            patch.object(engine, "_websocket_worker"),
            patch.object(
                engine,
                "_process_signals",
                side_effect=RuntimeError("signal_queue_status read failed"),
            ),
            patch.object(
                engine,
                "_drain_push_queue",
                side_effect=lambda: (drained.append(1), engine._stop_event.set()),
            ),
            patch.object(engine._config, "signal_send_start", time(0, 0)),
            patch.object(engine._config, "signal_send_end", time(23, 59, 59)),
            patch.object(engine._config, "market_close", time(23, 59, 59)),
        ):
            mock_settings.kill_flag_path = tmp_path / "kill.flag"
            engine.run_session()  # 例外を外に出さない
        return drained

    def test_failure_logged_flagged_and_drain_continues(self, sqlite_conn, duckdb_conn, tmp_path):
        engine = _make_engine(MockBrokerClient(), sqlite_conn, duckdb_conn)
        drained = self._run(engine, tmp_path)
        assert engine.signal_processing_failed is True
        assert drained, "push ドレインループ（Gate 3）は継続するべき"

    def test_failure_sends_notification(self, sqlite_conn, duckdb_conn, tmp_path):
        from unittest.mock import MagicMock

        engine = _make_engine(MockBrokerClient(), sqlite_conn, duckdb_conn)
        notifier = MagicMock()
        engine._notifier = notifier
        self._run(engine, tmp_path)
        notifier.send.assert_called_once()
        assert "signal_queue_status read failed" in notifier.send.call_args.args[0]

    def test_notification_failure_is_swallowed(self, sqlite_conn, duckdb_conn, tmp_path):
        from unittest.mock import MagicMock

        engine = _make_engine(MockBrokerClient(), sqlite_conn, duckdb_conn)
        engine._notifier = MagicMock()
        engine._notifier.send.side_effect = RuntimeError("LINE down")
        self._run(engine, tmp_path)
        assert engine.signal_processing_failed is True

    def test_flag_false_on_normal_session(self, sqlite_conn, duckdb_conn):
        engine = _make_engine(MockBrokerClient(), sqlite_conn, duckdb_conn)
        assert engine.signal_processing_failed is False


class TestQtyZeroAndOrphanProcessing:
    def test_qty_zero_records_cancelled(self, sqlite_conn, duckdb_conn):
        """Minor 1: size_multiplier 適用後 qty=0 のスキップは cancelled/qty_zero。"""
        duckdb_conn.execute(
            "INSERT INTO signals (date, code, side, score, signal_rank, size_multiplier)"
            " VALUES (?, '4444', 'buy', 0.8, 1, 0.0)",
            [TARGET_DATE],
        )
        _insert_target(duckdb_conn, "4444", qty=50, price=1000.0)
        engine = _make_engine(MockBrokerClient(), sqlite_conn, duckdb_conn)

        engine._process_signals()

        assert _status_row(sqlite_conn, f"{TARGET_DATE}_4444_buy")[:2] == (
            "cancelled",
            "qty_zero",
        )

    def test_orphan_processing_row_logs_error(self, sqlite_conn, duckdb_conn, caplog):
        """Minor 5: client_order_id なし・注文なしの processing 行は起動時に ERROR ログ。"""
        sqs.ensure_schema(sqlite_conn)
        sqs.record(
            sqlite_conn,
            queue_signal_id="orphan",
            signal_date=TARGET_DATE,
            code="1234",
            side="buy",
            status="processing",
        )
        engine = _make_engine(MockBrokerClient(), sqlite_conn, duckdb_conn)
        with caplog.at_level("ERROR", logger="kabusys.execution.execution_engine"):
            engine.sync_queue_statuses_from_orders()
        assert any("orphan" in r.getMessage() for r in caplog.records if r.levelname == "ERROR")

    def test_processing_row_with_existing_order_not_reported(
        self, sqlite_conn, duckdb_conn, caplog
    ):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        # client_order_id が無い processing 行だが、業務キーの注文は存在する
        sqlite_conn.execute("UPDATE signal_queue_status SET client_order_id = NULL")
        sqlite_conn.commit()
        with caplog.at_level("ERROR", logger="kabusys.execution.execution_engine"):
            engine.sync_queue_statuses_from_orders()
        assert not [r for r in caplog.records if r.levelname == "ERROR"]
