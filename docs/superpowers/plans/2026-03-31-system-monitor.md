# SystemMonitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `src/kabusys/monitoring/system_monitor.py` を実装し、CPU/メモリ/ディスク監視・Execution プロセス生存確認（PID ファイル方式）・株価データ鮮度チェックを行う `SystemMonitor` クラスを構築する。

**Architecture:** `order_repository.py` / `monitoring_db.py` と同じパターン — `SystemMonitor(conn, duckdb_conn, pid_file)` が `check_once()` を持ち、呼び出し元がポーリング間隔を管理する。`psutil` でシステムメトリクスを取得し、`MonitoringDB.log_system_status()` で SQLite に記録する。`ExecutionEngine.run_session()` に PID ファイル書き出し/削除を追加する。

**Tech Stack:** Python 3.13, psutil>=5.9, SQLite3, DuckDB, pytest

---

## File Structure

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/kabusys/monitoring/system_monitor.py` | 新規作成 | `SystemCheckResult`, `SystemMonitor` |
| `src/kabusys/monitoring/__init__.py` | 修正 | `SystemMonitor`, `SystemCheckResult` エクスポート追加 |
| `src/kabusys/execution/execution_engine.py` | 修正 | PID 書き出し/削除（`run_session` 先頭と `finally`）、`pid_file` パラメータ追加 |
| `src/kabusys/config.py` | 修正 | `pid_file_path`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct` 追加 |
| `requirements.txt` | 修正 | `psutil>=5.9,<7` 追加 |
| `tests/conftest.py` | 修正 | `duckdb_prices_conn` フィクスチャ追加 |
| `tests/test_system_monitor.py` | 新規作成 | 全テストケース |

---

## Task 1: `requirements.txt` + `config.py` への設定追加

**Files:**
- Modify: `requirements.txt`
- Modify: `src/kabusys/config.py:166`

- [ ] **Step 1: `requirements.txt` に psutil を追加**

`requirements.txt` の末尾に追加:

```
psutil>=5.9,<7
```

- [ ] **Step 2: psutil がインストールできることを確認**

```bash
pip install psutil
python -c "import psutil; print(psutil.version_info)"
```

Expected: バージョンタプルが表示される（エラーなし）

- [ ] **Step 3: `config.py` に監視設定プロパティを追加**

`src/kabusys/config.py` の `sqlite_path` プロパティ（`:166`）の直後、`# --- システム設定 ---` の前に以下を追加:

```python
    # --- 監視設定 ---
    @property
    def pid_file_path(self) -> Path:
        return Path(os.environ.get("PID_FILE_PATH", "data/execution.pid")).expanduser()

    @property
    def cpu_threshold_pct(self) -> float:
        return float(os.environ.get("CPU_THRESHOLD_PCT", "90.0"))

    @property
    def memory_threshold_pct(self) -> float:
        return float(os.environ.get("MEMORY_THRESHOLD_PCT", "85.0"))

    @property
    def disk_threshold_pct(self) -> float:
        return float(os.environ.get("DISK_THRESHOLD_PCT", "90.0"))
```

- [ ] **Step 4: config が正しく読めることを確認**

```bash
python -c "from kabusys.config import config; print(config.pid_file_path, config.cpu_threshold_pct)"
```

Expected: `data\execution.pid 90.0`

- [ ] **Step 5: 既存テストが壊れていないことを確認**

```bash
python -m pytest tests/ --tb=short -q
```

Expected: 全テストが PASS（リグレッションなし）

- [ ] **Step 6: コミット**

```bash
git add requirements.txt src/kabusys/config.py
git commit -m "feat: add psutil dependency and monitoring config properties (Issue #37)"
```

---

## Task 2: `SystemCheckResult` + `SystemMonitor` の骨格作成

**Files:**
- Create: `src/kabusys/monitoring/system_monitor.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_system_monitor.py`

- [ ] **Step 1: `duckdb_prices_conn` フィクスチャを `conftest.py` に追加**

`tests/conftest.py` の末尾に追加（既存コードはそのまま保持）:

```python
import duckdb as _duckdb


@pytest.fixture
def duckdb_prices_conn():
    """raw_prices テーブルを持つインメモリ DuckDB（SystemMonitor テスト専用）。"""
    conn = _duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE raw_prices (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            open DECIMAL(18,4), high DECIMAL(18,4),
            low DECIMAL(18,4), close DECIMAL(18,4),
            volume BIGINT, turnover DECIMAL(18,2),
            fetched_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY (date, code)
        )
    """)
    yield conn
    conn.close()
```

