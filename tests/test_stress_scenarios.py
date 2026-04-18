# tests/test_stress_scenarios.py
"""Issue #52 — ストレステスト・シナリオテスト

極端な市場状況でのシステム動作を検証する。

シナリオ:
  1. マーケットクラッシュ  — 急落によるドローダウン超過・KillSwitch 発動・発注ブロック
  2. API 接続遮断          — 連続 API エラー・サーキットブレーカー・レート制限・回復パス
  3. 流動性枯渇            — 発注拒否・未約定継続・部分約定・現金枯渇による発注停止
"""

from __future__ import annotations

import sqlite3

import pytest

from kabusys.execution.broker_api import Position
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.risk_manager import RiskConfig, RiskManager, RiskRejectReason
from kabusys.monitoring.kill_switch import KillSwitch
from kabusys.monitoring.risk_monitor import RiskCheckResult
from kabusys.monitoring.system_monitor import SystemCheckResult
from kabusys.monitoring.trade_monitor import TradeCheckResult


# ---------------------------------------------------------------------------
# 共通フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def sqlite_conn():
    conn = sqlite3.connect(":memory:")
    init_orders_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(sqlite_conn):
    return OrderRepository(sqlite_conn)


def _make_risk_manager(
    broker: MockBrokerClient,
    repo: OrderRepository,
    initial_portfolio_value: float = 10_000_000.0,
    max_drawdown: float = 0.15,
    circuit_breaker_errors: int = 5,
    circuit_breaker_window_sec: int = 60,
    rate_limit_per_sec: int = 5,
    max_utilization: float = 0.80,
    max_position_pct: float = 0.10,
) -> RiskManager:
    config = RiskConfig(
        initial_portfolio_value=initial_portfolio_value,
        max_drawdown=max_drawdown,
        circuit_breaker_errors=circuit_breaker_errors,
        circuit_breaker_window_sec=circuit_breaker_window_sec,
        rate_limit_per_sec=rate_limit_per_sec,
        max_utilization=max_utilization,
        max_position_pct=max_position_pct,
    )
    return RiskManager(broker=broker, repo=repo, config=config)


def _make_sys_check(process_ok: bool = True) -> SystemCheckResult:
    return SystemCheckResult(
        recorded_at="2026-04-18T09:00:00+09:00",
        cpu_percent=30.0,
        memory_percent=50.0,
        disk_percent=40.0,
        process_ok=process_ok,
        data_freshness_ok=True,
        stale_pid_detected=False,
    )


def _make_trade_check() -> TradeCheckResult:
    return TradeCheckResult(
        logged_at="2026-04-18T09:00:00+09:00",
        stale_orders=[],
        anomaly_fills=[],
    )


def _make_risk_check(
    drawdown_pct: float = 0.0,
    drawdown_alert: bool = False,
    position_limit_alert: bool = False,
) -> RiskCheckResult:
    return RiskCheckResult(
        logged_at="2026-04-18T09:00:00+09:00",
        drawdown_pct=drawdown_pct,
        drawdown_alert=drawdown_alert,
        position_count=5,
        position_limit_alert=position_limit_alert,
    )


# ===========================================================================
# シナリオ 1: マーケットクラッシュ
# ===========================================================================


