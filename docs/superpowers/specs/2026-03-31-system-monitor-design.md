# SystemMonitor 設計仕様

> **For agentic workers:** このドキュメントは Issue #37「【Phase 7】システム・データ監視エンジン実装」の設計仕様です。
> 実装前に必ず本ドキュメントを参照してください。

---

## 1. 目的

`src/kabusys/monitoring/system_monitor.py` を実装し、Phase 7 監視システムのシステム・データ監視エンジンを構築する。

- CPU / メモリ / ディスク使用率の収集と閾値監視
- `ExecutionEngine` プロセスの生存確認（PID ファイル方式）
- DuckDB の株価データ鮮度チェック
- 結果を `MonitoringDB.log_system_status()` で SQLite に記録

対象 Issue: #37「【Phase 7】システム・データ監視エンジン実装」

---

## 2. 前提・既存インフラ

| 要素 | 場所 | 内容 |
|---|---|---|
| `MonitoringDB.log_system_status()` | `monitoring_db.py` | `system_status` テーブルへの追記（#36 実装済み） |
| `pipeline.get_last_price_date()` | `data/pipeline.py` | DuckDB から最終株価更新日を取得 |
| `config.sqlite_path` / `config.duckdb_path` | `config.py:166` | DB ファイルパス |
| `ExecutionEngine.run_session()` | `execution/execution_engine.py` | PID 書き出し/削除を追加する対象 |

---

## 3. アーキテクチャ

```
src/kabusys/monitoring/
├── monitoring_db.py      ← 既存（#36）
├── system_monitor.py     ← 新規作成
└── __init__.py           ← SystemMonitor をエクスポート追加

src/kabusys/execution/
└── execution_engine.py   ← 修正: PID 書き出し/削除

src/kabusys/config.py     ← 修正: pid_file_path, 閾値設定追加

requirements.txt          ← 修正: psutil 追加

data/
└── execution.pid         ← 実行時生成（.gitignore 確認済み）

tests/
└── test_system_monitor.py  ← 新規作成
```

---

## 4. `config.py` への追加設定

`Config` クラスに以下のプロパティを追加する（既存の `sqlite_path` の近くに配置）:

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

---

## 5. `requirements.txt` への追加

```
psutil>=5.9,<7
```

---

## 6. PID ファイル設計

### `ExecutionEngine.run_session()` への変更

`run_session()` の先頭（reconciler 実行直後）と `finally` ブロックに以下を追加:

```python
import os
from kabusys.config import config

def run_session(self) -> None:
    pid_file = config.pid_file_path
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))
    try:
        # ... 既存の処理 ...
    finally:
        pid_file.unlink(missing_ok=True)
```

### 異常終了時のリカバリ方針

| 状態 | 判定 | `SystemMonitor` の対応 |
|---|---|---|
| PID ファイルなし | プロセス未起動 or 正常終了 | `process_ok=False`、stale なし |
| PID ファイルあり・プロセス生存 | 正常稼働 | `process_ok=True` |
| PID ファイルあり・プロセス死亡 | **異常終了（stale PID）** | `process_ok=False`、PID ファイル削除、`stale_pid_detected=True` |

- stale PID 検出時: PID ファイルを削除し、次回 `ExecutionEngine` 起動時にクリーンな状態で起動できるようにする
- プロセスの自動再起動は行わない（`Reconciler` が次回起動時に状態復旧を担当）
- `stale_pid_detected=True` の場合、呼び出し元（将来の #39 Slack アラート等）がアラートを発報する

---

## 7. `SystemMonitor` クラス API

```python
from __future__ import annotations

import os
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
    recorded_at: str           # ISO8601 UTC
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    process_ok: bool           # プロセスが生存しているか
    data_freshness_ok: bool    # 株価データが十分新鮮か
    stale_pid_detected: bool   # stale PID を検出・削除した場合 True


class SystemMonitor:
    """システム状態・データ鮮度を1回チェックして MonitoringDB に記録するクラス。

    ポーリング間隔の管理は呼び出し元が担当。
    """

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
        """1回分のシステム状態チェックを実行し、DBに記録して結果を返す。

        Args:
            today: データ鮮度判定の基準日（None → date.today()）。テスト時に注入。
        """
        if today is None:
            today = date.today()

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        process_ok, stale_pid_detected = self._check_process()
        data_freshness_ok = self._check_data_freshness(today)

        recorded_at = datetime.now(timezone.utc).isoformat()
        self._db.log_system_status(
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
        )

        return SystemCheckResult(
            recorded_at=recorded_at,
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

---

## 8. エクスポート

### `src/kabusys/monitoring/__init__.py`

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

---

## 9. テスト仕様（`tests/test_system_monitor.py`）

`conftest.py` に `duckdb_prices_conn` フィクスチャを追加:

```python
@pytest.fixture
def duckdb_prices_conn():
    """raw_prices テーブルを持つインメモリ DuckDB。"""
    conn = duckdb.connect(":memory:")
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

| テストクラス / ケース | 検証内容 |
|---|---|
| `TestCheckOnce` | |
| `test_healthy_system_writes_db` | `check_once()` 後に `system_status` に1行書き込まれる |
| `test_returns_correct_result_fields` | `SystemCheckResult` の全フィールドが存在し型が正しい |
| `TestProcessCheck` | |
| `test_no_pid_file_process_ok_false` | PID ファイルなし → `process_ok=False`, `stale_pid_detected=False` |
| `test_valid_pid_process_ok_true` | 自プロセスの PID を書いたファイル → `process_ok=True` |
| `test_stale_pid_detected_and_deleted` | 存在しない PID を書いたファイル → `process_ok=False`, `stale_pid_detected=True`, ファイル削除 |
| `TestDataFreshness` | |
| `test_fresh_data_ok` | 当日の株価データあり → `data_freshness_ok=True` |
| `test_stale_data_not_ok` | 4日以上古い株価データ → `data_freshness_ok=False` |
| `test_no_data_not_ok` | データなし → `data_freshness_ok=False` |
| `TestExecutionEnginePid` | |
| `test_pid_file_written_on_start` | `run_session()` 開始時に PID ファイルが生成される |
| `test_pid_file_removed_on_clean_exit` | 正常終了後に PID ファイルが削除される |

---

## 10. ファイル変更サマリー

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/kabusys/monitoring/system_monitor.py` | 新規作成 | `SystemCheckResult`, `SystemMonitor` |
| `src/kabusys/monitoring/__init__.py` | 修正 | `SystemMonitor`, `SystemCheckResult` エクスポート追加 |
| `src/kabusys/execution/execution_engine.py` | 修正 | PID 書き出し/削除（`run_session` の先頭と `finally`） |
| `src/kabusys/config.py` | 修正 | `pid_file_path`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct` 追加 |
| `requirements.txt` | 修正 | `psutil>=5.9,<7` 追加 |
| `tests/conftest.py` | 修正 | `duckdb_prices_conn` フィクスチャ追加 |
| `tests/test_system_monitor.py` | 新規作成 | 上記テストケース |
