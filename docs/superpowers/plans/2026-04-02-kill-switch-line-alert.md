# Kill Switch + LINE アラート 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MonitoringEngine が検知した異常条件でフラグファイルを書き込み ExecutionEngine を停止し、LINE Messaging API でオペレーターに通知する。

**Architecture:** `KillSwitch` クラスがフラグファイル IPC を担当、`AlertManager` クラスが LINE 通知を担当する独立設計。`MonitoringEngine` が両クラスを組み込み、`ExecutionEngine` がフラグファイルをポーリングして自動停止する。

**Tech Stack:** Python 3.10+, pathlib, requests (既存), unittest.mock

---

## ファイル構成

| ファイル | 変更種別 | 責務 |
|---|---|---|
| `src/kabusys/config.py` | 更新 | LINE 設定追加、kill_flag_path 追加、Slack 設定削除 |
| `src/kabusys/monitoring/kill_switch.py` | 新規 | フラグファイル IPC（書き込み・検出・削除） |
| `src/kabusys/monitoring/alert_manager.py` | 新規 | LINE Messaging API プッシュ通知 + クールダウン管理 |
| `src/kabusys/monitoring/monitoring_engine.py` | 更新 | KillSwitch/AlertManager 組み込み、run_once() 再設計 |
| `src/kabusys/monitoring/__init__.py` | 更新 | KillSwitch/AlertManager エクスポート追加 |
| `src/kabusys/execution/execution_engine.py` | 更新 | kill.flag ポーリング（run_session + _process_signals） |
| `tests/test_kill_switch.py` | 新規 | KillSwitch ユニットテスト |
| `tests/test_alert_manager.py` | 新規 | AlertManager ユニットテスト |
| `tests/test_monitoring_engine.py` | 更新 | MonitoringEngine + KillSwitch/AlertManager 統合テスト追加 |
| `tests/test_execution_engine.py` | 更新 | ExecutionEngine kill.flag テスト追加 |

---

## Task 1: config.py — LINE 設定追加・Slack 設定削除・kill_flag_path 追加

**Files:**
- Modify: `src/kabusys/config.py:150-157`

- [ ] **Step 1: 既存テストが PASS することを確認**

```bash
pytest -v
```
Expected: 全テスト PASS（`tests/test_config.py` は存在しないため全体スイートで確認する）

- [ ] **Step 2: config.py の Slack プロパティを LINE プロパティに置き換える**

`src/kabusys/config.py` の `# --- Slack ---` ブロック（lines 150-157）を次のコードで置き換える:

```python
    # --- LINE Messaging API ---
    @property
    def line_channel_access_token(self) -> str:
        return os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

    @property
    def line_user_id(self) -> str:
        return os.environ.get("LINE_USER_ID", "")
```

- [ ] **Step 3: kill_flag_path プロパティを追加する**

`# --- 監視設定 ---` ブロック（`pid_file_path` の直後）に追加:

```python
    @property
    def kill_flag_path(self) -> Path:
        return Path(os.environ.get("KILL_FLAG_PATH", "data/kill.flag")).expanduser()
```

- [ ] **Step 4: テストを実行して確認**

```bash
pytest -v
```

