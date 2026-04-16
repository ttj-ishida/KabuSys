# Phase 9: Deployment Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement operational scripts for KabuSys deployment: system start/stop, night batch entry points, and Windows Task Scheduler registration (Issues #45, #46).

**Architecture:** A shared `scripts/utils.py` provides PID file and stop flag primitives. `start_system.py` / `stop_system.py` coordinate process lifecycle via a sentinel file (`data/stop_requested.flag`). Night batch scripts are thin wrappers around existing domain functions. `setup_task_scheduler.ps1` registers 7 Task Scheduler jobs.

**Tech Stack:** Python 3.10+, `psutil` (already in requirements.txt), `pathlib`, `subprocess`, `threading`, `argparse`, PowerShell for Task Scheduler registration.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `scripts/utils.py` | Create | PID file I/O, stop flag, process liveness check |
| `scripts/start_system.py` | Create | Launch execution/monitoring via subprocess |
| `scripts/stop_system.py` | Create | Graceful stop with 10s timeout + force kill |
| `scripts/run_data_update.py` | Create | Night batch: run_daily_etl wrapper |
| `scripts/run_feature_gen.py` | Create | Night batch: build_features wrapper |
| `scripts/run_ai_analysis.py` | Create | Night batch: score_news + score_regime |
| `scripts/run_strategy_signal.py` | Create | Night batch: generate_signals wrapper |
| `scripts/run_portfolio_construction.py` | Create | Night batch: signals→select_candidates→signal_queue |
| `scripts/reset_signals.py` | Create | DELETE FROM signal_queue |
| `scripts/rebuild_features.py` | Create | Prerequisite check + build_features |
| `scripts/setup_task_scheduler.ps1` | Create | Register 7 Windows Task Scheduler jobs |
| `src/kabusys/run_execution.py` | Modify | Add thread + stop flag polling |
| `src/kabusys/run_monitoring.py` | Modify | Add stop flag check in while loop |
| `tests/test_scripts_utils.py` | Create | Unit tests for utils.py |
| `tests/test_start_system.py` | Create | Unit tests for start_system.py |
| `tests/test_stop_system.py` | Create | Unit tests for stop_system.py |
| `tests/test_scripts_batch.py` | Create | Unit tests for maintenance + batch scripts |

---

## Task 1: `scripts/utils.py` — Shared Utilities

**Files:**
- Create: `scripts/utils.py`
- Create: `tests/test_scripts_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scripts_utils.py
"""scripts/utils.py の単体テスト"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# scripts/ ディレクトリを PYTHONPATH に追加してインポート
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import utils as script_utils


def test_read_pid_missing_file(tmp_path):
    assert script_utils.read_pid(tmp_path / "missing.pid") is None


def test_read_pid_invalid_content(tmp_path):
    p = tmp_path / "bad.pid"
    p.write_text("not-an-int")
    assert script_utils.read_pid(p) is None


def test_write_and_read_pid_roundtrip(tmp_path):
    p = tmp_path / "test.pid"
    script_utils.write_pid(p, 12345)
    assert script_utils.read_pid(p) == 12345


def test_write_pid_creates_parent_dirs(tmp_path):
    p = tmp_path / "sub" / "dir" / "test.pid"
    script_utils.write_pid(p, 99)
    assert p.exists()


def test_delete_pid_removes_file(tmp_path):
    p = tmp_path / "test.pid"
    p.write_text("1")
    script_utils.delete_pid(p)
    assert not p.exists()


def test_delete_pid_missing_file_is_noop(tmp_path):
    script_utils.delete_pid(tmp_path / "nonexistent.pid")  # should not raise


def test_is_process_running_current_process():
    assert script_utils.is_process_running(os.getpid()) is True


def test_is_process_running_invalid_pid():
    assert script_utils.is_process_running(9_999_999) is False


def test_stop_flag_lifecycle(tmp_path):
    flag = tmp_path / "stop.flag"
    assert not script_utils.stop_requested(flag)
    script_utils.request_stop(flag)
    assert script_utils.stop_requested(flag)
    script_utils.clear_stop_flag(flag)
    assert not script_utils.stop_requested(flag)


def test_request_stop_creates_parent_dirs(tmp_path):
    flag = tmp_path / "sub" / "stop.flag"
    script_utils.request_stop(flag)
    assert flag.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:\Users\tetsu\Projects\KabuSys
pytest tests/test_scripts_utils.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'utils'`

- [ ] **Step 3: Create `scripts/utils.py`**

```python
# scripts/utils.py
"""PIDファイル・停止フラグ・プロセス生存確認の共通ユーティリティ。

すべての scripts/*.py から import して使う。
run_execution.py / run_monitoring.py は直接 _STOP_FLAG パスを使うため
このモジュールを import しない（PYTHONPATH 問題を避けるため）。
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import psutil
except ImportError:
    print(
        "ERROR: psutil がインストールされていません。"
        "pip install psutil を実行してください。",
        file=sys.stderr,
    )
    sys.exit(1)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXECUTION_PID_PATH = _PROJECT_ROOT / "data" / "execution.pid"
MONITORING_PID_PATH = _PROJECT_ROOT / "data" / "monitoring.pid"
STOP_FLAG_PATH = _PROJECT_ROOT / "data" / "stop_requested.flag"


def read_pid(path: Path) -> int | None:
    """PID ファイルを読み込む。ファイルが存在しないか不正な場合は None を返す。"""
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def write_pid(path: Path, pid: int) -> None:
    """PID をファイルに書き込む。親ディレクトリが存在しない場合は作成する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid))


def delete_pid(path: Path) -> None:
    """PID ファイルを削除する。存在しない場合は何もしない。"""
    path.unlink(missing_ok=True)


def is_process_running(pid: int) -> bool:
    """指定された PID のプロセスが生存しているかを返す。"""
    return psutil.pid_exists(pid)


def request_stop(flag_path: Path = STOP_FLAG_PATH) -> None:
    """停止フラグファイルを作成する。親ディレクトリが存在しない場合は作成する。"""
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.touch()


def stop_requested(flag_path: Path = STOP_FLAG_PATH) -> bool:
    """停止フラグファイルが存在するかを返す。"""
    return flag_path.exists()


def clear_stop_flag(flag_path: Path = STOP_FLAG_PATH) -> None:
    """停止フラグファイルを削除する。存在しない場合は何もしない。"""
    flag_path.unlink(missing_ok=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scripts_utils.py -v
```