- [ ] **Step 2: 失敗するテストを作成**

`tests/test_system_monitor.py` を新規作成:

```python
"""SystemMonitor 単体テスト（Issue #37）"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kabusys.monitoring.system_monitor import SystemCheckResult, SystemMonitor


@pytest.fixture
def monitor(monitoring_conn, duckdb_prices_conn, tmp_path):
    pid_file = tmp_path / "execution.pid"
    return SystemMonitor(monitoring_conn, duckdb_prices_conn, pid_file=pid_file)


class TestCheckOnce:

    def test_healthy_system_writes_db(self, monitor, monitoring_conn):
        """check_once() 後に system_status に1行書き込まれる"""
        with patch("psutil.cpu_percent", return_value=30.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=50.0)
            mock_disk.return_value = MagicMock(percent=60.0)
            monitor.check_once(today=date(2026, 3, 31))

        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM system_status"
        ).fetchone()[0]
        assert count == 1

    def test_returns_correct_result_fields(self, monitor):
        """SystemCheckResult の全フィールドが存在し型が正しい"""
        with patch("psutil.cpu_percent", return_value=30.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=50.0)
            mock_disk.return_value = MagicMock(percent=60.0)
            result = monitor.check_once(today=date(2026, 3, 31))

        assert isinstance(result, SystemCheckResult)
        assert isinstance(result.recorded_at, str)
        assert isinstance(result.cpu_percent, float)
        assert isinstance(result.memory_percent, float)
        assert isinstance(result.disk_percent, float)
        assert isinstance(result.process_ok, bool)
        assert isinstance(result.data_freshness_ok, bool)
        assert isinstance(result.stale_pid_detected, bool)
```

- [ ] **Step 3: テストが失敗することを確認**

```bash
python -m pytest tests/test_system_monitor.py::TestCheckOnce -v
```

Expected: `ModuleNotFoundError` または `ImportError`

- [ ] **Step 4: `system_monitor.py` の骨格を作成**

`src/kabusys/monitoring/system_monitor.py` を新規作成:

```python
# src/kabusys/monitoring/system_monitor.py
"""SystemMonitor — CPU/メモリ/ディスク・プロセス生存・データ鮮度を1回チェックして記録するクラス。

ポーリング間隔の管理は呼び出し元が担当。内部ループは持たない。
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import psutil
from duckdb import DuckDBPyConnection

from kabusys.data import pipeline
from kabusys.monitoring.monitoring_db import MonitoringDB

DATA_STALE_DAYS = 3  # 株価データが N 日以上古い場合を異常とする


@dataclass
class SystemCheckResult:
    recorded_at: str          # ISO8601 UTC
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    process_ok: bool          # プロセスが生存しているか
    data_freshness_ok: bool   # 株価データが十分新鮮か
    stale_pid_detected: bool  # stale PID を検出・削除した場合 True


class SystemMonitor:
    """システム状態・データ鮮度を1回チェックして MonitoringDB に記録するクラス。"""

    def __init__(
        self,
        conn: sqlite3.Connection,
        duckdb_conn: DuckDBPyConnection,
        pid_file: Path = Path("data/execution.pid"),
    ) -> None:
        self._db = MonitoringDB(conn)
        self._duckdb_conn = duckdb_conn
        self._pid_file = pid_file

    def check_once(self, today: date | None = None) -> SystemCheckResult:
        """1回分のシステム状態チェックを実行し、DB に記録して結果を返す。

        Args:
            today: データ鮮度判定の基準日（None → date.today()）。テスト時に注入。
        """
        raise NotImplementedError
```

- [ ] **Step 5: テストがまだ失敗することを確認（NotImplementedError）**

```bash
python -m pytest tests/test_system_monitor.py::TestCheckOnce -v
```

Expected: `NotImplementedError`

- [ ] **Step 6: コミット（骨格のみ）**

```bash
git add src/kabusys/monitoring/system_monitor.py tests/conftest.py tests/test_system_monitor.py
git commit -m "feat: add SystemMonitor skeleton and TestCheckOnce tests (Issue #37)"
```

---

## Task 3: `check_once()` の実装

**Files:**
- Modify: `src/kabusys/monitoring/system_monitor.py`

- [ ] **Step 1: `check_once()` と内部ヘルパーを実装**