Expected: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/config.py
git commit -m "feat: replace Slack config with LINE API + add kill_flag_path to Settings"
```

---

## Task 2: KillSwitch クラスの実装

**Files:**
- Create: `src/kabusys/monitoring/kill_switch.py`
- Create: `tests/test_kill_switch.py`

### Step 1: テストファイルを作成する

- [ ] `tests/test_kill_switch.py` を次の内容で作成する:

```python
"""tests/test_kill_switch.py — KillSwitch ユニットテスト"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kabusys.monitoring.kill_switch import KillSwitch
from kabusys.monitoring.system_monitor import SystemCheckResult
from kabusys.monitoring.trade_monitor import TradeCheckResult
from kabusys.monitoring.risk_monitor import RiskCheckResult


def _make_sys(process_ok: bool = True, data_freshness_ok: bool = True) -> SystemCheckResult:
    return SystemCheckResult(
        recorded_at="2026-04-02T09:05:00+09:00",
        cpu_percent=30.0,
        memory_percent=50.0,
        disk_percent=40.0,
        process_ok=process_ok,
        data_freshness_ok=data_freshness_ok,
        stale_pid_detected=False,
    )


def _make_trade(stale: list[str] | None = None, anomaly: list[str] | None = None) -> TradeCheckResult:
    return TradeCheckResult(
        logged_at="2026-04-02T09:05:00+09:00",
        stale_orders=stale or [],
        anomaly_fills=anomaly or [],
    )


def _make_risk(drawdown_alert: bool = False, position_limit_alert: bool = False,
               drawdown_pct: float = 0.0, position_count: int = 0) -> RiskCheckResult:
    return RiskCheckResult(
        logged_at="2026-04-02T09:05:00+09:00",
        drawdown_pct=drawdown_pct,
        drawdown_alert=drawdown_alert,
        position_count=position_count,
        position_limit_alert=position_limit_alert,
    )


class TestKillSwitchEvaluate:

    def test_drawdown_alert_writes_flag_and_returns_reason(self, tmp_path):
        """drawdown_alert=True → kill.flag 書き込み・理由文字列返却"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys(),
            _make_trade(),
            _make_risk(drawdown_alert=True, drawdown_pct=0.123),
        )
        assert reason is not None
        assert "DRAWDOWN" in reason
        assert (tmp_path / "kill.flag").exists()

    def test_position_limit_alert_writes_flag(self, tmp_path):
        """position_limit_alert=True → kill.flag 書き込み"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys(),
            _make_trade(),
            _make_risk(position_limit_alert=True, position_count=11),
        )
        assert reason is not None
        assert (tmp_path / "kill.flag").exists()

    def test_process_ok_false_does_not_write_flag(self, tmp_path):
        """process_ok=False のみ → kill.flag 書き込まない・None 返却"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys(process_ok=False),
            _make_trade(),
            _make_risk(),
        )
        assert reason is None
        assert not (tmp_path / "kill.flag").exists()

    def test_idempotent_does_not_overwrite_existing_flag(self, tmp_path):
        """flag が既存の場合は再書き込みしない（冪等）"""
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("original content")
        ks = KillSwitch(flag_path=flag_path)
        ks.evaluate(
            _make_sys(),
            _make_trade(),
            _make_risk(drawdown_alert=True, drawdown_pct=0.15),
        )
        assert flag_path.read_text() == "original content"

    def test_all_false_returns_none_no_flag(self, tmp_path):
        """全条件 False → None 返却・flag 作成なし"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(_make_sys(), _make_trade(), _make_risk())
        assert reason is None
        assert not (tmp_path / "kill.flag").exists()

    def test_drawdown_evaluated_before_position_limit(self, tmp_path):
        """両方 True の場合 drawdown_alert が先（評価順序）"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys(),
            _make_trade(),
            _make_risk(drawdown_alert=True, position_limit_alert=True, drawdown_pct=0.12),
        )
        assert reason is not None
        assert "DRAWDOWN" in reason