Expected: 9 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/utils.py tests/test_scripts_utils.py
git commit -m "feat: add scripts/utils.py - PID file and stop flag utilities"
```

---

## Task 2: `scripts/start_system.py` — System Start

**Files:**
- Create: `scripts/start_system.py`
- Create: `tests/test_start_system.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_start_system.py
"""scripts/start_system.py の単体テスト"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _run_start(args: list[str] | None = None):
    """start_system.main() をモックで実行する。sys.argv をオーバーライド。"""
    import start_system
    with patch.object(sys, "argv", ["start_system.py"] + (args or [])):
        return start_system.main()


def test_start_clears_existing_stop_flag(tmp_path):
    flag = tmp_path / "stop.flag"
    flag.touch()

    with patch("start_system.STOP_FLAG_PATH", flag), \
         patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"), \
         patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("start_system.is_process_running", return_value=False), \
         patch("start_system.subprocess.Popen") as mock_popen, \
         patch("start_system.write_pid"):
        mock_popen.return_value.pid = 1234
        _run_start()

    assert not flag.exists()


def test_start_already_running_exits_1(tmp_path):
    pid_path = tmp_path / "exec.pid"
    pid_path.write_text("1234")

    with patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("start_system.EXECUTION_PID_PATH", pid_path), \
         patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("start_system.is_process_running", return_value=True):
        with pytest.raises(SystemExit) as exc:
            _run_start(["--component", "execution"])
        assert exc.value.code == 1


def test_start_component_execution_only(tmp_path):
    launched = []

    def fake_popen(cmd, **kwargs):
        launched.append(cmd)
        m = MagicMock()
        m.pid = 9999
        return m

    with patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"), \
         patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("start_system.is_process_running", return_value=False), \
         patch("start_system.subprocess.Popen", side_effect=fake_popen), \
         patch("start_system.write_pid"):
        _run_start(["--component", "execution"])

    assert len(launched) == 1
    assert "run_execution.py" in str(launched[0])


def test_start_all_launches_both(tmp_path):
    launched = []

    def fake_popen(cmd, **kwargs):
        launched.append(cmd)
        m = MagicMock()
        m.pid = 9999
        return m

    with patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"), \
         patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("start_system.is_process_running", return_value=False), \
         patch("start_system.subprocess.Popen", side_effect=fake_popen), \
         patch("start_system.write_pid"):
        _run_start()  # default = all

    assert len(launched) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_start_system.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'start_system'`

- [ ] **Step 3: Create `scripts/start_system.py`**

```python
# scripts/start_system.py
"""システム起動スクリプト。execution / monitoring プロセスを起動する。

使い方:
    python scripts/start_system.py                      # 両方起動
    python scripts/start_system.py --component execution
    python scripts/start_system.py --component monitoring
    python scripts/start_system.py --component all      # 両方（明示的）
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# scripts/ ディレクトリを sys.path に追加して utils をインポート
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    EXECUTION_PID_PATH,
    MONITORING_PID_PATH,
    STOP_FLAG_PATH,
    clear_stop_flag,
    is_process_running,
    read_pid,
    write_pid,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RUN_EXECUTION = _PROJECT_ROOT / "src" / "kabusys" / "run_execution.py"
_RUN_MONITORING = _PROJECT_ROOT / "src" / "kabusys" / "run_monitoring.py"


def _launch(script: Path, pid_path: Path) -> None:
    """スクリプトを subprocess で起動し、PID をファイルに書き込む。"""
    existing_pid = read_pid(pid_path)
    if existing_pid is not None and is_process_running(existing_pid):
        logger.warning(
            "既に起動中です (PID=%d, script=%s)。起動をスキップします。",
            existing_pid,
            script.name,
        )
        sys.exit(1)

    proc = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(_PROJECT_ROOT),
    )
    write_pid(pid_path, proc.pid)
    logger.info("%s を起動しました (PID=%d)", script.name, proc.pid)


def main() -> None:
    parser = argparse.ArgumentParser(description="KabuSys システム起動")
    parser.add_argument(
        "--component",
        choices=["execution", "monitoring", "all"],
        default="all",
        help="起動するコンポーネント (デフォルト: all)",
    )
    args = parser.parse_args()

    # 停止フラグをクリア（前回停止時のフラグが残っている場合）
    clear_stop_flag(STOP_FLAG_PATH)

    if args.component in ("execution", "all"):
        _launch(_RUN_EXECUTION, EXECUTION_PID_PATH)

    if args.component in ("monitoring", "all"):
        _launch(_RUN_MONITORING, MONITORING_PID_PATH)

    logger.info("起動完了 (component=%s)", args.component)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_start_system.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/start_system.py tests/test_start_system.py
