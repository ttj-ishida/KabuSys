# Execution優先度制御 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows/Linux 両対応のプロセス優先度ユーティリティと、ExecutionEngine・SystemMonitor の起動スクリプトを実装する。

**Architecture:** `src/kabusys/utils/process_priority.py` がプラットフォーム差分（Windows: `HIGH_PRIORITY_CLASS` / Linux: `nice(-10)`）を吸収する。`run_execution.py` と `run_monitoring.py` は起動直後にこのユーティリティを呼び出し、全依存を `Settings` から解決してエンジンを起動する。

**Tech Stack:** Python 3.10+, psutil, pytest, unittest.mock

---

## ファイル構成

| ファイル | 種別 | 責務 |
|---|---|---|
| `src/kabusys/utils/__init__.py` | 新規 | パッケージ化のみ（空ファイル） |
| `src/kabusys/utils/process_priority.py` | 新規 | `set_process_priority()` / `set_cpu_affinity()` |
| `src/kabusys/run_execution.py` | 新規 | ExecutionEngine フル配線 + 起動 |
| `src/kabusys/run_monitoring.py` | 新規 | SystemMonitor ポーリングループ起動 |
| `tests/test_process_priority.py` | 新規 | 優先度ユーティリティのテスト（10件） |
| `tests/test_run_execution.py` | 新規 | run_execution.main() のテスト（4件） |
| `tests/test_run_monitoring.py` | 新規 | run_monitoring.main() のテスト（6件） |

---

### Task 1: `process_priority.py` を実装する

**Files:**
- Create: `src/kabusys/utils/__init__.py`
- Create: `src/kabusys/utils/process_priority.py`
- Create: `tests/test_process_priority.py`

- [ ] **Step 1: テストファイルを新規作成し、失敗するテストを書く**

```python
# tests/test_process_priority.py
import logging
import pytest
import psutil
from unittest.mock import MagicMock, patch

from kabusys.utils.process_priority import set_process_priority, set_cpu_affinity


class TestSetProcessPriority:
    def test_high_windows(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.platform.system", return_value="Windows"), \
             patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            set_process_priority("high")
            mock_proc.nice.assert_called_once_with(psutil.HIGH_PRIORITY_CLASS)

    def test_normal_windows(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.platform.system", return_value="Windows"), \
             patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            set_process_priority("normal")
            mock_proc.nice.assert_called_once_with(psutil.NORMAL_PRIORITY_CLASS)

    def test_low_windows(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.platform.system", return_value="Windows"), \
             patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            set_process_priority("low")
            mock_proc.nice.assert_called_once_with(psutil.IDLE_PRIORITY_CLASS)

    def test_high_linux(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.platform.system", return_value="Linux"), \
             patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            set_process_priority("high")
            mock_proc.nice.assert_called_once_with(-10)

    def test_normal_linux(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.platform.system", return_value="Linux"), \
             patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            set_process_priority("normal")
            mock_proc.nice.assert_called_once_with(0)

    def test_low_linux(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.platform.system", return_value="Linux"), \
             patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            set_process_priority("low")
            mock_proc.nice.assert_called_once_with(10)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            set_process_priority("realtime")

    def test_access_denied_logs_warning(self, caplog):
        mock_proc = MagicMock()
        mock_proc.nice.side_effect = psutil.AccessDenied(0)
        with patch("kabusys.utils.process_priority.platform.system", return_value="Windows"), \
             patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc), \
             caplog.at_level(logging.WARNING, logger="kabusys.utils.process_priority"):
            set_process_priority("high")  # 例外を投げないこと
        assert "権限不足" in caplog.text


class TestSetCpuAffinity:
    def test_pins_to_first_n_cores(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc), \
             patch("kabusys.utils.process_priority.psutil.cpu_count", return_value=4):
            set_cpu_affinity(2)
            mock_proc.cpu_affinity.assert_called_once_with([0, 1])

    def test_none_skips(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            set_cpu_affinity(None)
            mock_proc.cpu_affinity.assert_not_called()

    def test_access_denied_logs_warning(self, caplog):
        mock_proc = MagicMock()
        mock_proc.cpu_affinity.side_effect = psutil.AccessDenied(0)
        with patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc), \
             patch("kabusys.utils.process_priority.psutil.cpu_count", return_value=4), \
             caplog.at_level(logging.WARNING, logger="kabusys.utils.process_priority"):
            set_cpu_affinity(2)  # 例外を投げないこと
        assert "権限不足" in caplog.text
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_process_priority.py -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.utils'`

- [ ] **Step 3: `src/kabusys/utils/__init__.py` を作成（空ファイル）**

```bash
# ファイルを作成するだけ（中身は空）
```

- [ ] **Step 4: `src/kabusys/utils/process_priority.py` を作成**

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

