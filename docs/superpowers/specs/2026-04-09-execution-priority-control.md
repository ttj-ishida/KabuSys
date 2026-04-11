# Execution優先度制御 設計仕様

**Issue:** #43
**対象フェーズ:** Phase 8
**作成日:** 2026-04-09

---

## 背景・目的

Windows（将来は Linux/AWS）での実行環境において、ExecutionEngine および MonitoringService を OS レベルの高優先度プロセスとして稼働させる。AI/Strategy 処理による負荷スパイク時にも発注・損切りが確実に通るようにする。

---

## スコープ

| ファイル | 種別 | 責務 |
|---|---|---|
| `src/kabusys/utils/__init__.py` | 新規 | パッケージ化のみ |
| `src/kabusys/utils/process_priority.py` | 新規 | プロセス優先度・CPU affinity 設定ユーティリティ |
| `src/kabusys/run_execution.py` | 新規 | ExecutionEngine 起動スクリプト（High優先度） |
| `src/kabusys/run_monitoring.py` | 新規 | SystemMonitor ポーリングループ起動スクリプト（High優先度） |
| `tests/test_process_priority.py` | 新規 | 優先度ユーティリティのテスト |
| `tests/test_run_execution.py` | 新規 | run_execution.main() のテスト |
| `tests/test_run_monitoring.py` | 新規 | run_monitoring.main() のテスト |

**変更しないファイル:** `execution_engine.py`, `system_monitor.py`, `config.py`

---

## 設計

### 1. `process_priority.py`

```python
# src/kabusys/utils/process_priority.py
"""process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ。

Windows と Linux の差分を吸収し、呼び出し元はプラットフォームを意識しない。
"""
from __future__ import annotations

import logging
import platform

import psutil

logger = logging.getLogger(__name__)

_VALID_LEVELS = frozenset({"high", "normal", "low"})

# Windows 優先度クラス
_WINDOWS_PRIORITY = {
    "high":   psutil.HIGH_PRIORITY_CLASS,
    "normal": psutil.NORMAL_PRIORITY_CLASS,
    "low":    psutil.IDLE_PRIORITY_CLASS,
}

# Linux nice 値
_LINUX_NICE = {
    "high":   -10,
    "normal":  0,
    "low":     10,
}


def set_process_priority(level: str) -> None:
    """カレントプロセスの優先度を設定する。

    Args:
        level: "high" | "normal" | "low"

    Raises:
        ValueError: level が無効な場合
    """
    if level not in _VALID_LEVELS:
        raise ValueError(
            f"level が不正です: {level!r}. 有効な値: {sorted(_VALID_LEVELS)}"
        )
    try:
        p = psutil.Process()
        if platform.system() == "Windows":
            p.nice(_WINDOWS_PRIORITY[level])
        else:
            p.nice(_LINUX_NICE[level])
        logger.debug("プロセス優先度を %r に設定しました (PID=%d)", level, p.pid)
    except psutil.AccessDenied:
        logger.warning(
            "プロセス優先度の設定に失敗しました（権限不足）。"
            "管理者権限で実行するか、優先度設定をスキップします。"
        )


def set_cpu_affinity(cpu_count: int | None = None) -> None:
    """カレントプロセスを最初の N コアに固定する。

    Args:
        cpu_count: 使用するコア数。None の場合は設定しない（全コア使用）。
    """
    if cpu_count is None:
        return
    try:
        p = psutil.Process()
        available = list(range(psutil.cpu_count() or 1))
        p.cpu_affinity(available[:cpu_count])
        logger.debug(
            "CPU affinity を %r に設定しました (PID=%d)", available[:cpu_count], p.pid
        )
    except psutil.AccessDenied:
        logger.warning(
            "CPU affinity の設定に失敗しました（権限不足）。スキップします。"
        )
```

### 2. `run_execution.py`

```python
# src/kabusys/run_execution.py
"""run_execution.py — ExecutionEngine 起動スクリプト。

KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、
data/paper_trading.db に記録する。
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date

import duckdb

from kabusys.config import Settings
from kabusys.execution.broker_factory import BrokerClientFactory
from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_repository import OrderRepository
from kabusys.execution.reconciler import Reconciler
from kabusys.execution.risk_manager import RiskConfig, RiskManager
from kabusys.monitoring.monitoring_db import init_monitoring_db
from kabusys.utils.process_priority import set_process_priority, set_cpu_affinity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    # 1. プロセス優先度を High に設定
    set_process_priority("high")
    set_cpu_affinity()  # デフォルト: 全コア使用

    settings = Settings()
    logger.info("起動環境: KABUSYS_ENV=%s", settings.env)

    # 2. DB 接続
    #    paper_trading 環境は専用 DB を使用して本番 DB と完全分離
    sqlite_path = (
        settings.paper_sqlite_path if settings.is_paper else settings.sqlite_path
    )
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    init_monitoring_db(sqlite_conn)
    duckdb_conn = duckdb.connect(str(settings.duckdb_path))

    # 3. ブローカークライアント
    broker = BrokerClientFactory.create(settings)

    # 4. 依存コンポーネント組み立て
    repo = OrderRepository(sqlite_conn)
    order_manager = OrderManager(broker, repo)
    risk_manager = RiskManager(
        broker=broker,
        repo=repo,
        config=RiskConfig(
            max_position_pct=0.20,
            max_utilization=0.80,
            rate_limit_per_sec=5,
            circuit_breaker_errors=10,
            circuit_breaker_window_sec=60,
            max_drawdown=0.20,
            initial_portfolio_value=broker.get_available_cash(),
        ),
    )
    reconciler = Reconciler(broker=broker, repo=repo, order_manager=order_manager)

    # 5. ExecutionEngine 起動
    engine = ExecutionEngine(
        broker=broker,
        repo=repo,
        risk_manager=risk_manager,
        order_manager=order_manager,
        duckdb_conn=duckdb_conn,
        config=EngineConfig(target_date=date.today()),
        reconciler=reconciler,
        pid_file=settings.pid_file_path,
    )
    engine.run_session()


if __name__ == "__main__":
    main()
```