git commit -m "feat: add scripts/start_system.py - launch execution/monitoring processes"
```

---

## Task 3: `scripts/stop_system.py` — Graceful Shutdown

**Files:**
- Create: `scripts/stop_system.py`
- Create: `tests/test_stop_system.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_stop_system.py
"""scripts/stop_system.py の単体テスト"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _run_stop(tmp_path, exec_pid=None, mon_pid=None, process_alive=True, exits_within_timeout=True):
    """stop_system.main() をモックで実行するヘルパー。"""
    import stop_system

    exec_pid_path = tmp_path / "exec.pid"
    mon_pid_path = tmp_path / "mon.pid"
    flag_path = tmp_path / "stop.flag"

    if exec_pid:
        exec_pid_path.write_text(str(exec_pid))
    if mon_pid:
        mon_pid_path.write_text(str(mon_pid))

    mock_proc = MagicMock()
    poll_results = [None, None, None, None, None, 0] if exits_within_timeout else [None] * 30

    mock_proc.poll.side_effect = poll_results

    with patch("stop_system.EXECUTION_PID_PATH", exec_pid_path), \
         patch("stop_system.MONITORING_PID_PATH", mon_pid_path), \
         patch("stop_system.STOP_FLAG_PATH", flag_path), \
         patch("stop_system.is_process_running", return_value=process_alive), \
         patch("stop_system.psutil") as mock_psutil, \
         patch("stop_system.time.sleep"), \
         patch("stop_system.time.monotonic", side_effect=list(range(60))):
        mock_psutil.Process.return_value = mock_proc
        stop_system.main()

    return flag_path, exec_pid_path, mon_pid_path, mock_proc, mock_psutil


def test_stop_creates_flag(tmp_path):
    flag, _, _, _, _ = _run_stop(tmp_path, exec_pid=1234, process_alive=False)
    assert flag.exists()  # flag は stop_system.py が残す（start_system.py がクリア）


def test_stop_graceful_no_kill(tmp_path):
    _, _, _, mock_proc, mock_psutil = _run_stop(
        tmp_path, exec_pid=1234, exits_within_timeout=True
    )
    mock_psutil.Process.return_value.kill.assert_not_called()


def test_stop_force_kill_on_timeout(tmp_path):
    _, _, _, mock_proc, mock_psutil = _run_stop(
        tmp_path, exec_pid=1234, exits_within_timeout=False
    )
    mock_psutil.Process.return_value.kill.assert_called()


def test_stop_missing_pid_file_is_skipped(tmp_path):
    # exec PIDなし、mon PIDなし → エラーにならない
    flag, exec_pid, mon_pid, _, _ = _run_stop(tmp_path)
    assert not exec_pid.exists()
    assert not mon_pid.exists()


def test_stop_deletes_pid_files_after_exit(tmp_path):
    _, exec_pid, mon_pid, _, _ = _run_stop(
        tmp_path, exec_pid=1234, mon_pid=5678, exits_within_timeout=True
    )
    assert not exec_pid.exists()
    assert not mon_pid.exists()


def test_stop_partial_failure_handles_both(tmp_path):
    """execution がグレースフル終了、monitoring がタイムアウト → kill が1回呼ばれる"""
    import stop_system

    exec_pid_path = tmp_path / "exec.pid"
    mon_pid_path = tmp_path / "mon.pid"
    flag_path = tmp_path / "stop.flag"
    exec_pid_path.write_text("1234")
    mon_pid_path.write_text("5678")

    call_count = 0

    def mock_is_running(pid):
        return True

    # execution proc exits quickly, monitoring proc never exits
    exec_proc = MagicMock()
    exec_proc.poll.side_effect = [None, 0]  # exits on second poll
    mon_proc = MagicMock()
    mon_proc.poll.return_value = None  # never exits

    def make_proc(pid):
        return exec_proc if pid == 1234 else mon_proc

    with patch("stop_system.EXECUTION_PID_PATH", exec_pid_path), \
         patch("stop_system.MONITORING_PID_PATH", mon_pid_path), \
         patch("stop_system.STOP_FLAG_PATH", flag_path), \
         patch("stop_system.is_process_running", side_effect=mock_is_running), \
         patch("stop_system.psutil") as mock_psutil, \
         patch("stop_system.time.sleep"), \
         patch("stop_system.time.monotonic", side_effect=list(range(60))):
        mock_psutil.Process.side_effect = make_proc
        stop_system.main()

    exec_proc.kill.assert_not_called()
    mon_proc.kill.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_stop_system.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'stop_system'`

- [ ] **Step 3: Create `scripts/stop_system.py`**

```python
# scripts/stop_system.py
"""システム停止スクリプト。