_WINDOWS_PRIORITY = {
    "high":   psutil.HIGH_PRIORITY_CLASS,
    "normal": psutil.NORMAL_PRIORITY_CLASS,
    "low":    psutil.IDLE_PRIORITY_CLASS,
}

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

- [ ] **Step 5: テストが通ることを確認**

```bash
python -m pytest tests/test_process_priority.py -v
```

Expected: 11 passed

- [ ] **Step 6: 既存テスト全体が壊れていないことを確認**

```bash
python -m pytest tests/ -q --tb=short --ignore=tests/test_generated.py
```

Expected: 全テスト passed（追加11件を含む）

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/utils/__init__.py src/kabusys/utils/process_priority.py tests/test_process_priority.py
git commit -m "feat: add process_priority utility for Windows/Linux cross-platform support (Issue #43)"
```

---

### Task 2: `run_execution.py` を実装する

**Files:**
- Create: `src/kabusys/run_execution.py`
- Create: `tests/test_run_execution.py`

#### 背景

`ExecutionEngine` は以下の依存を必要とする:
- `broker` — `BrokerClientFactory.create(settings)` で生成
- `repo` — `OrderRepository(sqlite_conn)`
- `order_manager` — `OrderManager(broker, repo)`
- `risk_manager` — `RiskManager(broker, repo, RiskConfig(...))`
- `reconciler` — `Reconciler(broker, repo, order_manager)`
- `duckdb_conn` — `duckdb.connect(settings.duckdb_path)`
- `config` — `EngineConfig(target_date=date.today())`
- `pid_file` — `settings.pid_file_path`

Paper Trading モード（`settings.is_paper == True`）では `settings.paper_sqlite_path` を使用し、本番 DB と完全分離する。

- [ ] **Step 1: テストファイルを新規作成し、失敗するテストを書く**

```python
# tests/test_run_execution.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kabusys.run_execution import main


def _run_main(is_paper: bool = False):
    """全依存をモックして main() を実行するヘルパー。"""
    mock_broker = MagicMock()
    mock_broker.get_available_cash.return_value = 10_000_000.0
    mock_engine = MagicMock()

    with patch("kabusys.run_execution.set_process_priority") as mock_priority, \
         patch("kabusys.run_execution.set_cpu_affinity"), \
         patch("kabusys.run_execution.Settings") as mock_settings_cls, \
         patch("kabusys.run_execution.sqlite3.connect") as mock_sqlite, \
         patch("kabusys.run_execution.init_monitoring_db"), \
         patch("kabusys.run_execution.duckdb.connect"), \
         patch("kabusys.run_execution.BrokerClientFactory.create", return_value=mock_broker), \
         patch("kabusys.run_execution.OrderRepository"), \
         patch("kabusys.run_execution.OrderManager"), \
         patch("kabusys.run_execution.RiskManager"), \
         patch("kabusys.run_execution.Reconciler"), \
         patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine):

        settings = MagicMock()
        settings.is_paper = is_paper
        settings.paper_sqlite_path = Path("/paper.db")
        settings.sqlite_path = Path("/prod.db")
        settings.duckdb_path = Path("/data.duckdb")
        settings.pid_file_path = Path("/data/execution.pid")
        mock_settings_cls.return_value = settings

        main()

    return mock_priority, mock_sqlite, mock_engine, settings


class TestRunExecutionMain:
    def test_sets_high_priority_first(self):
        mock_priority, _, _, _ = _run_main()
        mock_priority.assert_called_once_with("high")

    def test_paper_mode_uses_paper_sqlite_path(self):
        _, mock_sqlite, _, settings = _run_main(is_paper=True)
        mock_sqlite.assert_called_once_with(str(settings.paper_sqlite_path))

    def test_dev_mode_uses_sqlite_path(self):
        _, mock_sqlite, _, settings = _run_main(is_paper=False)
        mock_sqlite.assert_called_once_with(str(settings.sqlite_path))

    def test_calls_run_session(self):
        _, _, mock_engine, _ = _run_main()
        mock_engine.run_session.assert_called_once()
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_run_execution.py -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.run_execution'`

- [ ] **Step 3: `src/kabusys/run_execution.py` を作成**

```python
# src/kabusys/run_execution.py
"""run_execution.py — ExecutionEngine 起動スクリプト。

KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、
data/paper_trading.db に記録する（本番 DB と完全分離）。
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
from kabusys.utils.process_priority import set_cpu_affinity, set_process_priority

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    # 1. プロセス優先度を High に設定（最初に実行）
    set_process_priority("high")
    set_cpu_affinity()  # デフォルト: 全コア使用

    settings = Settings()
    logger.info("起動環境: KABUSYS_ENV=%s", settings.env)

    # 2. DB 接続 — paper_trading は専用 DB で本番と分離
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

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_run_execution.py -v
```

Expected: 4 passed

