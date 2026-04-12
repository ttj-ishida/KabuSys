# Phase 9: Deployment Scripts Design Spec

**Issues:** #45 (Windows Task Scheduler Setup), #46 (System Start/Stop/Rebuild/Reset Scripts)

## Overview

This spec covers the implementation of operational scripts for KabuSys deployment on a single Windows node. The scripts fall into two categories:

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
├── start_system.py                   # Launch execution + monitoring processes
├── stop_system.py                    # Graceful stop → force kill (10s timeout)
├── rebuild_features.py               # Re-run feature generation (with prerequisite check)
├── reset_signals.py                  # Clear signal_queue table
├── run_data_update.py                # Night batch: market data ingestion
├── run_feature_gen.py                # Night batch: feature generation
├── run_ai_analysis.py                # Night batch: AI/NLP scoring
├── run_strategy_signal.py            # Night batch: strategy signal generation
├── run_portfolio_construction.py     # Night batch: portfolio construction
└── setup_task_scheduler.ps1         # Register 7 Windows Task Scheduler jobs
```

**Modified files:**
- `src/kabusys/run_execution.py` — add stop flag check in main loop
- `src/kabusys/run_monitoring.py` — add stop flag check in main loop

---

## Architecture

### Stop Flag Pattern

Graceful shutdown is coordinated via a sentinel file (`data/stop_requested.flag`):

- `stop_system.py` creates the flag file to signal processes to stop
- `run_execution.py` and `run_monitoring.py` check `utils.stop_requested()` in their main loops and exit cleanly
- If processes do not exit within 10 seconds, `psutil.Process.kill()` forcefully terminates them
- `start_system.py` clears the flag file before launching processes

### PID Files

| Process | PID File |
|---|---|
| ExecutionEngine | `data/execution.pid` (existing `Settings.pid_file_path`) |
| MonitoringEngine | `data/monitoring.pid` (new) |

### Exit Codes

All scripts use `sys.exit(0)` for success and `sys.exit(1)` for failure. This allows Windows Task Scheduler to detect and log failures.

---

## Component Details

### `scripts/utils.py`

Shared utility functions used by system control scripts:

```python
def read_pid(path: str) -> int | None
    """Read PID from file. Returns None if file missing or invalid."""

def write_pid(path: str, pid: int) -> None
    """Write PID to file."""

def delete_pid(path: str) -> None
    """Delete PID file if it exists."""

def is_process_running(pid: int) -> bool
    """Return True if process with given PID is alive."""

def request_stop(flag_path: str) -> None
    """Create stop flag file."""

def stop_requested(flag_path: str) -> bool
    """Return True if stop flag file exists."""

def clear_stop_flag(flag_path: str) -> None
    """Delete stop flag file if it exists."""