class TestKillSwitchIsFlaggedAndClear:

    def test_is_flagged_true_when_flag_exists(self, tmp_path):
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("test")
        ks = KillSwitch(flag_path=flag_path)
        assert ks.is_flagged() is True

    def test_is_flagged_false_when_no_flag(self, tmp_path):
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        assert ks.is_flagged() is False

    def test_clear_removes_flag(self, tmp_path):
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("test")
        ks = KillSwitch(flag_path=flag_path)
        ks.clear()
        assert not flag_path.exists()
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_kill_switch.py -v
```

Expected: FAIL（`ModuleNotFoundError: No module named 'kabusys.monitoring.kill_switch'`）

- [ ] **Step 3: `kill_switch.py` を実装する**

`src/kabusys/monitoring/kill_switch.py` を次の内容で作成する:

```python
"""kill_switch.py — フラグファイル書き込みによる ExecutionEngine 停止シグナル。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from kabusys.monitoring.risk_monitor import RiskCheckResult
from kabusys.monitoring.system_monitor import SystemCheckResult
from kabusys.monitoring.trade_monitor import TradeCheckResult

logger = logging.getLogger(__name__)


class KillSwitch:
    """data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送る。

    flag_path は呼び出し元が Settings.kill_flag_path から渡す。
    """

    def __init__(self, flag_path: Path) -> None:
        self._flag_path = flag_path

    def evaluate(
        self,
        system: SystemCheckResult,
        trade: TradeCheckResult,
        risk: RiskCheckResult,
    ) -> str | None:
        """トリガー条件を評価する。

        該当すれば kill.flag を書き込み、理由文字列を返す。
        評価順序: drawdown_alert → position_limit_alert（テーブル上から順）。
        flag が既存の場合は再書き込みしない（冪等）。
        該当なしは None を返す。
        """
        reason: str | None = None

        if risk.drawdown_alert:
            reason = (
                f"DRAWDOWN_ALERT: DD {risk.drawdown_pct * 100:.1f}% exceeded threshold 10.0%"
                f" at {datetime.now(tz=timezone.utc).isoformat()}"
            )
        elif risk.position_limit_alert:
            reason = (
                f"POSITION_LIMIT_ALERT: {risk.position_count} positions exceeded limit"
                f" at {datetime.now(tz=timezone.utc).isoformat()}"
            )

        if reason:
            self._write_flag(reason)

        return reason

    def _write_flag(self, reason: str) -> None:
        """kill.flag を書き込む。既存の場合はスキップ（冪等）。"""
        if self._flag_path.exists():
            logger.debug("kill.flag already exists — skipping write")
            return
        self._flag_path.parent.mkdir(parents=True, exist_ok=True)
        self._flag_path.write_text(reason)
        logger.warning("kill.flag written: %s", reason)

    def is_flagged(self) -> bool:
        """kill.flag が存在するか確認する。"""
        return self._flag_path.exists()

    def clear(self) -> None:
        """kill.flag を削除する（ExecutionEngine 起動時のクリーンアップ用）。"""
        self._flag_path.unlink(missing_ok=True)
        logger.info("kill.flag cleared")
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
pytest tests/test_kill_switch.py -v
```

Expected: 9 tests PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/kill_switch.py tests/test_kill_switch.py
git commit -m "feat: add KillSwitch class with flag-file IPC"
```

---

## Task 3: AlertManager クラスの実装

**Files:**
- Create: `src/kabusys/monitoring/alert_manager.py`
- Create: `tests/test_alert_manager.py`

### Step 1: テストファイルを作成する

- [ ] `tests/test_alert_manager.py` を次の内容で作成する:

```python
"""tests/test_alert_manager.py — AlertManager ユニットテスト"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from kabusys.monitoring.alert_manager import AlertManager


LINE_API_URL = "https://api.line.me/v2/bot/message/push"


