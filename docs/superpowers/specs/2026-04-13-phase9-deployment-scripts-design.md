# Phase 9: Deployment Scripts Design Spec

**Issues:** #45 (Windows Task Scheduler Setup), #46 (System Start/Stop/Rebuild/Reset Scripts)

## Overview

This spec covers the implementation of operational scripts for KabuSys deployment on a single Windows node. The scripts fall into four categories:

1. **System control scripts** (`start_system.py`, `stop_system.py`, `rebuild_features.py`, `reset_signals.py`)
2. **Night batch entry points** (`run_data_update.py`, `run_feature_gen.py`, `run_ai_analysis.py`, `run_strategy_signal.py`, `run_portfolio_construction.py`)
3. **Task Scheduler registration** (`setup_task_scheduler.ps1`)
4. **Shared utilities** (`scripts/utils.py`)

All scripts live in `scripts/` as flat files, consistent with the existing `src/kabusys/run_execution.py` and `src/kabusys/run_monitoring.py` style.

---

## File Structure

```
scripts/
├── utils.py                          # Shared: PID file, stop flag, process check
├── start_system.py                   # Launch execution and/or monitoring processes
├── stop_system.py                    # Graceful stop → force kill (10s timeout)
├── rebuild_features.py               # Re-run feature generation (with prerequisite check)
├── reset_signals.py                  # Clear signal_queue table
├── run_data_update.py                # Night batch: market data ingestion
├── run_feature_gen.py                # Night batch: feature generation
├── run_ai_analysis.py                # Night batch: AI/NLP scoring (news + regime)
├── run_strategy_signal.py            # Night batch: strategy signal generation
├── run_portfolio_construction.py     # Night batch: portfolio construction
└── setup_task_scheduler.ps1         # Register 7 Windows Task Scheduler jobs
```

**Modified files:**
- `src/kabusys/run_execution.py` — wrap `engine.run_session()` in thread; main thread polls stop flag
- `src/kabusys/run_monitoring.py` — add stop flag check in `while True:` loop

---

## Architecture

### Stop Flag Pattern

Graceful shutdown is coordinated via a sentinel file. The stop flag path is a project-wide convention:

```
data/stop_requested.flag
```

**Key rule:** The stop flag is owned by `stop_system.py` (creates it) and cleared by `start_system.py` (on next startup). `stop_system.py` does NOT delete the flag — it leaves it for `start_system.py` to clear before the next launch.

Shutdown sequence in `stop_system.py`:
1. Create `data/stop_requested.flag`
2. Wait up to 10 seconds for each process to exit (poll every 0.5s)
3. If still running after timeout → `psutil.Process(pid).kill()`
4. Verify both processes are dead
5. Delete PID files (NOT the stop flag)

### Stop Flag in `run_execution.py`

`run_execution.py` calls `engine.run_session()`, which is a blocking call with an internal `threading.Event`-based loop. To support graceful stop without modifying `ExecutionEngine`:

Modify `run_execution.py` as follows:
- Run `engine.run_session()` in a daemon `threading.Thread`
- The main thread polls `_stop_flag_exists()` every 1 second in a loop
- When the flag is detected, call `engine.stop()` to set `_stop_event` inside the engine
- Join the thread (with timeout) to wait for clean exit

```python
import threading
from pathlib import Path

_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"

def _stop_flag_exists() -> bool:
    return _STOP_FLAG.exists()

# In main():
thread = threading.Thread(target=engine.run_session, daemon=True)
thread.start()
while thread.is_alive():
    if _stop_flag_exists():
        logger.info("停止フラグを検知。エンジンを停止します。")
        engine.stop()
        break
    thread.join(timeout=1.0)
thread.join(timeout=30.0)
```

### Stop Flag in `run_monitoring.py`

`run_monitoring.py` has a `while True:` loop with `time.sleep(poll_interval)`. Modify by adding a stop flag check at the top of the loop body:

```python
from pathlib import Path

_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"

# Inside while True:
while True:
    if _STOP_FLAG.exists():
        logger.info("停止フラグを検知。監視ループを終了します。")
        break
    try:
        monitor.check_once()
    except Exception:
        ...
    time.sleep(poll_interval)
```

**Import note:** `_STOP_FLAG` is defined locally in each file using `Path(__file__).resolve()` — no import from `scripts/utils.py` is needed. This avoids `ModuleNotFoundError` since `scripts/` is not on `PYTHONPATH`.

### `start_system.py` `--component` Flag