class TestMarketCrashScenario:
    """急激な株価下落によるドローダウン超過・KillSwitch 発動・発注ブロックを検証する。"""

    def test_moderate_drawdown_does_not_block(self, repo):
        """5% ドローダウン（< 15% 閾値）は発注ブロックしない。"""
        broker = MockBrokerClient(available_cash=5_000_000.0)
        rm = _make_risk_manager(broker, repo, initial_portfolio_value=10_000_000.0)
        # 10M → 9.5M = 5% ドローダウン
        result = rm.check_metrics(current_portfolio_value=9_500_000.0)
        assert result.passed

    def test_severe_crash_triggers_drawdown_limit(self, repo):
        """20% ドローダウン（> 15% 閾値）でチェックが失敗する。"""
        broker = MockBrokerClient(available_cash=5_000_000.0)
        rm = _make_risk_manager(
            broker, repo, initial_portfolio_value=10_000_000.0, max_drawdown=0.15
        )
        # 10M → 8M = 20% ドローダウン
        result = rm.check_metrics(current_portfolio_value=8_000_000.0)
        assert not result.passed
        assert result.reject_reason == RiskRejectReason.DRAWDOWN_LIMIT

    def test_crash_at_exact_threshold_still_passes(self, repo):
        """ちょうど 15% のドローダウンは通過する。

        実装は `drawdown > max_drawdown`（厳密な大なり）のため、
        == は False → RiskResult(True) を返す。
        """
        broker = MockBrokerClient(available_cash=5_000_000.0)
        rm = _make_risk_manager(
            broker, repo, initial_portfolio_value=10_000_000.0, max_drawdown=0.15
        )
        # 10M → 8.5M = ちょうど 15% ドローダウン
        result = rm.check_metrics(current_portfolio_value=8_500_000.0)
        assert result.passed is True

    def test_kill_switch_activates_on_severe_crash(self, tmp_path):
        """急落アラートで KillSwitch が kill.flag を書き込む。"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys_check(),
            _make_trade_check(),
            _make_risk_check(drawdown_pct=0.20, drawdown_alert=True),
        )
        assert reason is not None
        assert (tmp_path / "kill.flag").exists()

    def test_new_orders_blocked_after_kill_switch(self, tmp_path, repo):
        """KillSwitch 発動後、kill.flag が存在する状態では Gate 1 が通過しても
        実際の運用フローでは発注をスキップすることを確認する（flag 存在検証）。"""
        flag_path = tmp_path / "kill.flag"
        ks = KillSwitch(flag_path=flag_path)
        # 急落アラートで発動
        ks.evaluate(
            _make_sys_check(),
            _make_trade_check(),
            _make_risk_check(drawdown_pct=0.25, drawdown_alert=True),
        )
        # flag が存在することで実行エンジンが発注をスキップする
        assert flag_path.exists()
        assert ks.is_flagged()

    def test_kill_switch_idempotent_on_repeated_crashes(self, tmp_path):
        """複数回のクラッシュ評価でも kill.flag が更新されない（冪等）。

        ファイル内容ではなく mtime_ns の不変性で検証することで、
        将来の内容フォーマット変更（タイムスタンプ追記等）への耐性を確保する。
        """
        flag_path = tmp_path / "kill.flag"
        ks = KillSwitch(flag_path=flag_path)
        # 1 回目
        ks.evaluate(
            _make_sys_check(),
            _make_trade_check(),
            _make_risk_check(drawdown_pct=0.20, drawdown_alert=True),
        )
        mtime_after_first = flag_path.stat().st_mtime_ns
        # 2 回目（さらに急落）
        ks.evaluate(
            _make_sys_check(),
            _make_trade_check(),
            _make_risk_check(drawdown_pct=0.30, drawdown_alert=True),
        )
        assert flag_path.stat().st_mtime_ns == mtime_after_first

    def test_positions_still_held_after_crash(self, repo):
        """クラッシュ後も保有ポジションはそのまま維持される（強制清算しない）。"""
        positions = [
            Position(code="1234", qty=500, avg_price=2000.0, current_price=1500.0),
            Position(code="5678", qty=300, avg_price=3000.0, current_price=2200.0),
        ]
        broker = MockBrokerClient(
            available_cash=3_000_000.0, initial_positions=positions
        )
        rm = _make_risk_manager(broker, repo, initial_portfolio_value=10_000_000.0)
        # ドローダウン超過チェック
        rm.check_metrics(current_portfolio_value=8_000_000.0)
        # ポジションはそのまま
        held = broker.get_positions()
        assert len(held) == 2
        codes = {p.code for p in held}
        assert codes == {"1234", "5678"}

    def test_signal_blocked_due_to_utilization_during_crash(self, repo):
        """クラッシュ後、ポジション評価額が全体上限に近い状態での新規発注は拒否される。

        900株 × 9,000円 = 8,100,000円。追加300,000円 → 合計8,400,000円 > 8,000,000円（80%）
        """
        big_pos = Position(code="9999", qty=900, avg_price=9000.0, current_price=9000.0)
        broker = MockBrokerClient(available_cash=500_000.0, initial_positions=[big_pos])
        rm = _make_risk_manager(
            broker, repo, initial_portfolio_value=10_000_000.0, max_utilization=0.80
        )
        result = rm.check_signal("2026-04-18_1111_buy", "1111", order_value=300_000.0)
        assert not result.passed
        assert result.reject_reason == RiskRejectReason.UTILIZATION_LIMIT


# ===========================================================================
# シナリオ 2: API 接続遮断
# ===========================================================================


class TestAPIConnectionDisruptionScenario:
    """API 連続エラーによるサーキットブレーカー・レート制限・回復を検証する。"""

    def test_single_api_error_does_not_open_circuit(self, repo):
        """1 件のエラーではサーキットブレーカーは開かない。"""
        broker = MockBrokerClient()
        rm = _make_risk_manager(broker, repo, circuit_breaker_errors=5)
        rm.record_api_error()
        result = rm.check_execution()
        assert result.passed

    def test_circuit_breaker_opens_after_threshold_errors(self, repo):
        """閾値（5 件）のエラー後にサーキットブレーカーが OPEN になる。"""
        broker = MockBrokerClient()
        rm = _make_risk_manager(broker, repo, circuit_breaker_errors=5)
        for _ in range(5):
            rm.record_api_error()
        result = rm.check_execution()
        assert not result.passed
        assert result.reject_reason == RiskRejectReason.CIRCUIT_BREAKER

    def test_circuit_breaker_blocks_all_orders_when_open(self, repo):
        """サーキットブレーカー OPEN 中は複数の発注試行がすべてブロックされる。"""
        broker = MockBrokerClient()
        rm = _make_risk_manager(broker, repo, circuit_breaker_errors=3)
        for _ in range(3):
            rm.record_api_error()
        # 連続 5 回の発注試行がすべて失敗（60 秒ウィンドウ内のため HALF_OPEN に遷移しない）
        blocked_count = sum(1 for _ in range(5) if not rm.check_execution().passed)
        assert blocked_count == 5

    def test_rate_limiter_blocks_burst_requests(self, repo):
        """レート制限（3件/秒）を超えるバースト発注は拒否される。"""
        broker = MockBrokerClient()
        rm = _make_risk_manager(broker, repo, rate_limit_per_sec=3)
        # 3 件まで通過
        for _ in range(3):
            assert rm.check_execution().passed
        # 4 件目は拒否
        result = rm.check_execution()
        assert not result.passed
        assert result.reject_reason == RiskRejectReason.RATE_LIMIT

    def test_rate_limiter_burst_then_sustained_high_volume(self, repo):
        """バースト後に追加リクエストが続いても安全に拒否され続ける。"""
        broker = MockBrokerClient()
        rm = _make_risk_manager(broker, repo, rate_limit_per_sec=2)
        # バースト消費
        for _ in range(2):
            rm.check_execution()
        # 追加 10 件 - すべて拒否されることを確認
        rejected = sum(1 for _ in range(10) if not rm.check_execution().passed)
        assert rejected == 10

    def test_circuit_breaker_recovery_half_open_allows_probe(self, repo):
        """ウィンドウ経過後、HALF_OPEN で 1 件のプローブ発注が許可される。"""
        broker = MockBrokerClient()
        rm = _make_risk_manager(
            broker, repo, circuit_breaker_errors=2, circuit_breaker_window_sec=0
        )
        rm.record_api_error()
        rm.record_api_error()
        rm.check_execution()  # OPEN: observed=True
        rm.check_execution()  # OPEN → HALF_OPEN 遷移 (False)
        probe = rm.check_execution()  # HALF_OPEN: プローブ許可
        assert probe.passed

    def test_circuit_breaker_closes_after_successful_probe(self, repo):
        """プローブ成功後にサーキットブレーカーが CLOSED に戻る。"""
        broker = MockBrokerClient()
        rm = _make_risk_manager(
            broker, repo, circuit_breaker_errors=2, circuit_breaker_window_sec=0
        )
        rm.record_api_error()
        rm.record_api_error()
        rm.check_execution()  # OPEN: observed=True
        rm.check_execution()  # HALF_OPEN 遷移
        rm.check_execution()  # HALF_OPEN プローブ許可
        rm.record_api_success()  # 成功通知 → CLOSED
        # 通常発注が全て通過する
        for _ in range(3):
            assert rm.check_execution().passed

    def test_simultaneous_circuit_breaker_and_drawdown(self, tmp_path, repo):
        """API 遮断とドローダウン超過が同時に発生した場合、両方のガードが機能する。"""
        broker = MockBrokerClient(available_cash=5_000_000.0)
        rm = _make_risk_manager(
            broker,
            repo,
            initial_portfolio_value=10_000_000.0,
            circuit_breaker_errors=3,
        )
        # API エラーでサーキットブレーカーを開く
        for _ in range(3):
            rm.record_api_error()
        cb_result = rm.check_execution()
        assert not cb_result.passed

        # ドローダウン超過
        dd_result = rm.check_metrics(current_portfolio_value=7_000_000.0)
        assert not dd_result.passed

        # KillSwitch も発動
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys_check(),
            _make_trade_check(),
            _make_risk_check(drawdown_pct=0.30, drawdown_alert=True),
        )
        assert reason is not None
        assert (tmp_path / "kill.flag").exists()


# ===========================================================================
# シナリオ 3: 流動性枯渇
# ===========================================================================


class TestLiquidityExhaustionScenario:
    """発注拒否・未約定継続・部分約定・現金枯渇による発注停止を検証する。"""

    def test_all_orders_rejected_by_broker(self, repo):
        """ブローカーが全発注を拒否する場合、send_order は Rejected 状態を返す。"""
        from kabusys.execution.broker_api import OrderRequest

        broker = MockBrokerClient(fill_mode="reject")
        om = OrderManager(broker=broker, repo=repo)
        request = OrderRequest(
            code="1234", side="buy", qty=100, order_type="market", price=0.0
        )
        # create_order は broker 呼び出し前なので正常に作成される
        record = om.create_order("2026-04-18_1234_buy_001", request)
        assert record.state == OrderState.OrderCreated

        # send_order: OrderRejectedError は内部でキャッチされ Rejected 状態を返す
        result = om.send_order(record.client_order_id)
        assert result.state == OrderState.Rejected

    def test_pending_order_blocks_duplicate_creation(self, repo):
        """未約定保留中の注文がある場合、同一 signal_id での再作成が DuplicateOrderError になる。

        fill_mode='never' では注文が OrderSent 状態で保留される（active 扱い）。
        active 注文（OrderSent 等）がある場合は DuplicateOrderError になる。
        """
        from kabusys.execution.broker_api import OrderRequest
        from kabusys.execution.order_manager import DuplicateOrderError

        broker = MockBrokerClient(fill_mode="never")  # OrderSent 状態で止まる
        om = OrderManager(broker=broker, repo=repo)

        signal_id = "2026-04-18_1234_buy"
        request = OrderRequest(
            code="1234", side="buy", qty=100, order_type="market", price=0.0
        )

        from kabusys.execution.broker_api import OrderSentPendingError

        # 1 回目: 注文作成 → OrderSent（never fill → active のまま）
        record1 = om.create_order(signal_id, request)
        with pytest.raises(OrderSentPendingError):
            om.send_order(record1.client_order_id)

        # 2 回目: 同一 signal_id で再試行 → active 注文あり → DuplicateOrderError
        with pytest.raises(DuplicateOrderError):
            om.create_order(signal_id, request)

    def test_never_fill_orders_remain_pending(self, repo):
        """fill_mode='never' でブローカーが約定させない場合、注文は OrderSent 状態を維持する。

        send_order は OrderSentPendingError を呼び出し元へ伝播させる。
        DB には OrderSent 状態 + broker_order_id が保存される（Reconciliation 対象）。
        """
        from kabusys.execution.broker_api import OrderRequest, OrderSentPendingError

        broker = MockBrokerClient(fill_mode="never")
        om = OrderManager(broker=broker, repo=repo)
        request = OrderRequest(
            code="5678", side="buy", qty=200, order_type="market", price=0.0
        )
        record = om.create_order("2026-04-18_5678_buy", request)
        with pytest.raises(OrderSentPendingError):
            om.send_order(record.client_order_id)

        # DB の状態を確認: OrderSent で保留中
        records = repo.get_by_signal("2026-04-18_5678_buy")
        assert len(records) == 1
        assert records[0].state == OrderState.OrderSent
        assert records[0].broker_order_id is not None  # broker_order_id は保存済み

    def test_partial_fill_leaves_remaining_qty_unfilled(self, repo):
        """部分約定シナリオでは broker 内でポジションが半数約定し、残りは未約定のまま。

        fill_mode='partial': qty=100 → filled_qty=50, status='partial'
        OrderAccepted に遷移後 sync_order で PartialFill に更新される。
        """
        from kabusys.execution.broker_api import OrderRequest

        broker = MockBrokerClient(fill_mode="partial", available_cash=5_000_000.0)
        om = OrderManager(broker=broker, repo=repo)
        request = OrderRequest(
            code="9012", side="buy", qty=100, order_type="limit", price=1500.0
        )
        record = om.create_order("2026-04-18_9012_buy", request)
        sent = om.send_order(record.client_order_id)
        # partial fill は OrderAccepted に遷移（sync_order 前なので PartialFill ではない）
        assert sent.state == OrderState.OrderAccepted

        # broker 内でポジションが部分的に作成されている（50 株）
        positions = broker.get_positions()
        pos_9012 = next((p for p in positions if p.code == "9012"), None)
        assert pos_9012 is not None
        assert pos_9012.qty == 50  # 100 // 2 = 50 株約定

        # sync_order で PartialFill に遷移
        synced = om.sync_order(sent.client_order_id)
        assert synced.state == OrderState.PartialFill
        assert synced.filled_qty == 50

    def test_cash_depletion_blocks_new_buy_orders(self, repo):
        """現金がほぼ枯渇した場合、余力不足で新規買い注文がブロックされる。"""
        broker = MockBrokerClient(available_cash=10_000.0)
        rm = _make_risk_manager(broker, repo, initial_portfolio_value=10_000_000.0)
        # 100,000 円の発注は余力不足で失敗
        result = rm.check_signal("2026-04-18_3456_buy", "3456", order_value=100_000.0)
        assert not result.passed
        assert result.reject_reason == RiskRejectReason.INSUFFICIENT_CASH

    def test_cash_depletion_does_not_block_sell_orders(self, repo):
        """現金枯渇中でも売り注文はブロックされない（ポジション解消のため）。"""
        broker = MockBrokerClient(available_cash=0.0)
        rm = _make_risk_manager(broker, repo, initial_portfolio_value=10_000_000.0)
        result = rm.check_signal(
            "2026-04-18_3456_sell", "3456", order_value=500_000.0, side="sell"
        )
        assert result.passed

    def test_multiple_low_liquidity_rejections_trigger_circuit_breaker(self, repo):
        """流動性枯渇による連続 API エラーがサーキットブレーカーを発動させる。"""
        broker = MockBrokerClient(fill_mode="reject")
        rm = _make_risk_manager(broker, repo, circuit_breaker_errors=3)
        # API エラーを連続で記録（流動性枯渇による発注拒否を模倣）
        for _ in range(3):
            rm.record_api_error()
        result = rm.check_execution()
        assert not result.passed
        assert result.reject_reason == RiskRejectReason.CIRCUIT_BREAKER

    def test_position_limit_blocks_illiquid_stock_overallocation(self, repo):
        """流動性の低い銘柄へのオーバーアロケーションがポジション上限でブロックされる。"""
        # 1234 に既に 8% 投資済み（800,000 円）
        illiquid_pos = Position(
            code="1234", qty=400, avg_price=1800.0, current_price=2000.0
        )
        broker = MockBrokerClient(
            available_cash=5_000_000.0, initial_positions=[illiquid_pos]
        )
        rm = _make_risk_manager(
            broker, repo, initial_portfolio_value=10_000_000.0, max_position_pct=0.10
        )
        # さらに 300,000 円追加 → 合計 1,100,000 円 > 1,000,000 円 (10%) → NG
        result = rm.check_signal("2026-04-18_1234_buy", "1234", order_value=300_000.0)
        assert not result.passed
        assert result.reject_reason == RiskRejectReason.POSITION_LIMIT

    def test_sell_during_liquidity_crisis_updates_cash(self, repo):
        """流動性危機中でも売却が成功し、現金残高が増加する。"""
        from kabusys.execution.broker_api import OrderRequest

        pos = Position(code="7777", qty=200, avg_price=2000.0)
        broker = MockBrokerClient(
            fill_mode="instant",
            available_cash=100_000.0,
            initial_positions=[pos],
        )
        om = OrderManager(broker=broker, repo=repo)
        request = OrderRequest(
            code="7777", side="sell", qty=100, order_type="limit", price=2000.0
        )
        record = om.create_order("2026-04-18_7777_sell", request)
        om.send_order(record.client_order_id)

        # 売却後、現金が増加している（100 株 × 2000 円 = 200,000 円増）
        cash_after = broker.get_available_cash()
        assert cash_after > 100_000.0
        assert cash_after == pytest.approx(100_000.0 + 100 * 2000.0)
