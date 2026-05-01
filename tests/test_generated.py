import os
import importlib
import json
import math
from pathlib import Path
from datetime import date, datetime, timezone

import pytest

# Ensure auto env loading is disabled to avoid side effects during import
os.environ.setdefault("KABUSYS_DISABLE_AUTO_ENV_LOAD", "1")

# Import modules under test
import kabusys.config as config
import kabusys.tools.paper_verification_report as pvr
import kabusys.operations.signal_queue_report as sqr
import kabusys.operations.performance_report as pr
import kabusys.operations.performance_collector as pc


def test_parse_env_line_blank_and_comment():
    assert config._parse_env_line("") is None
    assert config._parse_env_line("   \n") is None
    assert config._parse_env_line("# a comment") is None
    assert config._parse_env_line("   # another") is None


def test_parse_env_line_export_and_quotes_and_escapes():
    # export prefix
    assert config._parse_env_line("export FOO=bar") == ("FOO", "bar")
    # single quoted with escaped quote
    line = "A='x\\'y' # inline comment"
    assert config._parse_env_line(line) == ("A", "x'y")
    # double quoted with escape
    line2 = 'B="hello\\nworld"'
    assert config._parse_env_line(line2) == ("B", "hellonworld")
    # no equals
    assert config._parse_env_line("NOEQUALS") is None
    # key empty
    assert config._parse_env_line("=value") is None


def test_build_date_filter_variations():
    # neither
    clause, params = pvr._build_date_filter("ts", None, None)
    assert clause == ""
    assert params == []
    # from only
    clause, params = pvr._build_date_filter("ts", "2026-01-01", None)
    assert clause == "ts >= ?"
    assert params == ["2026-01-01"]
    # to only
    clause, params = pvr._build_date_filter("ts", None, "2026-01-31")
    assert clause == "ts <= ?"
    assert params == ["2026-01-31"]
    # both
    clause, params = pvr._build_date_filter("ts", "2026-01-01", "2026-01-31")
    assert " AND " in clause
    assert params == ["2026-01-01", "2026-01-31"]


def test_p95_empty_and_values():
    assert pvr._p95([]) is None
    # single value
    assert pvr._p95([42.0]) == 42.0
    # multiple values
    values = [i for i in range(1, 21)]  # 1..20
    # n=20 -> idx = ceil(20*0.95)-1 = ceil(19)-1 = 19-1 = 18 -> sorted[18] = 19
    assert pvr._p95(values) == 19


def test_fmt_float_and_int():
    assert pvr._fmt_float(None) == "N/A"
    assert pvr._fmt_float(12.3456, decimals=2, suffix=" ms") == "12.35 ms"
    assert pvr._fmt_int(None) == "N/A"
    assert pvr._fmt_int(123) == "123"


def test__parse_and_load_env_file(tmp_path, monkeypatch):
    # prepare a .env file
    env_file = tmp_path / ".env"
    content = "\n".join(
        [
            "# comment",
            "KEY1=val1",
            "KEY2=\"hello # not a comment\"",
            "export KEY3='x\\'y'",
            "BADLINE",
        ]
    )
    env_file.write_text(content, encoding="utf-8")
    # isolate environment
    monkeypatch.delenv("KEY1", raising=False)
    monkeypatch.delenv("KEY2", raising=False)
    monkeypatch.delenv("KEY3", raising=False)
    # load with override=False: should set missing keys
    config._load_env_file(env_file, override=False, protected=frozenset())
    assert os.environ.get("KEY1") == "val1"
    assert os.environ.get("KEY2") == "hello # not a comment"
    assert os.environ.get("KEY3") == "x'y"
    # test override protected: if protected contains KEY1, it should not be overwritten
    monkeypatch.setenv("KEY1", "original")
    config._load_env_file(env_file, override=True, protected=frozenset({"KEY1"}))
    assert os.environ.get("KEY1") == "original"


def test_require_and_settings_properties(monkeypatch):
    # ensure absence of keys triggers ValueError
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        config._require("JQUANTS_REFRESH_TOKEN")
    # set and ensure retrieval
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok123")
    assert config._require("JQUANTS_REFRESH_TOKEN") == "tok123"

    # PAPER_FILL_MODE valid
    s = config.Settings()
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "Partial")
    assert s.paper_fill_mode == "partial"
    # invalid mode
    monkeypatch.setenv("PAPER_FILL_MODE", "invalid_mode")
    with pytest.raises(ValueError):
        config.Settings().paper_fill_mode

    # env validation
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert config.Settings().env == "development"
    monkeypatch.setenv("KABUSYS_ENV", "LIVE")
    assert config.Settings().env == "live"
    monkeypatch.setenv("KABUSYS_ENV", "invalid")
    with pytest.raises(ValueError):
        config.Settings().env

    # log level validation
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    assert config.Settings().log_level == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert config.Settings().log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "NOPE")
    with pytest.raises(ValueError):
        config.Settings().log_level