`start_system.py` accepts an optional `--component` argument:

```
python scripts/start_system.py --component execution   # launch execution only
python scripts/start_system.py --component monitoring  # launch monitoring only
python scripts/start_system.py                         # launch both (default)
python scripts/start_system.py --component all         # explicit both
```

This is required because Task Scheduler registers execution (08:30) and monitoring (09:00) as separate jobs with different start times.

### PID Files

| Process | PID File |
|---|---|
| ExecutionEngine | `data/execution.pid` (matches `Settings.pid_file_path`) |
| MonitoringEngine | `data/monitoring.pid` (new) |

### Absolute Paths

All file paths in `scripts/utils.py` and individual scripts use paths anchored to the project root via `Path(__file__).resolve()`:

```python
# In scripts/utils.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXECUTION_PID_PATH = _PROJECT_ROOT / "data" / "execution.pid"
MONITORING_PID_PATH = _PROJECT_ROOT / "data" / "monitoring.pid"
STOP_FLAG_PATH = _PROJECT_ROOT / "data" / "stop_requested.flag"
```

This ensures scripts work correctly regardless of the working directory set by Task Scheduler.

### Exit Codes

All scripts use `sys.exit(0)` for success and `sys.exit(1)` for failure. This allows Windows Task Scheduler to detect and log failures.

---

## Component Details

### `scripts/utils.py`

```python
from pathlib import Path
import psutil  # pip install psutil required

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXECUTION_PID_PATH = _PROJECT_ROOT / "data" / "execution.pid"
MONITORING_PID_PATH = _PROJECT_ROOT / "data" / "monitoring.pid"
STOP_FLAG_PATH = _PROJECT_ROOT / "data" / "stop_requested.flag"


def read_pid(path: Path) -> int | None:
    """Read PID from file. Returns None if file missing or content invalid."""

def write_pid(path: Path, pid: int) -> None:
    """Write PID to file. Creates parent directories if needed."""
    # path.parent.mkdir(parents=True, exist_ok=True)

def delete_pid(path: Path) -> None:
    """Delete PID file if it exists."""

def is_process_running(pid: int) -> bool:
    """Return True if a process with the given PID exists and is alive."""
    # Uses psutil.pid_exists(pid) and checks process status

def request_stop() -> None:
    """Create stop flag file. Creates parent directories if needed."""

def stop_requested() -> bool:
    """Return True if stop flag file exists."""

def clear_stop_flag() -> None:
    """Delete stop flag file if it exists."""
```

**`psutil` import:** If `psutil` is not installed, the module raises `ImportError`. This is caught at the top of the module and handled with `print("ERROR: psutil が必要です。pip install psutil を実行してください。")` followed by `sys.exit(1)`, since logging is not yet configured at import time.

### `scripts/start_system.py`

1. Parse `--component` argument (`execution`, `monitoring`, `all`; default: `all`)
2. Clear stop flag if it exists (`utils.clear_stop_flag()`)
3. For each component to start:
   - Check PID file: if PID exists AND process is running → log warning "既に起動中です" → `sys.exit(1)`
   - Launch script via `subprocess.Popen([sys.executable, str(SCRIPT_PATH)])` where `SCRIPT_PATH = Path(__file__).resolve().parent.parent / "src" / "kabusys" / "run_execution.py"` (absolute path)
   - Write PID to PID file
4. Log "システム起動完了 (execution PID=X)" etc.

### `scripts/stop_system.py`

1. Create stop flag (`utils.request_stop()`)
2. For each PID file (`execution.pid`, `monitoring.pid`):
   - Read PID; if PID file is missing → log "PID ファイルが見つかりません。スキップします。" and continue (this is the normal case when only one component was started, e.g., `start_system.py --component execution` was used and `monitoring.pid` does not exist)
   - If PID found and process running: wait up to 10 seconds (poll every 0.5s) for graceful exit
   - If still running after timeout: `psutil.Process(pid).kill()` and log "強制終了しました"
   - Log "グレースフル終了" or "強制終了"
3. After both PID files processed (regardless of whether files were found): delete any PID files that exist
4. Do NOT delete stop flag (cleared by `start_system.py` on next startup)

### `scripts/rebuild_features.py`

1. Connect to DuckDB (`Settings.duckdb_path`)
2. Query: `SELECT COUNT(*) FROM prices_daily WHERE date = CURRENT_DATE`
3. If count == 0 → log error "本日の prices_daily データが存在しません。先に run_data_update.py を実行してください。" → `sys.exit(1)`
4. Call `build_features(conn, target_date=date.today())` from `kabusys.strategy.feature_engineering`
5. Log completion