`system_monitor.py` の `SystemMonitor` クラスを以下の完全な実装に置き換える:

```python
class SystemMonitor:
    """システム状態・データ鮮度を1回チェックして MonitoringDB に記録するクラス。"""

    def __init__(
        self,
        conn: sqlite3.Connection,
        duckdb_conn: DuckDBPyConnection,
        pid_file: Path = Path("data/execution.pid"),
    ) -> None:
        self._db = MonitoringDB(conn)
        self._duckdb_conn = duckdb_conn
        self._pid_file = pid_file

    def check_once(self, today: date | None = None) -> SystemCheckResult:
        """1回分のシステム状態チェックを実行し、DB に記録して結果を返す。

        Args:
            today: データ鮮度判定の基準日（None → date.today()）。テスト時に注入。
        """
        if today is None:
            today = date.today()

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        # Windows 対応: "/" は無効。Path.cwd().drive（例: "C:\\"）を使用。
        # 空の場合（Linux/テスト）は "/" にフォールバック。
        disk_path = Path.cwd().drive + "\\" if Path.cwd().drive else "/"
        disk = psutil.disk_usage(disk_path).percent

        process_ok, stale_pid_detected = self._check_process()
        data_freshness_ok = self._check_data_freshness(today)

        now_utc = datetime.now(timezone.utc)
        self._db.log_system_status(
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
            recorded_at=now_utc,
        )

        return SystemCheckResult(
            recorded_at=now_utc.isoformat(),
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
            data_freshness_ok=data_freshness_ok,
            stale_pid_detected=stale_pid_detected,
        )

    def _check_process(self) -> tuple[bool, bool]:
        """PID ファイルを確認してプロセス生存を判定する。

        Returns:
            (process_ok, stale_pid_detected)
        """
        if not self._pid_file.exists():
            return False, False

        try:
            pid = int(self._pid_file.read_text().strip())
        except (ValueError, OSError):
            self._pid_file.unlink(missing_ok=True)
            return False, True

        if psutil.pid_exists(pid):
            return True, False

        # Stale PID: プロセス死亡 → ファイル削除
        self._pid_file.unlink(missing_ok=True)
        return False, True

    def _check_data_freshness(self, today: date) -> bool:
        """DuckDB の最終株価更新日が十分新しいか確認する。

        Returns:
            True if (today - last_price_date).days <= DATA_STALE_DAYS
        """
        last = pipeline.get_last_price_date(self._duckdb_conn)
        if last is None:
            return False
        return (today - last).days <= DATA_STALE_DAYS
```

- [ ] **Step 2: TestCheckOnce テストを実行してパスを確認**

```bash
python -m pytest tests/test_system_monitor.py::TestCheckOnce -v
```

Expected: `2 passed`

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/monitoring/system_monitor.py
git commit -m "feat: implement SystemMonitor.check_once (Issue #37)"
```

---

## Task 4: プロセス生存チェックのテスト

**Files:**
- Modify: `tests/test_system_monitor.py`

- [ ] **Step 1: TestProcessCheck テストを追加**

`tests/test_system_monitor.py` に追加:

```python
class TestProcessCheck:

    def test_no_pid_file_process_ok_false(self, monitor):
        """PID ファイルなし → process_ok=False, stale_pid_detected=False"""
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = monitor.check_once(today=date(2026, 3, 31))

        assert result.process_ok is False
        assert result.stale_pid_detected is False

    def test_valid_pid_process_ok_true(self, monitor, tmp_path):
        """自プロセスの PID を書いたファイル → process_ok=True"""
        pid_file = tmp_path / "execution.pid"
        pid_file.write_text(str(os.getpid()))
        mon = SystemMonitor(monitor._db._conn, monitor._duckdb_conn, pid_file=pid_file)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=date(2026, 3, 31))

        assert result.process_ok is True
        assert result.stale_pid_detected is False

    def test_stale_pid_detected_and_deleted(self, monitor, tmp_path):
        """存在しない PID → process_ok=False, stale_pid_detected=True, ファイル削除"""
        pid_file = tmp_path / "execution.pid"
        pid_file.write_text("999999999")  # 存在しない PID
        mon = SystemMonitor(monitor._db._conn, monitor._duckdb_conn, pid_file=pid_file)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk, \
             patch("psutil.pid_exists", return_value=False):
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=date(2026, 3, 31))

        assert result.process_ok is False
        assert result.stale_pid_detected is True
        assert not pid_file.exists()