- [ ] **Step 5: 既存テスト全体が壊れていないことを確認**

```bash
python -m pytest tests/ -q --tb=short --ignore=tests/test_generated.py
```

Expected: 全テスト passed

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/run_execution.py tests/test_run_execution.py
git commit -m "feat: add run_execution.py startup script with High priority (Issue #43)"
```

---

### Task 3: `run_monitoring.py` を実装する

**Files:**
- Create: `src/kabusys/run_monitoring.py`
- Create: `tests/test_run_monitoring.py`

#### 背景

`SystemMonitor` は `check_once()` を1回呼ぶ設計（内部ループなし）。起動スクリプトが `while True: check_once(); sleep()` のポーリングループを担う。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト60秒）。Monitoring は Paper Trading 時も本番 `sqlite_path` を使用（監視DBは環境分離不要）。

- [ ] **Step 1: テストファイルを新規作成し、失敗するテストを書く**

```python
# tests/test_run_monitoring.py
import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kabusys.run_monitoring import _get_poll_interval


def _make_settings():
    settings = MagicMock()
    settings.sqlite_path = Path("/prod.db")
    settings.duckdb_path = Path("/data.duckdb")
    settings.pid_file_path = Path("/data/execution.pid")
    settings.env = "development"
    return settings


def _run_main():
    """全依存をモックして main() を実行するヘルパー。time.sleep で1回ループ後に終了。"""
    mock_monitor = MagicMock()

    with patch("kabusys.run_monitoring.set_process_priority") as mock_priority, \
         patch("kabusys.run_monitoring.Settings") as mock_settings_cls, \
         patch("kabusys.run_monitoring.sqlite3.connect") as mock_sqlite, \
         patch("kabusys.run_monitoring.init_monitoring_db"), \
         patch("kabusys.run_monitoring.duckdb.connect"), \
         patch("kabusys.run_monitoring.SystemMonitor", return_value=mock_monitor), \
         patch("kabusys.run_monitoring.time.sleep", side_effect=KeyboardInterrupt):

        mock_settings_cls.return_value = _make_settings()

        from kabusys.run_monitoring import main
        main()

    return mock_priority, mock_sqlite, mock_monitor


class TestRunMonitoringMain:
    def test_sets_high_priority_first(self):
        mock_priority, _, _ = _run_main()
        mock_priority.assert_called_once_with("high")

    def test_calls_check_once(self):
        _, _, mock_monitor = _run_main()
        mock_monitor.check_once.assert_called()

    def test_uses_sqlite_path(self):
        _, mock_sqlite, _ = _run_main()
        settings = _make_settings()
        mock_sqlite.assert_called_once_with(str(settings.sqlite_path))


class TestGetPollInterval:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
        assert _get_poll_interval() == 60

    def test_override(self, monkeypatch):
        monkeypatch.setenv("MONITOR_POLL_INTERVAL", "30")
        assert _get_poll_interval() == 30

    def test_invalid_uses_default(self, monkeypatch, caplog):
        monkeypatch.setenv("MONITOR_POLL_INTERVAL", "abc")
        with caplog.at_level(logging.WARNING, logger="kabusys.run_monitoring"):
            result = _get_poll_interval()
        assert result == 60
        assert "不正" in caplog.text
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_run_monitoring.py -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.run_monitoring'`

- [ ] **Step 3: `src/kabusys/run_monitoring.py` を作成**

```python
# src/kabusys/run_monitoring.py
"""run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。

MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する。
"""
from __future__ import annotations

import logging
import os
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


def _get_poll_interval() -> int:
    """MONITOR_POLL_INTERVAL 環境変数からポーリング間隔を取得する（デフォルト: 60秒）。"""
    try:
        return int(os.environ.get("MONITOR_POLL_INTERVAL", _DEFAULT_POLL_INTERVAL))
    except ValueError:
        logger.warning(
            "MONITOR_POLL_INTERVAL の値が不正です。デフォルト %d 秒を使用します。",
            _DEFAULT_POLL_INTERVAL,
        )
        return _DEFAULT_POLL_INTERVAL


def main() -> None:
    # 1. プロセス優先度を High に設定（最初に実行）
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
    poll_interval = _get_poll_interval()
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

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_run_monitoring.py -v
```

Expected: 6 passed

- [ ] **Step 5: 全テスト（21件）が通ることを確認**

```bash
python -m pytest tests/test_process_priority.py tests/test_run_execution.py tests/test_run_monitoring.py -v
```

Expected: 21 passed

- [ ] **Step 6: 既存テスト全体が壊れていないことを確認**

```bash
python -m pytest tests/ -q --tb=short --ignore=tests/test_generated.py
```

Expected: 全テスト passed

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/run_monitoring.py tests/test_run_monitoring.py
git commit -m "feat: add run_monitoring.py startup script with High priority polling loop (Issue #43)"
```
