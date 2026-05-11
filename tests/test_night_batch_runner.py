"""tests/test_night_batch_runner.py

run_night_batch_report.py のヘルパー関数のユニットテスト。
スクリプトを直接インポートして検証する。
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

# scripts/ ディレクトリを sys.path に追加してスクリプトをインポートする
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from run_night_batch_report import (  # noqa: E402
    collect_next_day_summary,
    collect_update_counts,
    load_job_results_or_empty,
)

# ---------------------------------------------------------------------------
# DB セットアップヘルパー
# ---------------------------------------------------------------------------


def _setup_db(conn: duckdb.DuckDBPyConnection) -> None:
    """テスト用の最小スキーマを作成する。"""
    conn.execute("CREATE TABLE prices_daily (date DATE, code VARCHAR, close DOUBLE)")
    conn.execute(
        "CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score DOUBLE, signal_rank INT)"
    )
    conn.execute("CREATE TABLE signal_queue (date DATE, code VARCHAR, status VARCHAR)")


# ---------------------------------------------------------------------------
# load_job_results_or_empty のテスト
# ---------------------------------------------------------------------------


def test_load_job_results_or_empty_nonexistent_dir(tmp_path: Path) -> None:
    """存在しないディレクトリを指定した場合は空リストを返す。"""
    nonexistent = tmp_path / "no_such_dir"
    result = load_job_results_or_empty(date(2026, 5, 7), base_dir=nonexistent)
    assert result == []


def test_load_job_results_or_empty_with_results(tmp_path: Path) -> None:
    """JSON ファイルが存在する場合に JobRunResult リストを返す。"""
    run_date = date(2026, 5, 7)
    job_dir = tmp_path / run_date.isoformat()
    job_dir.mkdir(parents=True)

    now = datetime.now(timezone.utc)
    job_data = {
        "job_name": "data_update_job",
        "status": "success",
        "started_at": now.isoformat(),
        "finished_at": now.isoformat(),
        "duration_sec": 12.5,
        "updated_rows": {"prices_daily": 100},
        "warnings": [],
        "errors": [],
    }
    (job_dir / "data_update_job.json").write_text(json.dumps(job_data), encoding="utf-8")

    result = load_job_results_or_empty(run_date, base_dir=tmp_path)
    assert len(result) == 1
    assert result[0].job_name == "data_update_job"
    assert result[0].status == "success"
    assert result[0].duration_sec == 12.5


def test_load_job_results_or_empty_handles_error(tmp_path: Path) -> None:
    """base_dir にファイルを渡してもエラーを返さず空リストを返す。"""
    # tmp_path にファイルを作成し、それをディレクトリとして渡す
    bogus_file = tmp_path / "not_a_dir.txt"
    bogus_file.write_text("content", encoding="utf-8")

    # not_a_dir.txt/{date} は存在しないので空リストを返すべき
    result = load_job_results_or_empty(date(2026, 5, 7), base_dir=bogus_file)
    assert result == []


# ---------------------------------------------------------------------------
# collect_update_counts のテスト
# ---------------------------------------------------------------------------


def test_collect_update_counts_empty_tables() -> None:
    """空テーブルのみ存在する場合、全カウントが 0 になる。"""
    conn = duckdb.connect(":memory:")
    _setup_db(conn)
    try:
        counts = collect_update_counts(conn, date(2026, 5, 7))
        assert counts.prices_daily == 0
        assert counts.signals == 0
        assert counts.signal_queue == 0
        assert counts.fundamentals == 0
        assert counts.ai_scores == 0
        assert counts.features == 0
        assert counts.raw_news == 0
    finally:
        conn.close()


def test_collect_update_counts_with_data() -> None:
    """データを挿入した場合に正しいカウントを返す。"""
    conn = duckdb.connect(":memory:")
    _setup_db(conn)
    run_date = date(2026, 5, 7)
    try:
        conn.execute("INSERT INTO prices_daily VALUES (?, '1301', 100.0)", [run_date])
        conn.execute("INSERT INTO prices_daily VALUES (?, '1302', 200.0)", [run_date])
        conn.execute("INSERT INTO signals VALUES (?, '1301', 'buy', 0.8, 1)", [run_date])
        conn.execute("INSERT INTO signal_queue VALUES (?, '1301', 'pending')", [run_date])

        counts = collect_update_counts(conn, run_date)
        assert counts.prices_daily == 2
        assert counts.signals == 1
        assert counts.signal_queue == 1
    finally:
        conn.close()


def test_collect_update_counts_missing_tables_return_zero() -> None:
    """存在しないテーブル（fundamentals, ai_scores, features 等）はカウント 0 を返す。"""
    conn = duckdb.connect(":memory:")
    # prices_daily と signals のみ作成、他は作らない
    conn.execute("CREATE TABLE prices_daily (date DATE, code VARCHAR, close DOUBLE)")
    conn.execute(
        "CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score DOUBLE, signal_rank INT)"
    )
    # signal_queue は作らない
    try:
        counts = collect_update_counts(conn, date(2026, 5, 7))
        assert counts.fundamentals == 0
        assert counts.ai_scores == 0
        assert counts.features == 0
        assert counts.raw_news == 0
        assert counts.signal_queue == 0
    finally:
        conn.close()


def test_collect_update_counts_prices_daily_count() -> None:
    """run_date の行のみカウントされ、他の日付の行は含まれない。"""
    conn = duckdb.connect(":memory:")
    _setup_db(conn)
    run_date = date(2026, 5, 7)
    other_date = date(2026, 5, 6)
    try:
        conn.execute("INSERT INTO prices_daily VALUES (?, '1301', 100.0)", [run_date])
        conn.execute("INSERT INTO prices_daily VALUES (?, '1302', 200.0)", [run_date])
        conn.execute("INSERT INTO prices_daily VALUES (?, '1303', 300.0)", [run_date])
        conn.execute("INSERT INTO prices_daily VALUES (?, '1304', 400.0)", [other_date])

        counts = collect_update_counts(conn, run_date)
        assert counts.prices_daily == 3
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# collect_next_day_summary のテスト
# ---------------------------------------------------------------------------


def test_collect_next_day_summary_with_future_data() -> None:
    """prices_daily に翌日データが存在する場合、next_trading_day が正しく設定される。"""
    conn = duckdb.connect(":memory:")
    _setup_db(conn)
    run_date = date(2026, 5, 7)
    next_day = date(2026, 5, 8)
    try:
        conn.execute("INSERT INTO prices_daily VALUES (?, '1301', 100.0)", [next_day])

        summary = collect_next_day_summary(conn, run_date)
        assert summary.buy_count == 0
        assert summary.sell_count == 0
    finally:
        conn.close()


def test_collect_next_day_summary_no_future_data() -> None:
    """将来データがない場合でもクラッシュせず、デフォルト値を返す。"""
    conn = duckdb.connect(":memory:")
    _setup_db(conn)
    run_date = date(2026, 5, 7)
    try:
        # prices_daily は空
        summary = collect_next_day_summary(conn, run_date)
        # 例外が起きないことと、buy/sell カウントが 0 であることを確認
        assert summary.buy_count == 0
        assert summary.sell_count == 0
    finally:
        conn.close()


def test_collect_next_day_summary_signal_counts() -> None:
    """buy/sell シグナルを挿入すると、対応するカウントが返る。"""
    conn = duckdb.connect(":memory:")
    _setup_db(conn)
    run_date = date(2026, 5, 7)
    try:
        conn.execute("INSERT INTO signals VALUES (?, '1301', 'buy', 0.9, 1)", [run_date])
        conn.execute("INSERT INTO signals VALUES (?, '1302', 'buy', 0.8, 2)", [run_date])
        conn.execute("INSERT INTO signals VALUES (?, '1303', 'sell', 0.7, 3)", [run_date])

        summary = collect_next_day_summary(conn, run_date)
        assert summary.buy_count == 2
        assert summary.sell_count == 1
    finally:
        conn.close()