```

- [ ] **Step 2: テストを実行してパスを確認**

```bash
python -m pytest tests/test_system_monitor.py::TestProcessCheck -v
```

Expected: `3 passed`

- [ ] **Step 3: コミット**

```bash
git add tests/test_system_monitor.py
git commit -m "feat: add TestProcessCheck tests for PID file monitoring (Issue #37)"
```

---

## Task 5: データ鮮度チェックのテスト

**Files:**
- Modify: `tests/test_system_monitor.py`

- [ ] **Step 1: TestDataFreshness テストを追加**

`tests/test_system_monitor.py` に追加:

```python
class TestDataFreshness:

    def _make_monitor(self, monitoring_conn, duckdb_prices_conn, tmp_path):
        pid_file = tmp_path / "execution.pid"
        return SystemMonitor(monitoring_conn, duckdb_prices_conn, pid_file=pid_file)

    def test_fresh_data_ok(self, monitoring_conn, duckdb_prices_conn, tmp_path):
        """当日の株価データあり → data_freshness_ok=True"""
        today = date(2026, 3, 31)
        duckdb_prices_conn.execute(
            "INSERT INTO raw_prices (date, code) VALUES (?, ?)",
            [today, "1234"],
        )
        mon = self._make_monitor(monitoring_conn, duckdb_prices_conn, tmp_path)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=today)

        assert result.data_freshness_ok is True

    def test_stale_data_not_ok(self, monitoring_conn, duckdb_prices_conn, tmp_path):
        """4日以上古い株価データ → data_freshness_ok=False"""
        today = date(2026, 3, 31)
        stale_date = date(2026, 3, 27)  # 4日前
        duckdb_prices_conn.execute(
            "INSERT INTO raw_prices (date, code) VALUES (?, ?)",
            [stale_date, "1234"],
        )
        mon = self._make_monitor(monitoring_conn, duckdb_prices_conn, tmp_path)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=today)

        assert result.data_freshness_ok is False

    def test_no_data_not_ok(self, monitoring_conn, duckdb_prices_conn, tmp_path):
        """データなし（空テーブル）→ data_freshness_ok=False"""
        mon = self._make_monitor(monitoring_conn, duckdb_prices_conn, tmp_path)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=date(2026, 3, 31))

        assert result.data_freshness_ok is False
```

- [ ] **Step 2: テストを実行してパスを確認**

```bash
python -m pytest tests/test_system_monitor.py::TestDataFreshness -v
```

Expected: `3 passed`

- [ ] **Step 3: コミット**

```bash
git add tests/test_system_monitor.py
git commit -m "feat: add TestDataFreshness tests for data freshness check (Issue #37)"
```

---

## Task 6: `ExecutionEngine` への PID ファイル対応追加

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py`
- Modify: `tests/test_system_monitor.py`

- [ ] **Step 1: TestExecutionEnginePid テストを追加**

`tests/test_system_monitor.py` に追加（ファイル末尾）:

```python
class TestExecutionEnginePid:

    def _make_engine(self, tmp_path):
        """テスト用 ExecutionEngine を最小モックで構築する。"""
        from datetime import date, time
        from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine

        broker = MagicMock()
        repo = MagicMock()
        risk_manager = MagicMock()
        order_manager = MagicMock()
        duckdb_conn = MagicMock()
        cfg = EngineConfig(
            target_date=date(2026, 3, 31),
            signal_send_start=time(8, 50),
            signal_send_end=time(9, 10),
            market_close=time(15, 30),
        )
        pid_file = tmp_path / "execution.pid"
        return ExecutionEngine(
            broker, repo, risk_manager, order_manager, duckdb_conn, cfg,
            pid_file=pid_file,
        ), pid_file

    def test_pid_file_written_on_start(self, tmp_path):
        """run_session() 開始時に PID ファイルが生成される"""
        engine, pid_file = self._make_engine(tmp_path)
        pid_existed_during = []

        def capture_and_raise():
            pid_existed_during.append(pid_file.exists())
            raise KeyboardInterrupt

        with patch.object(engine, "_process_signals", side_effect=capture_and_raise), \
             patch.object(engine, "_websocket_worker"):
            with pytest.raises(KeyboardInterrupt):
                engine.run_session()

        assert pid_existed_during[0] is True  # 実行中は PID ファイルが存在した

    def test_pid_file_removed_on_clean_exit(self, tmp_path):
        """finally ブロックで PID ファイルが削除される"""
        engine, pid_file = self._make_engine(tmp_path)

        with patch.object(engine, "_process_signals", side_effect=KeyboardInterrupt), \
             patch.object(engine, "_websocket_worker"):
            with pytest.raises(KeyboardInterrupt):
                engine.run_session()

        # KeyboardInterrupt 後も finally で削除される
        assert not pid_file.exists()
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_system_monitor.py::TestExecutionEnginePid -v
```

