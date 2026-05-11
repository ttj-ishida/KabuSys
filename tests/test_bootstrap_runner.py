from __future__ import annotations

import gzip
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

from kabusys.data.bootstrap.runner import (
    run_bootstrap,
    BootstrapResult,
    _reset_bootstrap,
    _safe_filename,
    _safe_errmsg,
)


# ---------------------------------------------------------------------------
# テスト用 DB フィクスチャ（最小スキーマ）
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    c.execute("""
        CREATE TABLE bootstrap_load_history (
            file_key VARCHAR NOT NULL PRIMARY KEY,
            endpoint VARCHAR NOT NULL,
            file_name VARCHAR NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'pending',
            row_count BIGINT,
            error_msg VARCHAR,
            loaded_at TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE raw_prices (
            date DATE NOT NULL, code VARCHAR NOT NULL,
            open DECIMAL(18,4), high DECIMAL(18,4),
            low DECIMAL(18,4), close DECIMAL(18,4),
            volume BIGINT, turnover DECIMAL(18,2),
            adj_factor DECIMAL(18,6),
            fetched_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY (date, code)
        )
    """)
    c.execute("""
        CREATE TABLE prices_daily (
            date DATE NOT NULL, code VARCHAR NOT NULL,
            open DECIMAL(18,4) NOT NULL, high DECIMAL(18,4) NOT NULL,
            low DECIMAL(18,4) NOT NULL CHECK (low <= high),
            close DECIMAL(18,4) NOT NULL, volume BIGINT NOT NULL,
            turnover DECIMAL(18,2),
            PRIMARY KEY (date, code)
        )
    """)
    c.execute("""
        CREATE TABLE stocks (
            code VARCHAR NOT NULL PRIMARY KEY,
            name VARCHAR, market VARCHAR, sector VARCHAR,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    c.execute("""
        CREATE TABLE raw_financials (
            code VARCHAR NOT NULL, report_date DATE NOT NULL,
            period_type VARCHAR NOT NULL,
            revenue DECIMAL(20,4), operating_profit DECIMAL(20,4),
            net_income DECIMAL(20,4), eps DECIMAL(18,4), roe DECIMAL(10,6),
            fetched_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY (code, report_date, period_type)
        )
    """)
    c.execute("""
        CREATE TABLE fundamentals (
            code VARCHAR NOT NULL, report_date DATE NOT NULL,
            period_type VARCHAR NOT NULL,
            revenue DECIMAL(20,4), operating_profit DECIMAL(20,4),
            net_income DECIMAL(20,4), eps DECIMAL(18,4), roe DECIMAL(10,6),
            PRIMARY KEY (code, report_date, period_type)
        )
    """)
    c.execute("""
        CREATE TABLE market_calendar (
            date DATE NOT NULL PRIMARY KEY,
            is_trading_day BOOLEAN NOT NULL,
            is_half_day BOOLEAN NOT NULL DEFAULT false,
            is_sq_day BOOLEAN NOT NULL DEFAULT false,
            holiday_name VARCHAR
        )
    """)
    c.execute("""
        CREATE TABLE dividends (
            code VARCHAR NOT NULL, pub_date DATE NOT NULL,
            ref_no VARCHAR NOT NULL,
            ex_date DATE, record_date DATE, pay_date DATE,
            div_rate DECIMAL(18,4),
            fetched_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY (code, pub_date, ref_no)
        )
    """)
    c.execute("""
        CREATE TABLE topix_daily (
            date DATE NOT NULL PRIMARY KEY,
            open DECIMAL(18,4) NOT NULL, high DECIMAL(18,4) NOT NULL,
            low DECIMAL(18,4) NOT NULL, close DECIMAL(18,4) NOT NULL
        )
    """)
    yield c
    c.close()


def _gz_prices(tmp_path: Path) -> bytes:
    import csv
    import io

    buf = io.StringIO()
    w = csv.DictWriter(
        buf, fieldnames=["Date", "Code", "O", "H", "L", "C", "Vo", "Va", "AdjFactor"]
    )
    w.writeheader()
    w.writerow(
        {
            "Date": "2024-01-10",
            "Code": "7203",
            "O": "2800",
            "H": "2850",
            "L": "2780",
            "C": "2830",
            "Vo": "1000000",
            "Va": "",
            "AdjFactor": "1.0",
        }
    )
    return gzip.compress(buf.getvalue().encode())


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------


def test_run_bootstrap_dry_run_returns_result(conn, tmp_path):
    file_list = [{"Key": "prices_2024_01.csv.gz", "Size": 1024, "LastModified": "2024-01-01T00:00:00Z"}]
    with (
        patch("kabusys.data.bootstrap.runner.list_files", return_value=file_list),
        patch(
            "kabusys.data.bootstrap.runner.get_presigned_url",
            return_value="https://s3/f",
        ),
        patch("kabusys.data.bootstrap.runner.download_file") as mock_dl,
    ):
        result = run_bootstrap(
            conn=conn,
            api_key="test_key",
            raw_dir=tmp_path,
            dry_run=True,
            endpoints=["/equities/bars/daily"],
        )
    mock_dl.assert_not_called()
    assert isinstance(result, BootstrapResult)
    assert result.total_files == 1


def test_run_bootstrap_skips_loaded_files(conn, tmp_path):
    conn.execute(
        "INSERT INTO bootstrap_load_history (file_key, endpoint, file_name, status, row_count) "
        "VALUES ('prices_2024_01.csv.gz', '/equities/bars/daily', 'prices_2024_01.csv.gz', 'loaded', 100)"
    )
    file_list = [{"Key": "prices_2024_01.csv.gz", "Size": 1024, "LastModified": "2024-01-01T00:00:00Z"}]
    with (
        patch("kabusys.data.bootstrap.runner.list_files", return_value=file_list),
        patch("kabusys.data.bootstrap.runner.download_file") as mock_dl,
    ):
        result = run_bootstrap(
            conn=conn,
            api_key="test_key",
            raw_dir=tmp_path,
            endpoints=["/equities/bars/daily"],
        )
    mock_dl.assert_not_called()
    assert result.skipped_files == 1


def test_run_bootstrap_records_loaded_status(conn, tmp_path):
    ep_dir = tmp_path / "equities" / "bars" / "daily"
    ep_dir.mkdir(parents=True)
    gz_path = ep_dir / "prices_2024_01.csv.gz"
    gz_path.write_bytes(_gz_prices(tmp_path))

    file_list = [{"Key": "prices_2024_01.csv.gz", "Size": 1024, "LastModified": "2024-01-01T00:00:00Z"}]
    with (
        patch("kabusys.data.bootstrap.runner.list_files", return_value=file_list),
        patch(
            "kabusys.data.bootstrap.runner.get_presigned_url",
            return_value="https://s3/f",
        ),
        patch("kabusys.data.bootstrap.runner.download_file", return_value=gz_path),
    ):
        result = run_bootstrap(
            conn=conn,
            api_key="test_key",
            raw_dir=tmp_path,
            endpoints=["/equities/bars/daily"],
        )

    row = conn.execute(
        "SELECT status, row_count FROM bootstrap_load_history WHERE file_key='prices_2024_01.csv.gz'"
    ).fetchone()
    assert row[0] == "loaded"
    assert row[1] == 1
    assert result.failed_files == 0


def test_run_bootstrap_continues_on_single_file_failure(conn, tmp_path):
    file_list = [
        {"Key": "prices_2024_01.csv.gz", "Size": 1024, "LastModified": "2024-01-01T00:00:00Z"},
        {"Key": "prices_2024_02.csv.gz", "Size": 2048, "LastModified": "2024-02-01T00:00:00Z"},
    ]
    ep_dir = tmp_path / "equities" / "bars" / "daily"
    ep_dir.mkdir(parents=True)
    good_gz = ep_dir / "prices_2024_02.csv.gz"
    good_gz.write_bytes(_gz_prices(tmp_path))

    def _side_effect(url, dest):
        if "2024_01" in str(dest):
            raise RuntimeError("download failed")
        dest.write_bytes(_gz_prices(tmp_path))
        return dest

    with (
        patch("kabusys.data.bootstrap.runner.list_files", return_value=file_list),
        patch(
            "kabusys.data.bootstrap.runner.get_presigned_url",
            return_value="https://s3/f",
        ),
        patch("kabusys.data.bootstrap.runner.download_file", side_effect=_side_effect),
    ):
        result = run_bootstrap(
            conn=conn,
            api_key="test_key",
            raw_dir=tmp_path,
            endpoints=["/equities/bars/daily"],
        )

    assert result.failed_files == 1
    assert result.loaded_files == 1
    failed_row = conn.execute(
        "SELECT status FROM bootstrap_load_history WHERE file_key='prices_2024_01.csv.gz'"
    ).fetchone()
    assert failed_row[0] == "failed"


def test_safe_filename_rejects_dot_and_dotdot():
    assert _safe_filename("path/to/file.csv.gz") == "file.csv.gz"
    assert _safe_filename("file.csv.gz") == "file.csv.gz"
    # PurePosixPath は "path/." を "path" に正規化するため None にはならない
    # 重要なのは ".." を含むパス横断を防ぐこと
    assert _safe_filename("path/..") is None
    assert _safe_filename("..") is None
    assert _safe_filename("") is None


def test_safe_errmsg_masks_http_error():
    import urllib.error

    exc = urllib.error.HTTPError(
        url="https://s3.amazonaws.com/bucket/key?X-Amz-Signature=secret",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )
    msg = _safe_errmsg(exc)
    assert "403" in msg
    assert "Forbidden" in msg
    assert "secret" not in msg
    assert "s3.amazonaws.com" not in msg


def test_safe_errmsg_url_error_shows_reason():
    import urllib.error

    exc = urllib.error.URLError(reason="Connection refused")
    msg = _safe_errmsg(exc)
    assert "Connection refused" in msg
    assert "URLError" in msg


def test_safe_errmsg_generic_exception_shows_message():
    msg = _safe_errmsg(ValueError("some detail"))
    assert msg == "some detail"


def test_safe_errmsg_unwraps_cause_chain():
    """BulkApiError でラップされた HTTPError でも URL が漏れないことを確認。"""
    import urllib.error

    http_exc = urllib.error.HTTPError(
        url="https://s3.amazonaws.com/?X-Amz-Signature=secret",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )
    wrapped = RuntimeError("download failed")
    wrapped.__cause__ = http_exc

    msg = _safe_errmsg(wrapped)
    assert "403" in msg
    assert "Forbidden" in msg
    assert "secret" not in msg


# ---------------------------------------------------------------------------
# _reset_bootstrap
# ---------------------------------------------------------------------------


def test_reset_bootstrap_clears_history_and_raw_dir(conn, tmp_path):
    conn.execute(
        "INSERT INTO bootstrap_load_history (file_key, endpoint, file_name, status, row_count) "
        "VALUES ('k1.csv.gz', '/equities/bars/daily', 'k1.csv.gz', 'loaded', 10)"
    )
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "some_file.csv.gz").write_bytes(b"data")

    _reset_bootstrap(conn, raw_dir)

    rows = conn.execute("SELECT COUNT(*) FROM bootstrap_load_history").fetchone()[0]
    assert rows == 0
    assert not raw_dir.exists()


def test_reset_bootstrap_raw_dir_not_exist(conn, tmp_path):
    raw_dir = tmp_path / "nonexistent"
    _reset_bootstrap(conn, raw_dir)  # 例外が出ないことを確認
    assert not raw_dir.exists()