停止フラグファイルを作成し、execution / monitoring プロセスのグレースフル終了を待つ。
10秒以内に終了しない場合は強制終了する。
停止フラグは削除しない（次回 start_system.py 起動時にクリアされる）。
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    print("ERROR: psutil が必要です。pip install psutil を実行してください。", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    EXECUTION_PID_PATH,
    MONITORING_PID_PATH,
    STOP_FLAG_PATH,
    delete_pid,
    is_process_running,
    read_pid,
    request_stop,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_GRACEFUL_TIMEOUT_SEC = 10
_POLL_INTERVAL_SEC = 0.5


def _wait_or_kill(pid: int, label: str) -> None:
    """プロセスがグレースフルに終了するのを待ち、タイムアウト後に強制終了する。

    注意: psutil.Process には .poll() が存在しない（subprocess.Popen のメソッド）。
    プロセスの生存確認には is_process_running(pid) または psutil.pid_exists(pid) を使う。
    """
    deadline = time.monotonic() + _GRACEFUL_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if not is_process_running(pid):
            logger.info("%s (PID=%d) がグレースフルに終了しました。", label, pid)
            return
        time.sleep(_POLL_INTERVAL_SEC)
    logger.warning(
        "%s (PID=%d) がタイムアウト後も終了しません。強制終了します。", label, pid
    )
    try:
        psutil.Process(pid).kill()
    except psutil.NoSuchProcess:
        pass  # タイムアウト判定直後に終了した場合


def main() -> None:
    logger.info("停止フラグを作成します: %s", STOP_FLAG_PATH)
    request_stop(STOP_FLAG_PATH)

    for pid_path, label in [
        (EXECUTION_PID_PATH, "execution_service"),
        (MONITORING_PID_PATH, "monitoring_service"),
    ]:
        pid = read_pid(pid_path)
        if pid is None:
            logger.info(
                "%s の PID ファイルが見つかりません。スキップします。"
                "（片方のコンポーネントのみ起動中の場合は正常）",
                label,
            )
            continue
        if not is_process_running(pid):
            logger.info("%s (PID=%d) は既に停止しています。", label, pid)
            delete_pid(pid_path)
            continue

        _wait_or_kill(pid, label)
        delete_pid(pid_path)

    logger.info(
        "停止処理完了。停止フラグ (%s) は次回起動時にクリアされます。", STOP_FLAG_PATH
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_stop_system.py -v
```

Expected: 6 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/stop_system.py tests/test_stop_system.py
git commit -m "feat: add scripts/stop_system.py - graceful shutdown with 10s timeout"
```

---

## Task 4: Stop Flag Support in `run_execution.py` and `run_monitoring.py`

**Files:**
- Modify: `src/kabusys/run_execution.py` (lines 77-78: `engine.run_session()` → thread pattern)
- Modify: `src/kabusys/run_monitoring.py` (lines 70-75: add stop flag check in while loop)
- Modify: `tests/test_run_execution.py` (add test for stop flag)
- Modify: `tests/test_run_monitoring.py` (add test for stop flag)

- [ ] **Step 1: Write the failing test for `run_execution.py`**

Add to `tests/test_run_execution.py`:

```python
def test_run_execution_stops_on_flag(tmp_path):
    """停止フラグが作成されたとき engine.stop() が呼ばれることを確認する。"""
    import kabusys.run_execution as re_mod

    stop_flag = tmp_path / "stop.flag"
    # フラグを事前に作成（メインループがすぐに検知する）
    stop_flag.touch()

    mock_engine = MagicMock()
    mock_engine.run_session.return_value = None  # ブロックしない

    with patch.object(re_mod, "_STOP_FLAG", stop_flag), \
         patch("kabusys.run_execution.set_process_priority"), \
         patch("kabusys.run_execution.Settings"), \
         patch("kabusys.run_execution.sqlite3.connect"), \
         patch("kabusys.run_execution.init_monitoring_db"), \
         patch("kabusys.run_execution.duckdb.connect"), \
         patch("kabusys.run_execution.BrokerClientFactory.create"), \
         patch("kabusys.run_execution.OrderRepository"), \
         patch("kabusys.run_execution.OrderManager"), \
         patch("kabusys.run_execution.RiskManager"), \
         patch("kabusys.run_execution.Reconciler"), \
         patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine):
        re_mod.main()

    mock_engine.stop.assert_called_once()
```

- [ ] **Step 2: Run the new test to verify it fails**

```bash
pytest tests/test_run_execution.py::test_run_execution_stops_on_flag -v
```

Expected: FAIL — `AttributeError: module has no attribute '_STOP_FLAG'`

- [ ] **Step 3: Modify `src/kabusys/run_execution.py`**

Read the file first. Then modify `main()` to replace the `engine.run_session()` call (around line 77) with a thread + stop flag polling pattern.

Add at the top of the file (after existing imports):

```python
import threading
from pathlib import Path

_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"
```

Replace the `engine.run_session()` call with:

```python
        thread = threading.Thread(target=engine.run_session, daemon=True)
        thread.start()
        while thread.is_alive():
            if _STOP_FLAG.exists():
                logger.info("停止フラグを検知。エンジンを停止します。")
                engine.stop()
                break
            thread.join(timeout=1.0)
        # thread.join(timeout=1.0) の while ループは以下どちらかで終了する:
        # (a) 停止フラグ検知 → engine.stop() 呼び出し
        # (b) engine.run_session() が自然終了（例: 15:30 のマーケットクローズ）
        # どちらも正常動作。
        thread.join(timeout=30.0)
```

- [ ] **Step 4: Run the new test to verify it passes**

```bash
pytest tests/test_run_execution.py -v
```

Expected: ALL PASSED

- [ ] **Step 5: Write the failing test for `run_monitoring.py`**

Add to `tests/test_run_monitoring.py`:

```python
def test_run_monitoring_stops_on_flag(tmp_path):
    """停止フラグが存在するとき監視ループが終了することを確認する。"""
    import kabusys.run_monitoring as rm_mod

    stop_flag = tmp_path / "stop.flag"
    stop_flag.touch()

    with patch.object(rm_mod, "_STOP_FLAG", stop_flag), \
         patch("kabusys.run_monitoring.set_process_priority"), \
         patch("kabusys.run_monitoring.Settings", return_value=_make_settings()), \
         patch("kabusys.run_monitoring.sqlite3.connect"), \
         patch("kabusys.run_monitoring.init_monitoring_db"), \
         patch("kabusys.run_monitoring.duckdb.connect"), \
         patch("kabusys.run_monitoring.SystemMonitor"):
        rm_mod.main()  # フラグがあるのでループせずに終了するはず
```

- [ ] **Step 6: Run the new test to verify it fails**

```bash
pytest tests/test_run_monitoring.py::test_run_monitoring_stops_on_flag -v
```

Expected: FAIL

- [ ] **Step 7: Modify `src/kabusys/run_monitoring.py`**

Read the file first. Then add the stop flag constant after existing imports:

```python
from pathlib import Path

_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"
```

Change the `while True:` loop body to add a stop flag check at the top:

```python
    try:
        while True:
            if _STOP_FLAG.exists():
                logger.info("停止フラグを検知。監視ループを終了します。")
                break
            try:
                monitor.check_once()
            except Exception:
                logger.exception("check_once() で予期しないエラーが発生しました。次のポーリングまで待機します。")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("監視ループを終了します。")
```

- [ ] **Step 8: Run all monitoring tests to verify they pass**

```bash
pytest tests/test_run_monitoring.py tests/test_run_execution.py -v
```

Expected: ALL PASSED

- [ ] **Step 9: Commit**

```bash
git add src/kabusys/run_execution.py src/kabusys/run_monitoring.py \
        tests/test_run_execution.py tests/test_run_monitoring.py
git commit -m "feat: add stop flag support to run_execution.py and run_monitoring.py"
```

---

## Task 5: Night Batch Scripts (4 simple wrappers)

**Files:**
- Create: `scripts/run_data_update.py`
- Create: `scripts/run_feature_gen.py`
- Create: `scripts/run_ai_analysis.py`
- Create: `scripts/run_strategy_signal.py`
- Create: `tests/test_scripts_batch.py` (first part)

All four scripts share the same pattern:
1. `logging.basicConfig`
2. `Settings()` + `duckdb.connect`
3. Call domain function
4. Log result + `sys.exit(0)` or `sys.exit(1)` on exception

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scripts_batch.py (作成)
"""Night batch スクリプトの単体テスト"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


# ---------- run_data_update ----------

def test_run_data_update_calls_run_daily_etl():
    import run_data_update
    mock_result = MagicMock()
    mock_result.errors = []

    with patch("run_data_update.Settings") as mock_settings, \
         patch("run_data_update.duckdb.connect"), \
         patch("run_data_update.run_daily_etl", return_value=mock_result) as mock_etl:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_data_update.main()

    mock_etl.assert_called_once()


def test_run_data_update_exits_1_on_error():
    import run_data_update

    with patch("run_data_update.Settings"), \
         patch("run_data_update.duckdb.connect"), \
         patch("run_data_update.run_daily_etl", side_effect=RuntimeError("fail")):
        with pytest.raises(SystemExit) as exc:
            run_data_update.main()
        assert exc.value.code == 1


# ---------- run_feature_gen ----------

def test_run_feature_gen_calls_build_features():
    import run_feature_gen

    with patch("run_feature_gen.Settings") as mock_settings, \
         patch("run_feature_gen.duckdb.connect"), \
         patch("run_feature_gen.build_features", return_value=5) as mock_fn:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_feature_gen.main()

    mock_fn.assert_called_once()


# ---------- run_ai_analysis ----------

def test_run_ai_analysis_calls_both_functions():
    import run_ai_analysis

    with patch("run_ai_analysis.Settings") as mock_settings, \
         patch("run_ai_analysis.duckdb.connect"), \
         patch("run_ai_analysis.score_news", return_value=3) as mock_news, \
         patch("run_ai_analysis.score_regime", return_value=1) as mock_regime:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        mock_settings.return_value.openai_api_key = "test-key"
        run_ai_analysis.main()

    mock_news.assert_called_once()
    mock_regime.assert_called_once()


# ---------- run_strategy_signal ----------

def test_run_strategy_signal_calls_generate_signals():
    import run_strategy_signal

    with patch("run_strategy_signal.Settings") as mock_settings, \
         patch("run_strategy_signal.duckdb.connect"), \
         patch("run_strategy_signal.generate_signals", return_value=10) as mock_fn:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_strategy_signal.main()

    mock_fn.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scripts_batch.py -v -k "data_update or feature_gen or ai_analysis or strategy_signal"
```

Expected: FAIL — module not found

- [ ] **Step 3: Create `scripts/run_data_update.py`**

```python
# scripts/run_data_update.py
"""Night batch: 日次市場データ更新 (data_update_job)。

Task Scheduler から 15:30 に起動される。
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.pipeline import run_daily_etl

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        result = run_daily_etl(conn)
        if result.errors:
            logger.warning("ETL 完了（エラーあり）: %s", result.errors)
        else:
            logger.info("ETL 完了")
    except Exception:
        logger.exception("run_daily_etl が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `scripts/run_feature_gen.py`**

```python
# scripts/run_feature_gen.py
"""Night batch: 特徴量生成 (feature_generation_job)。

Task Scheduler から 16:00 に起動される。
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.strategy.feature_engineering import build_features

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        target_date = date.today()
        n = build_features(conn, target_date)
        logger.info("特徴量生成完了: %d 件 (date=%s)", n, target_date)
    except Exception:
        logger.exception("build_features が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create `scripts/run_ai_analysis.py`**

```python
# scripts/run_ai_analysis.py
"""Night batch: AI分析 — ニュースセンチメント + 市場レジーム判定 (ai_analysis_job)。

Task Scheduler から 18:00 に起動される。
score_news() と score_regime() を順次実行する。
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    target_date = date.today()
    api_key = getattr(settings, "openai_api_key", None)

    try:
        n_news = score_news(conn, target_date, api_key=api_key)
        logger.info("score_news 完了: %d 件スコア (date=%s)", n_news, target_date)
    except Exception:
        logger.exception("score_news が失敗しました")
        conn.close()
        sys.exit(1)

    try:
        n_regime = score_regime(conn, target_date, api_key=api_key)
        logger.info("score_regime 完了: %d 件 (date=%s)", n_regime, target_date)
    except Exception:
        logger.exception("score_regime が失敗しました")
        conn.close()
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Create `scripts/run_strategy_signal.py`**

```python
# scripts/run_strategy_signal.py
"""Night batch: 売買シグナル生成 (strategy_signal_job)。

Task Scheduler から 20:00 に起動される。
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.strategy.signal_generator import generate_signals

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        target_date = date.today()
        n = generate_signals(conn, target_date)
        logger.info("シグナル生成完了: %d 件 (date=%s)", n, target_date)
    except Exception:
        logger.exception("generate_signals が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Run the batch tests to verify they pass**

```bash
pytest tests/test_scripts_batch.py -v -k "data_update or feature_gen or ai_analysis or strategy_signal"
```

Expected: 5 tests PASSED

- [ ] **Step 8: Commit**

```bash
git add scripts/run_data_update.py scripts/run_feature_gen.py \
        scripts/run_ai_analysis.py scripts/run_strategy_signal.py \
        tests/test_scripts_batch.py
git commit -m "feat: add night batch scripts - data_update, feature_gen, ai_analysis, strategy_signal"
```

---

## Task 6: `scripts/run_portfolio_construction.py` — Portfolio Construction

**Files:**
- Create: `scripts/run_portfolio_construction.py`
- Modify: `tests/test_scripts_batch.py` (add portfolio tests)

This script is more complex than the others because it:
1. Reads buy signals from `signals` table
2. Calls in-memory portfolio builder functions
3. Gets latest prices and current positions from DuckDB
4. Writes to `portfolio_targets` AND `signal_queue`

**Key schemas:**
- `signals`: `(date, code, side, score, signal_rank)`
- `portfolio_targets`: `(date, code, target_weight, target_size)`
- `signal_queue`: `(signal_id, date, code, side, size, order_type, price, status, created_at, processed_at)`
- Portfolio value: `os.environ.get("PORTFOLIO_VALUE", "10000000")` (default 10M JPY)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scripts_batch.py`:

```python
# ---------- run_portfolio_construction ----------

def test_portfolio_construction_writes_signal_queue():
    import run_portfolio_construction

    mock_conn = MagicMock()
    # signals テーブルから 2件のBUYシグナルを返す
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("7203", "buy", 0.8, 1),
        ("6758", "buy", 0.6, 2),
    ]
    mock_cursor.description = [
        ("code",), ("side",), ("score",), ("signal_rank",)
    ]
    # prices_daily クエリ
    price_cursor = MagicMock()
    price_cursor.fetchall.return_value = [("7203", 2500.0), ("6758", 5000.0)]
    price_cursor.description = [("code",), ("close",)]
    # positions クエリ
    pos_cursor = MagicMock()
    pos_cursor.fetchall.return_value = []
    pos_cursor.description = [("code",), ("size",)]

    mock_conn.execute.side_effect = [
        mock_cursor,   # signals query
        price_cursor,  # prices query
        pos_cursor,    # positions query
        MagicMock(),   # DELETE portfolio_targets
        MagicMock(),   # INSERT portfolio_targets
        MagicMock(),   # DELETE signal_queue
        MagicMock(),   # INSERT signal_queue (7203)
        MagicMock(),   # INSERT signal_queue (6758)
    ]

    with patch("run_portfolio_construction.Settings") as mock_settings, \
         patch("run_portfolio_construction.duckdb.connect", return_value=mock_conn):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_portfolio_construction.main()

    # signal_queue への INSERT が呼ばれたことを確認
    insert_calls = [
        str(c) for c in mock_conn.execute.call_args_list
        if "signal_queue" in str(c) and "INSERT" in str(c)
    ]
    assert len(insert_calls) >= 1


def test_portfolio_construction_no_signals_exits_0():
    """シグナルが 0 件のとき正常終了する（signal_queue は空のまま）。"""
    import run_portfolio_construction

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = [("code",), ("side",), ("score",), ("signal_rank",)]
    mock_conn.execute.return_value = mock_cursor

    with patch("run_portfolio_construction.Settings") as mock_settings, \
         patch("run_portfolio_construction.duckdb.connect", return_value=mock_conn):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        run_portfolio_construction.main()  # SystemExit が起きないこと
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scripts_batch.py -v -k "portfolio"
```

Expected: FAIL

- [ ] **Step 3: Create `scripts/run_portfolio_construction.py`**

```python
# scripts/run_portfolio_construction.py
"""Night batch: ポートフォリオ構築 (portfolio_construction_job)。

Task Scheduler から 21:00 に起動される。
signals テーブルから当日の BUY シグナルを読み込み、
ポートフォリオ構築を行って signal_queue と portfolio_targets に書き込む。

環境変数:
    PORTFOLIO_VALUE: 総資産額（円）。デフォルト: 10,000,000
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.portfolio.portfolio_builder import calc_score_weights, select_candidates
from kabusys.portfolio.position_sizing import calc_position_sizes

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_DEFAULT_PORTFOLIO_VALUE = 10_000_000  # 1000万円
_MAX_UTILIZATION = 0.70


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    target_date = date.today()

    portfolio_value = float(
        os.environ.get("PORTFOLIO_VALUE", str(_DEFAULT_PORTFOLIO_VALUE))
    )
    available_cash = portfolio_value * _MAX_UTILIZATION

    try:
        # 1. 当日の BUY シグナルを取得
        cur = conn.execute(
            "SELECT code, side, score, signal_rank FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        )
        rows = cur.fetchall()
        buy_signals = [
            dict(zip([d[0] for d in cur.description], row)) for row in rows
        ]

        if not buy_signals:
            logger.info("本日の BUY シグナルが 0 件です。signal_queue を更新しません。")
            return

        # 2. 銘柄選定・重み計算（メモリ内）
        candidates = select_candidates(buy_signals)
        weights = calc_score_weights(candidates)

        # 3. 最新終値を取得（直近の prices_daily から）
        codes = [c["code"] for c in candidates]
        code_params = ",".join(["?"] * len(codes))
        price_cur = conn.execute(
            f"""
            SELECT p.code, p.close
            FROM prices_daily p
            INNER JOIN (
                SELECT code, MAX(date) AS max_date
                FROM prices_daily
                WHERE code IN ({code_params})
                GROUP BY code
            ) latest ON p.code = latest.code AND p.date = latest.max_date
            """,
            codes,
        )
        open_prices = {r[0]: float(r[1]) for r in price_cur.fetchall() if r[1]}

        # 4. 現在のポジション取得
        pos_cur = conn.execute(
            "SELECT code, size FROM positions WHERE code IN (" + code_params + ")",
            codes,
        )
        current_positions = {r[0]: int(r[1]) for r in pos_cur.fetchall()}

        # 5. ポジションサイズ計算
        sizes = calc_position_sizes(
            weights=weights,
            candidates=candidates,
            portfolio_value=portfolio_value,
            available_cash=available_cash,
            current_positions=current_positions,
            open_prices=open_prices,
        )

        # 6. portfolio_targets を更新
        conn.execute(
            "DELETE FROM portfolio_targets WHERE date = ?", [target_date]
        )
        for code, weight in weights.items():
            size = sizes.get(code, 0)
            conn.execute(
                "INSERT INTO portfolio_targets (date, code, target_weight, target_size) VALUES (?,?,?,?)",
                [target_date, code, weight, size],
            )

        # 7. signal_queue を更新（当日の pending シグナルをクリアして再挿入）
        conn.execute(
            "DELETE FROM signal_queue WHERE date = ? AND status = 'pending'",
            [target_date],
        )
        inserted = 0
        for code, shares in sizes.items():
            if shares <= 0:
                continue
            price = open_prices.get(code)
            conn.execute(
                """INSERT INTO signal_queue
                   (signal_id, date, code, side, size, order_type, price, status)
                   VALUES (?, ?, ?, 'buy', ?, 'market', ?, 'pending')""",
                [str(uuid.uuid4()), target_date, code, shares, price],
            )
            inserted += 1

        logger.info(
            "ポートフォリオ構築完了: %d 銘柄を signal_queue に挿入 (date=%s)",
            inserted,
            target_date,
        )

    except Exception:
        logger.exception("ポートフォリオ構築が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run portfolio tests to verify they pass**

```bash
pytest tests/test_scripts_batch.py -v -k "portfolio"
```

Expected: 2 tests PASSED

- [ ] **Step 5: Run all batch tests**

```bash
pytest tests/test_scripts_batch.py -v
```

Expected: ALL PASSED

- [ ] **Step 6: Commit**

```bash
git add scripts/run_portfolio_construction.py tests/test_scripts_batch.py
git commit -m "feat: add scripts/run_portfolio_construction.py - night batch portfolio construction"
```

---

## Task 7: `reset_signals.py` and `rebuild_features.py` — Maintenance Scripts

**Files:**
- Create: `scripts/reset_signals.py`
- Create: `scripts/rebuild_features.py`
- Create: `tests/test_scripts_maintenance.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scripts_maintenance.py
"""reset_signals.py / rebuild_features.py の単体テスト"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


# ---------- reset_signals ----------

def test_reset_signals_clears_rows():
    import reset_signals

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3
    mock_conn.execute.return_value = mock_cursor

    with patch("reset_signals.Settings") as mock_settings, \
         patch("reset_signals.duckdb.connect", return_value=mock_conn):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        reset_signals.main()

    delete_calls = [c for c in mock_conn.execute.call_args_list if "DELETE" in str(c)]
    assert len(delete_calls) == 1


def test_reset_signals_empty_table_is_ok():
    import reset_signals

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 0
    mock_conn.execute.return_value = mock_cursor

    with patch("reset_signals.Settings") as mock_settings, \
         patch("reset_signals.duckdb.connect", return_value=mock_conn):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        reset_signals.main()  # SystemExit が起きないこと


# ---------- rebuild_features ----------

def test_rebuild_features_no_data_exits_1():
    import rebuild_features

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_conn.execute.return_value = mock_cursor

    with patch("rebuild_features.Settings") as mock_settings, \
         patch("rebuild_features.duckdb.connect", return_value=mock_conn), \
         patch("rebuild_features.build_features") as mock_fn:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        with pytest.raises(SystemExit) as exc:
            rebuild_features.main()
        assert exc.value.code == 1

    mock_fn.assert_not_called()


def test_rebuild_features_with_data_calls_build_features():
    import rebuild_features

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (5,)
    mock_conn.execute.return_value = mock_cursor

    with patch("rebuild_features.Settings") as mock_settings, \
         patch("rebuild_features.duckdb.connect", return_value=mock_conn), \
         patch("rebuild_features.build_features", return_value=5) as mock_fn:
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        rebuild_features.main()

    mock_fn.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scripts_maintenance.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Create `scripts/reset_signals.py`**

```python
# scripts/reset_signals.py
"""signal_queue テーブルをクリアするメンテナンススクリプト。

未処理のシグナルをすべて削除する。
使い方: python scripts/reset_signals.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        cursor = conn.execute("DELETE FROM signal_queue")
        n = cursor.rowcount
        logger.info("signal_queue をクリアしました（%d 件削除）", n)
    except Exception:
        logger.exception("signal_queue のクリアに失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `scripts/rebuild_features.py`**

```python
# scripts/rebuild_features.py
"""特徴量を手動で再計算するメンテナンススクリプト。

prices_daily に当日データが存在することを確認してから build_features() を実行する。
使い方: python scripts/rebuild_features.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.strategy.feature_engineering import build_features

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    target_date = date.today()

    try:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM prices_daily WHERE date = ?", [target_date]
        )
        count = cursor.fetchone()[0]
        if count == 0:
            logger.error(
                "本日 (%s) の prices_daily データが存在しません。"
                "先に run_data_update.py を実行してください。",
                target_date,
            )
            sys.exit(1)

        n = build_features(conn, target_date)
        logger.info("特徴量再計算完了: %d 件 (date=%s)", n, target_date)

    except SystemExit:
        raise
    except Exception:
        logger.exception("rebuild_features が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run maintenance tests to verify they pass**

```bash
pytest tests/test_scripts_maintenance.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 6: Run all tests**

```bash
pytest tests/ -v --tb=short -q
```

Expected: ALL PASSED (no regressions)

- [ ] **Step 7: Commit**

```bash
git add scripts/reset_signals.py scripts/rebuild_features.py \
        tests/test_scripts_maintenance.py
git commit -m "feat: add reset_signals.py and rebuild_features.py - maintenance scripts"
```

---

## Task 8: `setup_task_scheduler.ps1` — Windows Task Scheduler Registration

**Files:**
- Create: `scripts/setup_task_scheduler.ps1`

PowerShell scripts cannot be unit-tested with pytest. Manual verification steps are provided.

- [ ] **Step 1: Create `scripts/setup_task_scheduler.ps1`**

```powershell
# scripts/setup_task_scheduler.ps1
# KabuSys Windows Task Scheduler 登録スクリプト
#
# 使い方:
#   powershell -File scripts\setup_task_scheduler.ps1
#   powershell -File scripts\setup_task_scheduler.ps1 -PythonPath C:\path\to\python.exe
#
# 既存のジョブは -Force で上書き登録される。

param(
    [string]$PythonPath = "python",
    [string]$WorkDir = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

Write-Host "KabuSys Task Scheduler 登録開始"
Write-Host "  WorkDir   : $WorkDir"
Write-Host "  PythonPath: $PythonPath"

function Register-KabuSysTask {
    param(
        [string]$TaskName,
        [string]$Script,
        [string]$Arguments = "",
        [string]$TriggerTime
    )

    $action = if ($Arguments) {
        New-ScheduledTaskAction -Execute $PythonPath `
            -Argument "scripts\$Script $Arguments" `
            -WorkingDirectory $WorkDir
    } else {
        New-ScheduledTaskAction -Execute $PythonPath `
            -Argument "scripts\$Script" `
            -WorkingDirectory $WorkDir
    }

    $trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -StartWhenAvailable

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Force | Out-Null

    Write-Host "  登録完了: $TaskName ($TriggerTime)"
}

# Night batch jobs
Register-KabuSysTask -TaskName "KabuSys_DataUpdate"            -Script "run_data_update.py"            -TriggerTime "15:30"
Register-KabuSysTask -TaskName "KabuSys_FeatureGen"            -Script "run_feature_gen.py"            -TriggerTime "16:00"
Register-KabuSysTask -TaskName "KabuSys_AiAnalysis"            -Script "run_ai_analysis.py"            -TriggerTime "18:00"
Register-KabuSysTask -TaskName "KabuSys_StrategySignal"        -Script "run_strategy_signal.py"        -TriggerTime "20:00"
Register-KabuSysTask -TaskName "KabuSys_PortfolioConstruction" -Script "run_portfolio_construction.py" -TriggerTime "21:00"

# System start jobs
Register-KabuSysTask -TaskName "KabuSys_ExecutionStart"  -Script "start_system.py" -Arguments "--component execution"  -TriggerTime "08:30"
Register-KabuSysTask -TaskName "KabuSys_MonitoringStart" -Script "start_system.py" -Arguments "--component monitoring" -TriggerTime "09:00"

Write-Host ""
Write-Host "7 件のジョブ登録が完了しました。"
Write-Host "確認: Get-ScheduledTask -TaskName 'KabuSys_*' | Select-Object TaskName, State"
```

- [ ] **Step 2: Verify PowerShell syntax (dry run — no actual registration)**

```powershell
powershell -NoProfile -Command "& { Get-Content scripts\setup_task_scheduler.ps1 | Out-Null; Write-Host 'Syntax OK' }"
```

Expected: `Syntax OK`

- [ ] **Step 3: Run all Python tests as final regression check**

```bash
pytest tests/ -v --tb=short -q
```

Expected: ALL PASSED

- [ ] **Step 4: Commit**

```bash
git add scripts/setup_task_scheduler.ps1
git commit -m "feat: add setup_task_scheduler.ps1 - register 7 Windows Task Scheduler jobs"
```

---

## Final Verification

- [ ] **Verify all scripts are present**

```bash
ls scripts/
```

Expected output includes:
```
rebuild_features.py
reset_signals.py
run_ai_analysis.py
run_data_update.py
run_feature_gen.py
run_portfolio_construction.py
run_strategy_signal.py
setup_task_scheduler.ps1
start_system.py
stop_system.py
utils.py
```

- [ ] **Run full test suite**

```bash
pytest tests/ -q --tb=short
```

Expected: ALL PASSED

- [ ] **Verify `run_execution.py` and `run_monitoring.py` pass existing tests**

```bash
pytest tests/test_run_execution.py tests/test_run_monitoring.py -v
```

Expected: ALL PASSED