def make_signal(code: str, side: str, target_size, target_weight, rank):
    return {
        "code": code,
        "side": side,
        "target_size": target_size,
        "target_weight": target_weight,
        "signal_rank": rank,
    }


def test_signal_queue_build_and_format_and_json_and_save(tmp_path):
    # signals with one buy missing size and one sell fully specified
    signals = [
        make_signal("7203", "buy", None, None, 1),
        make_signal("9432", "sell", 100, 0.05, 2),
    ]
    report = sqr.build_report(signals, report_date=date(2026, 4, 28))
    assert report.status == sqr.STATUS_READY
    assert report.total_count == 2
    assert report.buy_count == 1
    assert report.sell_count == 1
    # warnings should mention target_size missing
    assert any("target_size" in w for w in report.warnings)

    # format CLI summary contains codes and counts
    text = sqr.format_cli_summary(report)
    assert "7203" in text
    assert "9432" in text
    assert "total" in text
    assert "buy" in text

    # format_json returns valid JSON with expected keys
    j = sqr.format_json(report)
    obj = json.loads(j)
    assert obj["status"] == report.status
    assert obj["total_count"] == report.total_count
    assert isinstance(obj["signals"], list)

    # save_report writes files to provided output dir
    out = sqr.save_report(report, output_dir=tmp_path)
    assert (out / "summary.json").exists()
    assert (out / "report.md").exists()
    assert (out / "warnings.json").exists()
    # validate content of summary.json
    data = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert data["report_date"] == report.report_date


def test_save_report_invalid_date_raises(tmp_path):
    # craft a fake report dataclass with invalid date string
    bad = sqr.SignalQueueReport(
        report_date="2026-02-30",  # invalid calendar date but matches regex
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status="READY",
        total_count=0,
        buy_count=0,
        sell_count=0,
        signals=[],
        warnings=[],
    )
    with pytest.raises(ValueError):
        sqr.save_report(bad, output_dir=tmp_path)


def make_daily_row(d: date, equity, daily_return, drawdown, cumulative):
    return pc.DailyRow(
        date=d,
        env="live",
        equity=equity,
        daily_return=daily_return,
        drawdown=drawdown,
        cumulative_return=cumulative,
    )


def test_performance_build_report_daily_and_markdown_and_save(tmp_path):
    # construct three daily rows
    rows = [
        pc.DailyRow(date=date(2026, 4, 1), env="live", equity=100.0, daily_return=0.0, drawdown=0.0, cumulative_return=0.0),
        pc.DailyRow(date=date(2026, 4, 2), env="live", equity=110.0, daily_return=0.10, drawdown=-0.01, cumulative_return=0.10),
        pc.DailyRow(date=date(2026, 4, 3), env="live", equity=105.0, daily_return=-0.0454545, drawdown=-0.05, cumulative_return=0.05),
    ]
    report = pr.build_report(rows, report_type="daily", env="live", from_date=date(2026, 4, 1), to_date=date(2026, 4, 3))
    s = report.summary
    assert s["total_trading_days"] == 3
    assert s["equity_start"] == 100.0
    assert s["equity_end"] == 105.0
    # cumulative_return = 105/100 - 1.0 = 0.05
    assert pytest.approx(s["cumulative_return"], rel=1e-6) == 0.05
    md = pr.format_markdown(report)
    assert "累積リターン" in md or "累積" in md
    # save to tmp path
    out = pr.save_report(report, output_dir=tmp_path)
    assert (out / "report.md").exists()


def test_performance_build_report_empty_rows():
    rows: list = []
    report = pr.build_report(rows, report_type="daily", env="live", from_date=date(2026, 4, 1), to_date=date(2026, 4, 3))
    s = report.summary
    # summary fields should be None or zero appropriately
    assert s["total_trading_days"] == 0
    assert s["cumulative_return"] is None
    assert s["equity_start"] is None
    assert s["equity_end"] is None
    md = pr.format_markdown(report)
    assert "営業日数" in md or "期間" in md


# Additional tests for paper_verification_report _query helpers that are pure functions
def test_pvr__fmt_helpers():
    assert pvr._fmt_float(None) == "N/A"
    assert pvr._fmt_float(12.3456, 1) == "12.3"
    assert pvr._fmt_int(None) == "N/A"
    assert pvr._fmt_int(0) == "0"


# Ensure imports didn't trigger unexpected side-effects; reload config to ensure stable state
def test_config_reload_no_auto_load(monkeypatch):
    monkeypatch.setenv("KABUSYS_DISABLE_AUTO_ENV_LOAD", "1")
    importlib.reload(config)
    # after reload, settings instance exists
    s = config.Settings()
    assert isinstance(s, config.Settings)