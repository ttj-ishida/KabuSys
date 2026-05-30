#!/usr/bin/env python3
# scripts/run_scheduler.py
"""KabuSys スケジューラーデーモン。

単一 Python プロセスがジョブスケジュールを管理する。
Task Scheduler には「ログオン時にこのスクリプトを起動」の1エントリを登録するだけでよい。

解決する問題:
  run_execution が DuckDB 接続を保持しているため夜間バッチが DB ロックで失敗する。
  本デーモンは exclusive_db ジョブの実行前に run_execution を自動停止し、
  取引時間内なら完了後に再起動する。

取引カレンダー:
  市場が休みの日（土日・祝日・年末年始）はすべてのジョブをスキップする。
  判定は market_calendar テーブルを read-only で参照し、取得不能時は土日チェックにフォールバック。

使用方法:
  python scripts/run_scheduler.py          # デーモンモード（常駐）
  python scripts/run_scheduler.py --once   # 1 回チェックして終了（動作確認用）
  python scripts/run_scheduler.py --list   # 現在のスケジュールを表示して終了

Task Scheduler 登録例:
  - トリガー: ログオン時
  - アクション: python scripts\\run_scheduler.py
  - 作業フォルダー: <KabuSys ルート>
  - ログ: logs\\scheduler.log に自動追記

ログ:
  スケジューラー本体  → logs/scheduler.log
  各ジョブの stdout/stderr → logs/<job_name>.log

再起動耐性:
  実行済みジョブは data/scheduler_ran_today.json に日付付きで保存される。
  デーモンが再起動しても当日分のジョブは重複実行されない。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from datetime import time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from utils import (
    EXECUTION_PID_PATH,
    STOP_FLAG_PATH,
    is_process_running,
    read_pid,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
_PYTHON = sys.executable

_LOG_FILE = _PROJECT_ROOT / "logs" / "scheduler.log"
_RAN_TODAY_FILE = _PROJECT_ROOT / "data" / "scheduler_ran_today.json"

# 取引時間帯: この範囲内に exclusive_db ジョブが完了した場合のみ execution を再起動する
_EXECUTION_START_TIME = dtime(8, 30)
_MARKET_CLOSE_TIME = dtime(15, 35)

_STOP_WAIT_SEC = 20   # execution 停止の追加待機上限（stop_system.py の後）
_POLL_INTERVAL_SEC = 30


# ---------------------------------------------------------------------------
# ログ設定
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(_LOG_FILE), encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)


logger = logging.getLogger("scheduler")


# ---------------------------------------------------------------------------
# 取引カレンダー判定
# ---------------------------------------------------------------------------

def _check_is_trading_day(today: date) -> bool:
    """今日が取引日（JPX 営業日）かどうかを返す。

    market_calendar テーブルを read-only で参照する。
    DuckDB が利用不能（DB 未初期化・ロック等）な場合は土日チェックにフォールバック。
    read-only 接続は即座にクローズするため、バッチジョブと競合しない。
    """
    try:
        from kabusys.config import Settings
        from kabusys.data.calendar_management import is_trading_day
        import duckdb

        settings = Settings()
        if not settings.duckdb_path.exists():
            raise FileNotFoundError(f"DuckDB が見つかりません: {settings.duckdb_path}")

        conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
        try:
            result = is_trading_day(conn, today)
        finally:
            conn.close()

        logger.debug("取引カレンダー: %s → is_trading_day=%s (DB参照)", today, result)
        return result

    except Exception as exc:
        # DB 未初期化・接続失敗時は土日フォールバック
        is_weekday = today.weekday() < 5
        logger.warning(
            "取引カレンダー取得失敗 (%s)。土日フォールバック: %s → %s",
            exc, today, "営業日" if is_weekday else "休日",
        )
        return is_weekday


# ---------------------------------------------------------------------------
# ジョブ定義
# ---------------------------------------------------------------------------

@dataclass
class JobSpec:
    name: str                # 識別子 (ran_today・ログファイル名に使用)
    script: str              # scripts/ 以下のファイル名
    args: list[str]          # 追加引数
    trigger_hour: int
    trigger_minute: int
    needs_exclusive_db: bool  # True → 実行前に run_execution を停止する
    enabled: bool = True


def _parse_env_flag(key: str, default: bool = False) -> bool:
    """プロジェクトルートの .env から bool フラグを読む。"""
    env_file = _PROJECT_ROOT / ".env"
    if not env_file.exists():
        return default
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().lower() == "true"
    return default


def _build_job_schedule() -> list[JobSpec]:
    """ジョブリストを構築する。起動時と日付変更時に呼ばれる。"""
    enable_yahoonews = _parse_env_flag("ENABLE_YAHOONEWS")
    enable_ai = _parse_env_flag("ENABLE_AI_SENTIMENT")
    enable_tdnet = _parse_env_flag("ENABLE_TDNET")

    return [
        # --- 朝のレポート (execution 起動前なので DB 競合なし) ---
        JobSpec("pre_market_report",
                "run_pre_market_report.py",            [],  8,  0, False),
        JobSpec("signal_queue_report",
                "run_signal_queue_report.py",          [],  8,  2, False),
        JobSpec("position_reconciliation_report",
                "run_position_reconciliation_report.py", [], 8, 5, False),

        # --- システム起動 ---
        JobSpec("execution_start",
                "start_system.py",
                ["--component", "execution", "--clear-stop-flag"],
                8, 30, False),
        JobSpec("monitoring_start",
                "start_system.py",
                ["--component", "monitoring"],
                9,  0, False),

        # --- 夜間バッチ (DuckDB 書き込みが必要 → execution を事前停止) ---
        JobSpec("tdnet_collection",
                "run_tdnet_collection.py",      [], 15, 35, True,  enable_tdnet),
        JobSpec("data_update",
                "run_data_update.py",           [], 17, 30, True),
        JobSpec("yahoonews_collection",
                "run_yahoonews_collection.py",  [], 17, 33, True,  enable_yahoonews),
        JobSpec("feature_gen",
                "run_feature_gen.py",           [], 18, 30, True),
        JobSpec("ai_analysis",
                "run_ai_analysis.py",           [], 19,  0, True,  enable_ai),
        JobSpec("strategy_signal",
                "run_strategy_signal.py",       [], 20,  0, True),
        JobSpec("portfolio_construction",
                "run_portfolio_construction.py",[], 21,  0, True),
        JobSpec("night_batch_report",
                "run_night_batch_report.py",    [], 21, 15, True),
    ]


# ---------------------------------------------------------------------------
# プロセス管理
# ---------------------------------------------------------------------------

def _is_execution_running() -> bool:
    pid = read_pid(EXECUTION_PID_PATH)
    return pid is not None and is_process_running(pid)


def _stop_execution_if_running() -> bool:
    """execution が起動中なら stop_system.py で停止し、True を返す。"""
    if not _is_execution_running():
        return False

    logger.info("execution エンジンを停止します (stop_system.py)...")
    result = subprocess.run(
        [_PYTHON, str(_SCRIPTS_DIR / "stop_system.py")],
        cwd=str(_PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        logger.warning("stop_system.py が rc=%d で終了しました:\n%s",
                       result.returncode, result.stderr.strip())

    # stop_system.py のタイムアウト後も念のため追加待機
    deadline = time.monotonic() + _STOP_WAIT_SEC
    while time.monotonic() < deadline and _is_execution_running():
        time.sleep(0.5)

    if _is_execution_running():
        logger.warning("execution プロセスが %d 秒後もまだ起動中です。バッチを続行します。",
                       _STOP_WAIT_SEC)
    else:
        logger.info("execution エンジンが停止しました。")
    return True


def _start_execution() -> None:
    """execution エンジンを再起動する（停止フラグをクリアして start_system.py を呼ぶ）。"""
    if _is_execution_running():
        logger.info("execution エンジンは既に起動中です。スキップします。")
        return
    logger.info("execution エンジンを再起動します...")
    subprocess.Popen(
        [_PYTHON, str(_SCRIPTS_DIR / "start_system.py"),
         "--component", "execution", "--clear-stop-flag"],
        cwd=str(_PROJECT_ROOT),
    )


# ---------------------------------------------------------------------------
# ジョブ実行
# ---------------------------------------------------------------------------

def _run_job(job: JobSpec) -> int:
    """ジョブを同期実行してリターンコードを返す。"""
    script = _SCRIPTS_DIR / job.script
    cmd = [_PYTHON, str(script)] + job.args
    logger.info("ジョブ開始: %s", " ".join(str(c) for c in cmd))

    log_file = _PROJECT_ROOT / "logs" / f"{job.name}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with log_file.open("a", encoding="utf-8") as lf:
        lf.write(f"\n=== {datetime.now().isoformat()} ===\n")
        result = subprocess.run(cmd, cwd=str(_PROJECT_ROOT), stdout=lf, stderr=lf)

    if result.returncode != 0:
        logger.warning("ジョブ失敗: %s (rc=%d) → ログ: %s",
                       job.name, result.returncode, log_file)
    else:
        logger.info("ジョブ完了: %s (rc=0)", job.name)
    return result.returncode


# ---------------------------------------------------------------------------
# 実行済みジョブの永続化
# ---------------------------------------------------------------------------

def _load_ran_today() -> set[str]:
    """data/scheduler_ran_today.json から本日分の実行済みジョブを復元する。"""
    if not _RAN_TODAY_FILE.exists():
        return set()
    try:
        data = json.loads(_RAN_TODAY_FILE.read_text(encoding="utf-8"))
        return set(data.get(date.today().isoformat(), []))
    except Exception:
        return set()


def _save_ran_today(today: date, ran_today: set[str]) -> None:
    _RAN_TODAY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _RAN_TODAY_FILE.write_text(
        json.dumps({today.isoformat(): sorted(ran_today)}, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# メインループ
# ---------------------------------------------------------------------------

def _in_execution_window(t: dtime) -> bool:
    """取引時間帯なら True（この時間帯のみ exclusive_db 後に execution を再起動する）。"""
    return _EXECUTION_START_TIME <= t <= _MARKET_CLOSE_TIME


def _print_schedule(jobs: list[JobSpec]) -> None:
    print(f"{'時刻':>6}  {'ジョブ名':<35}  {'exclusive_db':^14}  {'enabled':^8}")
    print("-" * 72)
    for j in jobs:
        status = "YES" if j.needs_exclusive_db else "-"
        ena = "yes" if j.enabled else "skip"
        print(f"{j.trigger_hour:02d}:{j.trigger_minute:02d}  {j.name:<35}  {status:^14}  {ena:^8}")


def main() -> None:
    parser = argparse.ArgumentParser(description="KabuSys スケジューラーデーモン")
    parser.add_argument("--once", action="store_true",
                        help="1 回チェックして終了（動作確認用）")
    parser.add_argument("--list", action="store_true",
                        help="スケジュールを表示して終了")
    args = parser.parse_args()

    _setup_logging()
    jobs = _build_job_schedule()

    if args.list:
        _print_schedule(jobs)
        return

    logger.info("KabuSys スケジューラーデーモン起動 (PID=%d)", os.getpid())
    logger.info("ポーリング間隔: %d 秒 / ログ: %s", _POLL_INTERVAL_SEC, _LOG_FILE)

    ran_today = _load_ran_today()
    last_date = date.today()
    today_is_trading: bool = _check_is_trading_day(last_date)
    logger.info("本日 %s は%s", last_date, "営業日です。" if today_is_trading else "非営業日です。ジョブをスキップします。")

    while True:
        now = datetime.now()
        today = now.date()

        # 日付が変わったらスケジュールをリセット (.env 再読み込みも兼ねる)
        if today != last_date:
            logger.info("日付変更 (%s → %s)。スケジュールをリセットします。", last_date, today)
            ran_today.clear()
            _save_ran_today(today, ran_today)
            last_date = today
            jobs = _build_job_schedule()
            today_is_trading = _check_is_trading_day(today)
            logger.info(
                "本日 %s は%s", today,
                "営業日です。" if today_is_trading else "非営業日です。ジョブをスキップします。",
            )

        # 非営業日はすべてのジョブをスキップ
        if not today_is_trading:
            if args.once:
                logger.info("--once モード: 非営業日のためスキップして終了します。")
                break
            time.sleep(_POLL_INTERVAL_SEC)
            continue

        for job in jobs:
            if not job.enabled:
                continue
            if job.name in ran_today:
                continue
            trigger_dt = datetime.combine(today, dtime(job.trigger_hour, job.trigger_minute))
            if now < trigger_dt:
                continue

            # トリガー時刻到達
            logger.info(
                "トリガー: %s (予定 %02d:%02d、現在 %s)",
                job.name, job.trigger_hour, job.trigger_minute, now.strftime("%H:%M:%S"),
            )
            ran_today.add(job.name)
            _save_ran_today(today, ran_today)

            was_running = False
            if job.needs_exclusive_db:
                was_running = _stop_execution_if_running()

            _run_job(job)

            # execution 停止していた場合: 取引時間内なら再起動
            if was_running and _in_execution_window(now.time()):
                logger.info("取引時間帯のため execution エンジンを再起動します。")
                _start_execution()

        if args.once:
            logger.info("--once モード: チェック完了。終了します。")
            break

        time.sleep(_POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