### 3. `run_monitoring.py`

```python
# src/kabusys/run_monitoring.py
"""run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。"""
from __future__ import annotations

import logging
import sqlite3
import time

import duckdb

from kabusys.config import Settings
from kabusys.monitoring.monitoring_db import init_monitoring_db
from kabusys.monitoring.system_monitor import SystemMonitor
from kabusys.utils.process_priority import set_process_priority

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL = 60  # 秒


def _get_poll_interval(settings: Settings) -> int:
    """MONITOR_POLL_INTERVAL 環境変数からポーリング間隔を取得する（デフォルト: 60秒）。"""
    import os
    try:
        return int(os.environ.get("MONITOR_POLL_INTERVAL", _DEFAULT_POLL_INTERVAL))
    except ValueError:
        logger.warning("MONITOR_POLL_INTERVAL の値が不正です。デフォルト %d 秒を使用します。", _DEFAULT_POLL_INTERVAL)
        return _DEFAULT_POLL_INTERVAL


def main() -> None:
    # 1. プロセス優先度を High に設定
    set_process_priority("high")

    settings = Settings()
    logger.info("起動環境: KABUSYS_ENV=%s", settings.env)

    # 2. DB 接続（monitoring は環境にかかわらず本番 sqlite_path を使用）
    sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
    init_monitoring_db(sqlite_conn)
    duckdb_conn = duckdb.connect(str(settings.duckdb_path))

    # 3. SystemMonitor 初期化
    monitor = SystemMonitor(
        conn=sqlite_conn,
        duckdb_conn=duckdb_conn,
        pid_file=settings.pid_file_path,
    )

    # 4. ポーリングループ
    poll_interval = _get_poll_interval(settings)
    logger.info("監視ループ開始（ポーリング間隔: %d 秒）", poll_interval)
    try:
        while True:
            monitor.check_once()
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("監視ループを終了します。")


if __name__ == "__main__":
    main()
```

---

## エラーハンドリング

| 状況 | 挙動 |
|---|---|
| `set_process_priority` で権限不足 | `WARNING` ログを出して続行（プロセスを落とさない） |
| `set_cpu_affinity` で権限不足 | `WARNING` ログを出して続行 |
| `level` に無効値 | `ValueError` を raise（起動時に失敗） |
| `KeyboardInterrupt`（run_monitoring） | クリーンに終了 |

---

## テスト方針

### `tests/test_process_priority.py`

| テスト | 検証内容 |
|---|---|
| `test_set_priority_high_windows` | Windows 環境で `HIGH_PRIORITY_CLASS` を設定 |
| `test_set_priority_normal_windows` | Windows 環境で `NORMAL_PRIORITY_CLASS` を設定 |
| `test_set_priority_low_windows` | Windows 環境で `IDLE_PRIORITY_CLASS` を設定 |
| `test_set_priority_high_linux` | Linux 環境で `nice(-10)` を設定 |
| `test_set_priority_normal_linux` | Linux 環境で `nice(0)` を設定 |
| `test_set_priority_low_linux` | Linux 環境で `nice(10)` を設定 |
| `test_set_priority_invalid_raises` | 無効な level で `ValueError` |
| `test_set_priority_access_denied_logs_warning` | `AccessDenied` で warning ログ・例外なし |
| `test_set_cpu_affinity_pins_cores` | `cpu_count=2` で `cpu_affinity([0, 1])` を呼ぶ |
| `test_set_cpu_affinity_none_skips` | `cpu_count=None` で `cpu_affinity` を呼ばない |

### `tests/test_run_execution.py`

| テスト | 検証内容 |
|---|---|
| `test_main_paper_mode_uses_paper_sqlite_path` | `is_paper=True` で `paper_sqlite_path` を使用 |
| `test_main_dev_mode_uses_sqlite_path` | `is_paper=False` で `sqlite_path` を使用 |
| `test_main_sets_high_priority_first` | `set_process_priority("high")` が最初に呼ばれる |
| `test_main_calls_run_session` | `engine.run_session()` が呼ばれる |

### `tests/test_run_monitoring.py`

| テスト | 検証内容 |
|---|---|
| `test_main_sets_high_priority_first` | `set_process_priority("high")` が最初に呼ばれる |
| `test_main_calls_check_once` | `monitor.check_once()` が呼ばれる |
| `test_main_uses_sqlite_path` | monitoring は常に `sqlite_path` を使用 |
| `test_poll_interval_default` | `MONITOR_POLL_INTERVAL` 未設定で 60 秒 |
| `test_poll_interval_override` | `MONITOR_POLL_INTERVAL=30` で 30 秒 |
| `test_poll_interval_invalid_uses_default` | `MONITOR_POLL_INTERVAL=abc` で 60 秒（warning） |

---

## 非スコープ

- strategy_service / ai_service の起動スクリプト（これらはライブラリであり独立プロセスではない）
- メモリ制限（OS/コンテナ層に委譲）
- systemd / Windows Service 登録
- `run_execution.py` 内の RiskConfig の環境変数化（将来の改善候補）