Expected: `TypeError` — `ExecutionEngine.__init__()` に `pid_file` パラメータがない

- [ ] **Step 3: `ExecutionEngine` に `pid_file` パラメータと PID 書き出し/削除を追加**

`src/kabusys/execution/execution_engine.py` の `ExecutionEngine.__init__` に `pid_file` を追加し、`run_session()` を修正する:

`__init__` の引数に追加（`reconciler: Reconciler | None = None` の後）:

```python
        pid_file: Path | None = None,
```

`__init__` の `self._reconciler = reconciler` の後に追加:

```python
        self._pid_file: Path | None = pid_file
```

`run_session()` の先頭（`logger.info("ExecutionEngine: セッション開始 ...")` の直後）に追加:

```python
        # PID ファイルへの書き出し（None の場合は config.pid_file_path を使用）
        from kabusys.config import config as _config
        _active_pid_file = self._pid_file if self._pid_file is not None else _config.pid_file_path
        _active_pid_file.parent.mkdir(parents=True, exist_ok=True)
        _active_pid_file.write_text(str(os.getpid()))
```

`run_session()` 末尾の `logger.info("ExecutionEngine: セッション終了")` を `try/finally` で囲む（`_active_pid_file` を `finally` で削除）:

```python
        try:
            # WebSocket スレッド起動
            ws_thread = threading.Thread(target=self._websocket_worker, daemon=True, name="ws-push")
            ws_thread.start()

            def _now_time() -> time:
                return datetime.now().time().replace(microsecond=0)

            # signal_send_start まで待機
            while _now_time() < self._config.signal_send_start and not self._stop_event.is_set():
                self._stop_event.wait(timeout=5.0)

            # シグナル処理ループ（8:50 ～ 9:10）
            if not self._stop_event.is_set() and _now_time() < self._config.signal_send_end:
                self._process_signals()

            # push drain ループ（9:10 ～ 15:30）
            while _now_time() < self._config.market_close and not self._stop_event.is_set():
                self._drain_push_queue()
                self._stop_event.wait(timeout=1.0)

            # セッション終了
            self._stop_event.set()
            ws_thread.join(timeout=5.0)
            logger.info("ExecutionEngine: セッション終了")
        finally:
            _active_pid_file.unlink(missing_ok=True)
```

また、`execution_engine.py` の先頭の import に `os` と `Path` を追加:

```python
import os
from pathlib import Path
```

- [ ] **Step 4: テストを実行してパスを確認**

```bash
python -m pytest tests/test_system_monitor.py::TestExecutionEnginePid -v
```

Expected: `2 passed`

- [ ] **Step 5: 全テストでリグレッションなしを確認**

```bash
python -m pytest --tb=short -q
```

Expected: 全テストが PASS（リグレッションなし）

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/execution/execution_engine.py tests/test_system_monitor.py
git commit -m "feat: add PID file support to ExecutionEngine.run_session (Issue #37)"
```

---

## Task 7: `__init__.py` エクスポート追加 + 全テスト確認

**Files:**
- Modify: `src/kabusys/monitoring/__init__.py`

- [ ] **Step 1: `__init__.py` を更新**

`src/kabusys/monitoring/__init__.py` を以下の内容で上書き:

```python
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
from kabusys.monitoring.system_monitor import SystemCheckResult, SystemMonitor

__all__ = [
    "MonitoringDB",
    "init_monitoring_db",
    "SystemCheckResult",
    "SystemMonitor",
]
```

- [ ] **Step 2: インポートが機能することを確認**

```bash
python -m pytest tests/test_system_monitor.py -v
```

Expected: 全テストが PASS（最低 10 件）

- [ ] **Step 3: 全テストでリグレッションなしを確認**

```bash
python -m pytest --tb=short -q
```

Expected: 全テストが PASS

- [ ] **Step 4: コミット**

```bash
git add src/kabusys/monitoring/__init__.py
git commit -m "feat: export SystemMonitor and SystemCheckResult from monitoring package (Issue #37)"
```