### `scripts/reset_signals.py`

1. Connect to DuckDB (`Settings.duckdb_path`)
2. Execute `DELETE FROM signal_queue`
3. Log "signal_queue をクリアしました（{n}件削除）"

**Scope note:** `portfolio_targets` is intentionally NOT cleared. It represents the strategy's desired portfolio state and is managed by the portfolio construction job. Clearing it independently of a portfolio reconstruction run would leave the system in an inconsistent state.

### Night Batch Scripts

Each script configures logging, loads settings, connects to DuckDB, calls the domain function, and exits with code 0 or 1.

| Script | Module | Function call |
|---|---|---|
| `run_data_update.py` | `kabusys.data.pipeline` | `run_daily_etl(conn, target_date)` |
| `run_feature_gen.py` | `kabusys.strategy.feature_engineering` | `build_features(conn, target_date)` |
| `run_ai_analysis.py` | `kabusys.ai.news_nlp`, `kabusys.ai.regime_detector` | `score_news(conn, target_date)` then `score_regime(conn, target_date)` |
| `run_strategy_signal.py` | `kabusys.strategy.signal_generator` | `generate_signals(conn, target_date)` |
| `run_portfolio_construction.py` | `kabusys.portfolio.portfolio_builder` | fetch signals from DuckDB → `select_candidates(buy_signals)` → `calc_score_weights(candidates)` |

> **Implementation note:** Exact function signatures must be verified by reading the source at implementation time. If a function does not accept `target_date` as a parameter, use `date.today()` directly inside the script. If the function does not yet exist as a single callable, create a thin wrapper function in the respective module.

**`run_portfolio_construction.py` detail:** `select_candidates` and `calc_score_weights` operate in-memory on Python lists; they do NOT accept a DuckDB connection. The script must first query DuckDB to retrieve today's buy signals, then pass them as a `list[dict]` to these functions:
```python
from kabusys.portfolio.portfolio_builder import select_candidates, calc_score_weights

# 1. Fetch signals from DuckDB
rows = conn.execute("SELECT * FROM signal_queue WHERE date = CURRENT_DATE AND side = 'buy'").fetchall()
buy_signals = [dict(zip([d[0] for d in conn.description], row)) for row in rows]

# 2. Portfolio construction (in-memory)
candidates = select_candidates(buy_signals)
weights = calc_score_weights(candidates)
```

**`run_ai_analysis.py` detail:** Must call both AI functions sequentially:
```python
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

target_date = date.today()
score_news(conn, target_date)
score_regime(conn, target_date)
```

### `setup_task_scheduler.ps1`

Parameters block at top:
```powershell
param(
    [string]$PythonPath = "python",
    [string]$WorkDir = (Resolve-Path "$PSScriptRoot\..").Path
)
```

`$PSScriptRoot` resolves to the `scripts/` directory (where the `.ps1` file lives), so `"$PSScriptRoot\.."` resolves to the project root. This is safe whether the script is run from Task Scheduler or the command line. If the operator needs to override the project root, they pass `-WorkDir C:\path\to\KabuSys`.

Registers exactly 7 jobs (matching `documents/10_Runtime/RuntimeJobSchedule.md` section 7) using `Register-ScheduledTask -Force`:

| Task Name | Script | Arguments | Schedule |
|---|---|---|---|
| `KabuSys_DataUpdate` | `run_data_update.py` | — | Daily 15:30 |
| `KabuSys_FeatureGen` | `run_feature_gen.py` | — | Daily 16:00 |
| `KabuSys_AiAnalysis` | `run_ai_analysis.py` | — | Daily 18:00 |
| `KabuSys_StrategySignal` | `run_strategy_signal.py` | — | Daily 20:00 |
| `KabuSys_PortfolioConstruction` | `run_portfolio_construction.py` | — | Daily 21:00 |
| `KabuSys_ExecutionStart` | `start_system.py` | `--component execution` | Daily 08:30 |
| `KabuSys_MonitoringStart` | `start_system.py` | `--component monitoring` | Daily 09:00 |

**Out of scope:** The `market_close_job` mentioned in `documents/10_Runtime/RuntimeJobSchedule.md` section 6 is a conceptual job for position/performance updates and is not part of this issue's Task Scheduler registration.