class TestAlertManagerNotify:

    def test_sends_message_when_token_set(self):
        """トークンあり → requests.post が呼ばれ True を返す"""
        manager = AlertManager(channel_access_token="token123", user_id="uid123")
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = manager.notify("テストメッセージ", level="INFO", category="TEST")
        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == LINE_API_URL
        assert "テストメッセージ" in call_kwargs[1]["json"]["messages"][0]["text"]

    def test_skips_when_token_empty(self):
        """トークン空 → スキップ・False 返却・例外なし"""
        manager = AlertManager(channel_access_token="", user_id="")
        result = manager.notify("テスト", level="WARNING")
        assert result is False

    def test_cooldown_suppresses_duplicate_within_window(self):
        """同一 (level, category) の cooldown 内 → スキップ"""
        manager = AlertManager(channel_access_token="token", user_id="uid", cooldown_minutes=30)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            manager.notify("first", level="CRITICAL", category="DRAWDOWN")
            result = manager.notify("second", level="CRITICAL", category="DRAWDOWN")
        assert result is False
        assert mock_post.call_count == 1

    def test_sends_after_cooldown_expires(self):
        """cooldown 経過後 → 送信"""
        manager = AlertManager(channel_access_token="token", user_id="uid", cooldown_minutes=30)
        # 31分前の時刻を直接セット
        past = datetime.now(tz=timezone.utc) - timedelta(minutes=31)
        manager._last_sent[("CRITICAL", "DRAWDOWN")] = past
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = manager.notify("msg", level="CRITICAL", category="DRAWDOWN")
        assert result is True
        mock_post.assert_called_once()

    def test_different_categories_do_not_share_cooldown(self):
        """同一 level・異なる category → クールダウン非干渉（両方送信）"""
        manager = AlertManager(channel_access_token="token", user_id="uid", cooldown_minutes=30)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            r1 = manager.notify("msg1", level="CRITICAL", category="DRAWDOWN")
            r2 = manager.notify("msg2", level="CRITICAL", category="PROCESS")
        assert r1 is True
        assert r2 is True
        assert mock_post.call_count == 2

    def test_request_exception_returns_false_no_propagation(self):
        """requests.exceptions.RequestException → False 返却・例外非伝播"""
        manager = AlertManager(channel_access_token="token", user_id="uid")
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("no network")):
            result = manager.notify("msg", level="CRITICAL")
        assert result is False

    def test_non_2xx_response_returns_false(self):
        """非 2xx レスポンス → False 返却・例外非伝播"""
        manager = AlertManager(channel_access_token="token", user_id="uid")
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=429)
            result = manager.notify("msg", level="WARNING")
        assert result is False
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_alert_manager.py -v
```

Expected: FAIL（`ModuleNotFoundError: No module named 'kabusys.monitoring.alert_manager'`）

- [ ] **Step 3: `alert_manager.py` を実装する**

`src/kabusys/monitoring/alert_manager.py` を次の内容で作成する:

```python
"""alert_manager.py — LINE Messaging API による一方向プッシュ通知。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


class AlertManager:
    """LINE Messaging API push message を送信する。

    channel_access_token / user_id が空の場合は送信せずログのみ出力する。
    同一 (level, category) に対するクールダウン管理をメモリ内で行う。
    """

    def __init__(
        self,
        channel_access_token: str,
        user_id: str,
        cooldown_minutes: int = 30,
    ) -> None:
        self._token = channel_access_token
        self._user_id = user_id
        self._cooldown = timedelta(minutes=cooldown_minutes)
        self._last_sent: dict[tuple[str, str], datetime] = {}

    def notify(self, message: str, level: str = "INFO", category: str = "") -> bool:
        """LINE push message を送信する。

        Returns:
            True: 送信成功
            False: スキップ（トークン未設定 / cooldown / エラー）
        """
        if not self._token or not self._user_id:
            logger.warning("LINE token/user_id not configured — skipping alert: [%s] %s", level, message)
            return False

        key = (level, category)
        now = datetime.now(tz=timezone.utc)
        last = self._last_sent.get(key)
        if last is not None and now - last < self._cooldown:
            logger.debug("Alert cooldown active for (%s, %s) — skipping", level, category)
            return False

        now_jst = datetime.now(tz=timezone.utc).astimezone(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=9))
        )
        text = f"[{level}] KabuSys 監視アラート\n{message}\n{now_jst.strftime('%Y-%m-%d %H:%M:%S JST')}"

        try:
            resp = requests.post(
                LINE_PUSH_URL,
                headers={"Authorization": f"Bearer {self._token}"},
                json={"to": self._user_id, "messages": [{"type": "text", "text": text}]},
                timeout=10,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("LINE API request failed: %s", exc)
            return False

        if resp.status_code < 200 or resp.status_code >= 300:
            logger.error("LINE API returned non-2xx status %d", resp.status_code)
            return False

        self._last_sent[key] = now
        logger.info("LINE alert sent: [%s] %s", level, message)
        return True
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
pytest tests/test_alert_manager.py -v
```

Expected: 7 tests PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/alert_manager.py tests/test_alert_manager.py
git commit -m "feat: add AlertManager with LINE Messaging API push and cooldown"
```

---

## Task 4: MonitoringEngine の再設計

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_engine.py`
- Modify: `tests/test_monitoring_engine.py` (テスト追加)

- [ ] **Step 1: 新テストケースを `tests/test_monitoring_engine.py` に追加する**

ファイル末尾に追加:

```python
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
```

- [ ] **Step 2: 追加テストが FAIL することを確認**

```bash
pytest tests/test_monitoring_engine.py::test_monitoring_engine_calls_kill_switch_when_all_results_available -v
```

Expected: FAIL（KillSwitch import error または evaluate not called）

- [ ] **Step 3: `monitoring_engine.py` を全面書き換えする**

`src/kabusys/monitoring/monitoring_engine.py` を次の内容で置き換える:

```python
"""monitoring_engine.py — 各 Monitor を束ねてポーリングする。"""
from __future__ import annotations

import logging
import time

from kabusys.monitoring.alert_manager import AlertManager
from kabusys.monitoring.kill_switch import KillSwitch
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
        kill_switch: KillSwitch | None = None,
        alert_manager: AlertManager | None = None,
    ) -> None:
        self._system_monitor = system_monitor
        self._trade_monitor = trade_monitor
        self._risk_monitor = risk_monitor
        self._interval_sec = interval_sec
        self._kill_switch = kill_switch
        self._alert_manager = alert_manager

    def run_once(self) -> None:
        """テスト用: 各 Monitor を1回だけ呼び出す。"""
        sys_result = None
        try:
            sys_result = self._system_monitor.check_once()
        except Exception:
            logger.exception("SystemMonitor failed")

        trade_result = None
        try:
            trade_result = self._trade_monitor.check_once()
        except Exception:
            logger.exception("TradeMonitor failed")

        risk_result = None
        try:
            risk_result = self._risk_monitor.check_once()
        except Exception:
            logger.exception("RiskMonitor failed")

        # Kill Switch 評価（全 result が揃っている場合のみ）
        if self._kill_switch and sys_result and trade_result and risk_result:
            reason = self._kill_switch.evaluate(sys_result, trade_result, risk_result)
            if reason and self._alert_manager:
                self._alert_manager.notify(
                    f"Kill Switch 発動: {reason}", "CRITICAL", category="KILL_SWITCH"
                )

        # 個別アラート（各 result が None でない場合のみ参照）
        if self._alert_manager:
            if sys_result and not sys_result.process_ok:
                self._alert_manager.notify(
                    "Execution プロセス停止を検出", "CRITICAL", category="PROCESS"
                )
            if trade_result and trade_result.stale_orders:
                self._alert_manager.notify(
                    f"滞留注文 {len(trade_result.stale_orders)} 件", "WARNING", category="STALE_ORDER"
                )
            if trade_result and trade_result.anomaly_fills:
                self._alert_manager.notify(
                    f"約定異常価格 {len(trade_result.anomaly_fills)} 件", "WARNING", category="PRICE_ANOMALY"
                )
            if risk_result and risk_result.drawdown_alert:
                self._alert_manager.notify(
                    f"DD {risk_result.drawdown_pct * 100:.1f}% 超過", "CRITICAL", category="DRAWDOWN"
                )
            if risk_result and risk_result.position_limit_alert:
                self._alert_manager.notify(
                    f"ポジション上限超過: {risk_result.position_count} 銘柄", "WARNING", category="POSITION_LIMIT"
                )
            if sys_result and not sys_result.data_freshness_ok:
                self._alert_manager.notify(
                    "株価データ鮮度異常", "WARNING", category="DATA_FRESHNESS"
                )

    def run(self) -> None:
        """本番用: KeyboardInterrupt まで interval_sec 間隔でポーリング。"""
        logger.info("MonitoringEngine starting (interval=%ds)", self._interval_sec)
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("MonitoringEngine stopped")
                break
            except Exception:
                logger.exception("MonitoringEngine run loop error — continuing")
            try:
                time.sleep(self._interval_sec)
            except KeyboardInterrupt:
                logger.info("MonitoringEngine stopped")
                break
```

- [ ] **Step 4: 全テストが PASS することを確認**

```bash
pytest tests/test_monitoring_engine.py -v
```

Expected: 全テスト PASS（既存テストも含む）

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/monitoring/monitoring_engine.py tests/test_monitoring_engine.py
git commit -m "feat: integrate KillSwitch and AlertManager into MonitoringEngine"
```

---

## Task 5: monitoring/__init__.py のエクスポート更新

**Files:**
- Modify: `src/kabusys/monitoring/__init__.py`

- [ ] **Step 1: `__init__.py` に KillSwitch / AlertManager を追加する**

```python
from kabusys.monitoring.alert_manager import AlertManager
from kabusys.monitoring.kill_switch import KillSwitch
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
from kabusys.monitoring.monitoring_engine import MonitoringEngine
from kabusys.monitoring.risk_monitor import RiskCheckResult, RiskMonitor
from kabusys.monitoring.system_monitor import SystemCheckResult, SystemMonitor
from kabusys.monitoring.trade_monitor import TradeCheckResult, TradeMonitor

__all__ = [
    "AlertManager",
    "KillSwitch",
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
python -c "from kabusys.monitoring import KillSwitch, AlertManager; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/monitoring/__init__.py
git commit -m "feat: export KillSwitch and AlertManager from monitoring package"
```

---

## Task 6: ExecutionEngine の kill.flag ポーリング追加

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py:59-123, 219-223`
- Modify: `tests/test_execution_engine.py`

- [ ] **Step 1: テストケースを `tests/test_execution_engine.py` に追加する**

**まず** ファイル先頭の import 行を更新する（line 8）:

```python
# 変更前
from unittest.mock import MagicMock
# 変更後
from unittest.mock import MagicMock, patch
```

次に、ファイル末尾にクラスを追加する:

```python
class TestKillFlagPolling:
    """kill.flag ポーリング動作のテスト"""

    def test_process_signals_skips_on_kill_flag_at_method_head(self, sqlite_conn, duckdb_conn, tmp_path):
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

    def test_run_session_clears_kill_flag_on_startup(self, sqlite_conn, duckdb_conn, tmp_path):
        """起動時に kill.flag が存在する場合は削除される"""
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("old flag")
        pid_file = tmp_path / "execution.pid"

        broker = MockBrokerClient()
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        # _pid_file を設定することで run_session() 内の _active_pid_file が tmp_path 配下になる
        # （これはローカルの _config.pid_file_path ではなく engine._pid_file 優先パスを使う）
        engine._pid_file = pid_file

        with patch("kabusys.execution.execution_engine.settings") as mock_settings, \
             patch.object(engine, "_websocket_worker"), \
             patch.object(engine, "_process_signals"), \
             patch.object(engine, "_drain_push_queue"):
            mock_settings.kill_flag_path = flag_path
            # mock_settings.pid_file_path は run_session() 内の local re-import に影響しないため設定不要
            engine._stop_event.set()  # 即座に停止
            try:
                engine.run_session()
            except Exception:
                pass

        assert not flag_path.exists()
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_execution_engine.py::TestKillFlagPolling -v
```

Expected: FAIL（`AttributeError: settings` など）

- [ ] **Step 3: `execution_engine.py` に kill.flag ポーリングを追加する**

`src/kabusys/execution/execution_engine.py` を次の箇所で編集する。

**変更 1: モジュール先頭に settings をモジュールレベルでインポート追加【必須・最初に行うこと】**

`execution_engine.py` のモジュール先頭（既存 import 群の末尾、`from kabusys.execution.risk_manager import ...` 等の後）に追加:

```python
from kabusys.config import settings
```

このモジュールレベルの `settings` 名が存在しないと:
- 変更 2〜4 で参照する `settings.kill_flag_path` が `NameError` になる
- テストが `patch("kabusys.execution.execution_engine.settings")` で `AttributeError` になる

**重要:** `run_session()` 内には既存の `from kabusys.config import settings as _config`（line 219）が存在し、`_active_pid_file = ... _config.pid_file_path` として使われている。このローカルインポートは**削除しないこと**。モジュールレベルの `settings` と共存させる（両方とも同じシングルトンを参照する）。

**変更 2: `run_session()` — PID ファイル書き込み直後に kill.flag クリア**

`_active_pid_file.write_text(str(os.getpid()))` の次の行に追加（line 222 の直後）:

```python
        settings.kill_flag_path.unlink(missing_ok=True)   # 起動時に kill.flag をクリア
```

**変更 3: `_process_signals()` — メソッド先頭に kill.flag チェック追加**

`_process_signals()` メソッドの先頭（`from kabusys.execution.broker_api import OrderRequest` の直後）に追加:

```python
        # 1. メソッド先頭チェック
        if settings.kill_flag_path.exists():
            logger.warning("kill.flag を検出 — kill_switch を発動します")
            self.kill_switch()
            return
```

**変更 4: `_process_signals()` — for ループ内に kill.flag チェック追加**

`for sig in signals:` ループ内の `if self._stop_event.is_set(): break` の直後に追加:

```python
            # 2. ループ内チェック（発注ループ実行中の kill.flag 検出）
            if settings.kill_flag_path.exists():
                logger.warning("kill.flag を検出（ループ内）— kill_switch を発動します")
                self.kill_switch()
                return
```

- [ ] **Step 4: 全テストを実行して確認**

```bash
pytest tests/test_execution_engine.py -v
```

Expected: 全テスト PASS

- [ ] **Step 5: 全体テストを実行**

```bash
pytest -v
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/execution/execution_engine.py tests/test_execution_engine.py
git commit -m "feat: add kill.flag polling to ExecutionEngine (run_session + _process_signals)"
```

---

## Task 7: .env.example 更新（ドキュメント）

**Files:**
- Modify: `.env.example` または `.env` ファイル（存在する場合）

- [ ] **Step 1: .env.example に LINE 設定を追加する**

```bash
grep -l "SLACK_BOT_TOKEN\|LINE_CHANNEL" .env.example 2>/dev/null || echo "not found"
```

`.env.example` が存在する場合、`SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID` を削除し、次を追加:

```
# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_USER_ID=your_line_user_id_here

# Kill Switch
# 本番環境では絶対パスを推奨（MonitoringEngine と ExecutionEngine を同一 CWD から起動する場合は不要）
# KILL_FLAG_PATH=/absolute/path/to/data/kill.flag
```

- [ ] **Step 2: 最終全体テスト**

```bash
pytest -v
```

Expected: 全テスト PASS

- [ ] **Step 3: コミット**

```bash
git add .env.example
git commit -m "docs: update .env.example for LINE API and kill_flag_path"
```

---

## 実装完了チェックリスト

- [ ] `pytest -v` で全テスト PASS
- [ ] `from kabusys.monitoring import KillSwitch, AlertManager` が通る
- [ ] `KillSwitch(flag_path=Path("data/kill.flag"))` が作成できる
- [ ] `AlertManager(channel_access_token="", user_id="")` でも例外なし
- [ ] `Settings().kill_flag_path` が `Path` を返す
- [ ] `Settings().line_channel_access_token` が `str` を返す
- [ ] `Settings().slack_bot_token` が存在しない（削除済み）