```

Constants:
```python
EXECUTION_PID_PATH = "data/execution.pid"
MONITORING_PID_PATH = "data/monitoring.pid"
STOP_FLAG_PATH = "data/stop_requested.flag"
```

### `scripts/start_system.py`

1. Check if stop flag exists → clear it
2. Check `data/execution.pid` and `data/monitoring.pid`:
   - If PID file exists AND process is alive → log warning "Already running" → `sys.exit(1)`
3. Launch `src/kabusys/run_execution.py` via `subprocess.Popen([sys.executable, "src/kabusys/run_execution.py"])`
4. Launch `src/kabusys/run_monitoring.py` via `subprocess.Popen([sys.executable, "src/kabusys/run_monitoring.py"])`
5. Write PIDs to respective PID files
6. Log "System started (execution PID=X, monitoring PID=Y)"

### `scripts/stop_system.py`

1. Create stop flag file (`data/stop_requested.flag`)
2. Read PIDs from `data/execution.pid` and `data/monitoring.pid`
3. For each PID (if found and process running):
   - Wait up to 10 seconds for graceful exit (poll every 0.5s)
   - If still running after timeout → `psutil.Process(pid).kill()`
   - Log whether graceful or forced
4. Delete PID files and stop flag

### `scripts/rebuild_features.py`

1. Connect to DuckDB (path from `Settings.duckdb_path`)
2. Query: `SELECT COUNT(*) FROM market_data WHERE date = CURRENT_DATE`
3. If count == 0 → log error "本日の market_data が存在しません。先に run_data_update.py を実行してください。" → `sys.exit(1)`
4. Call feature generation function (import from `kabusys.features`)
5. Log completion and row count

### `scripts/reset_signals.py`

1. Connect to DuckDB (path from `Settings.duckdb_path`)
2. Execute `DELETE FROM signal_queue`
3. Log "signal_queue をクリアしました（{n}件削除）"

### Night Batch Scripts (5 files)

Each script follows the same pattern:
1. Configure logging
2. Load settings
3. Call the corresponding domain function
4. Log success/failure
5. `sys.exit(0)` or `sys.exit(1)`

| Script | Function to call |
|---|---|
| `run_data_update.py` | `kabusys.data.update_market_data()` |
| `run_feature_gen.py` | `kabusys.features.generate_features()` |
| `run_ai_analysis.py` | `kabusys.ai.run_analysis()` |
| `run_strategy_signal.py` | `kabusys.strategy.generate_signals()` |
| `run_portfolio_construction.py` | `kabusys.portfolio.construct_portfolio()` |

> **Note:** These function signatures will be confirmed at implementation time by reading the actual source. The scripts are thin wrappers; if the target function does not yet exist, a `NotImplementedError` stub will be added.

### `setup_task_scheduler.ps1`

Parameters block at top:
```powershell
param(
    [string]$PythonPath = "python",
    [string]$WorkDir = (Get-Location).Path
)
```

Registers 7 jobs using `Register-ScheduledTask -Force`:

| Task Name | Script | Schedule |
|---|---|---|
| `KabuSys_DataUpdate` | `run_data_update.py` | Daily 15:30 |
| `KabuSys_FeatureGen` | `run_feature_gen.py` | Daily 16:00 |
| `KabuSys_AiAnalysis` | `run_ai_analysis.py` | Daily 18:00 |
| `KabuSys_StrategySignal` | `run_strategy_signal.py` | Daily 20:00 |
| `KabuSys_PortfolioConstruction` | `run_portfolio_construction.py` | Daily 21:00 |
| `KabuSys_ExecutionStart` | `start_system.py` (execution only) | Daily 08:30 |
| `KabuSys_MonitoringStart` | `start_system.py` (monitoring only) | Daily 09:00 |

> **Note on ExecutionStart/MonitoringStart:** `start_system.py` launches both processes. For Task Scheduler, execution and monitoring are registered as separate tasks that both call `start_system.py`. Alternatively, `start_system.py` can accept `--component execution|monitoring|all` flag. This will be finalized at implementation time.

Each task:
- Run As: current user (no SYSTEM account required for paper trading phase)
- Working directory: `$WorkDir`
- Action: `$PythonPath scripts\<script>.py`
- Trigger: Daily at specified time
- Settings: `ExecutionTimeLimit = PT1H` (1 hour max)

### Modifications to `run_execution.py` and `run_monitoring.py`

Add to the main loop body:

```python
from scripts.utils import stop_requested, STOP_FLAG_PATH

# Inside main loop:
if stop_requested(STOP_FLAG_PATH):
    logger.info("停止フラグを検知しました。グレースフルシャットダウンを開始します。")
    break
```

> Import path will be adjusted based on how `scripts/utils.py` is made importable (e.g., adding `scripts/` to `sys.path` or using a relative path).

---

## Error Handling

| Situation | Behavior |
|---|---|
| `psutil` not installed | `ImportError` with clear message "pip install psutil が必要です" |
| Process already running on start | Warning log + `sys.exit(1)` |
| PID file missing on stop | Log "プロセスが見つかりません" + continue |
| DuckDB path missing | Settings validation error (existing behavior) |
| Night batch function raises | Log exception + `sys.exit(1)` |

All scripts use `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")`.

---

## Testing

### `tests/unit/test_scripts_utils.py`
- `test_read_pid_missing_file` — returns None
- `test_read_pid_invalid_content` — returns None
- `test_write_and_read_pid` — roundtrip
- `test_is_process_running_current` — current PID is running
- `test_is_process_running_invalid` — PID 99999999 not running
- `test_stop_flag_lifecycle` — create, check, clear

### `tests/unit/test_reset_signals.py`
- `test_reset_signals_clears_queue` — insert rows, run script logic, verify 0 rows remain
- `test_reset_signals_empty_queue` — no error on empty table

### `tests/unit/test_rebuild_features.py`
- `test_rebuild_no_data_exits_1` — mock DuckDB returns 0 rows → exit code 1
- `test_rebuild_with_data_calls_function` — mock DuckDB returns >0 rows → feature function called

### `tests/unit/test_start_stop_system.py`
- `test_start_clears_stop_flag` — stop flag exists before start → cleared
- `test_start_already_running` — PID file + mock running process → exit 1
- `test_stop_graceful` — process exits within timeout → no kill called
- `test_stop_force_kill` — process does not exit → kill called after timeout

---

## Dependencies

- `psutil` — process management (add to `requirements.txt`)
- Python standard library: `subprocess`, `pathlib`, `logging`, `sys`, `time`
- `duckdb` — already in requirements
- `sqlite3` — standard library

---

## Out of Scope

- Automated restart on crash (watchdog) — separate issue
- Log rotation for script output — handled by Windows Task Scheduler history
- Remote monitoring/alerting for batch failures — Phase 10