Each task settings:
- Run As: current user (no SYSTEM account; paper trading phase does not require elevated permissions)
- Working directory: `$WorkDir`
- Action: `$PythonPath scripts\<script>.py [args]`
- Trigger: Daily at specified time
- `ExecutionTimeLimit = PT1H` (1 hour maximum)

### Modifications to `run_execution.py`

Add thread-based stop flag polling to `main()`:

```python
import threading
from pathlib import Path

_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"

# After creating engine, replace:
#   engine.run_session()
# With:
thread = threading.Thread(target=engine.run_session, daemon=True)
thread.start()
while thread.is_alive():
    if _STOP_FLAG.exists():
        logger.info("停止フラグを検知。エンジンを停止します。")
        engine.stop()
        break
    thread.join(timeout=1.0)
# thread.join(timeout=1.0) exits when: (a) stop flag triggered and engine.stop() called,
# OR (b) engine.run_session() finished naturally (e.g., market session ended at 15:30).
# Both cases are handled correctly — no additional logic needed.
thread.join(timeout=30.0)
```

### Modifications to `run_monitoring.py`

Add stop flag check inside `while True:`:

```python
from pathlib import Path

_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"

# Change while loop:
while True:
    if _STOP_FLAG.exists():
        logger.info("停止フラグを検知。監視ループを終了します。")
        break
    try:
        monitor.check_once()
    except Exception:
        logger.exception("check_once() で予期しないエラー。次のポーリングまで待機。")
    time.sleep(poll_interval)
```

---

## Error Handling

| Situation | Behavior |
|---|---|
| `psutil` not installed | `print("ERROR: pip install psutil ...") + sys.exit(1)` at import time |
| Process already running on start | Warning log + `sys.exit(1)` |
| PID file missing on stop | Log "PID ファイルが見つかりません。スキップします。" + continue |
| `prices_daily` has no data in rebuild | Error log + `sys.exit(1)` |
| `data/` directory missing | `utils.write_pid()` creates it via `path.parent.mkdir(parents=True, exist_ok=True)` |
| Night batch function raises | Log exception + `sys.exit(1)` |

All scripts use `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")`.

---

## Testing

### `tests/unit/test_scripts_utils.py`

Uses `tmp_path` fixture for all file I/O.

- `test_read_pid_missing_file` — returns `None`
- `test_read_pid_invalid_content` — non-integer content returns `None`
- `test_write_and_read_pid_roundtrip` — write then read returns same int
- `test_write_pid_creates_parent_dirs` — nested path created automatically
- `test_is_process_running_current_process` — `os.getpid()` returns `True`
- `test_is_process_running_invalid_pid` — PID 9999999 returns `False`
- `test_stop_flag_lifecycle` — `request_stop()` → `stop_requested()` is True → `clear_stop_flag()` → False

### `tests/unit/test_reset_signals.py`

Uses in-memory DuckDB.

- `test_reset_signals_clears_rows` — insert 3 rows, run reset logic, verify 0 rows remain
- `test_reset_signals_empty_table` — no error when table is already empty, returns count 0

### `tests/unit/test_rebuild_features.py`

Uses `unittest.mock.patch` for DuckDB connection.

- `test_no_data_exits_with_code_1` — mock returns count=0 → function raises `SystemExit(1)`
- `test_with_data_calls_build_features` — mock returns count=5 → `build_features` called once

### `tests/unit/test_start_stop_system.py`

Uses `unittest.mock.patch` for `subprocess.Popen` and `psutil`.

- `test_start_clears_existing_stop_flag` — stop flag present → cleared before launch
- `test_start_already_running_exits_1` — PID file exists + mock process alive → `SystemExit(1)`
- `test_start_component_execution_only` — `--component execution` → only execution script launched
- `test_stop_graceful_exit` — mock process exits within timeout → kill NOT called, PID files deleted
- `test_stop_force_kill_on_timeout` — mock process does not exit → `kill()` called after 10s
- `test_stop_partial_failure` — execution exits gracefully, monitoring requires force kill → both handled independently

---

## Dependencies

- `psutil` — add to `requirements.txt` (process management)
- Python standard library: `subprocess`, `pathlib`, `logging`, `sys`, `time`, `threading`, `argparse`
- `duckdb` — already in requirements
- Existing `kabusys.*` modules (imports verified at implementation time)

---

## Out of Scope

- `market_close_job` (position update at 15:30) — separate issue
- Automated restart on crash (watchdog) — separate issue
- Log rotation for script output — handled by Windows Task Scheduler history
- Remote monitoring/alerting for batch failures — Phase 10
