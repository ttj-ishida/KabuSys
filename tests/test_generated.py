import importlib
import json
import math
import os
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import pytest


def test_get_poll_interval_valid_and_invalid(monkeypatch):
    # Import the module
    from kabusys import run_monitoring

    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "5")
    assert run_monitoring._get_poll_interval() == 5

    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    # 0 is treated as invalid and should fallback to default
    assert run_monitoring._get_poll_interval() == run_monitoring._DEFAULT_POLL_INTERVAL

    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-10")
    assert run_monitoring._get_poll_interval() == run_monitoring._DEFAULT_POLL_INTERVAL

    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "not-an-int")
    assert run_monitoring._get_poll_interval() == run_monitoring._DEFAULT_POLL_INTERVAL

    # Clean up
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)


def reload_config_with_disable(monkeypatch):
    # Ensure automatic env load is disabled during tests
    monkeypatch.setenv("KABUSYS_DISABLE_AUTO_ENV_LOAD", "1")
    import importlib

    import kabusys.config as config

    importlib.reload(config)
    return config


def test_parse_env_line_basic_cases(monkeypatch):
    config = reload_config_with_disable(monkeypatch)

    # Blank / comment
    assert config._parse_env_line("") is None
    assert config._parse_env_line("# comment") is None

    # export prefix
    assert config._parse_env_line("export KEY=value") == ("KEY", "value")

    # simple key=value
    assert config._parse_env_line("A=1") == ("A", "1")

    # quoted single with escapes
    assert config._parse_env_line(r"Q='va\'lue'") == ("Q", "va'lue")
    # quoted double with escape
    assert config._parse_env_line(r'P="line\n"') == ("P", "line\n")

    # inline comment for unquoted where '#' preceded by space
    assert config._parse_env_line("X=foo # comment") == ("X", "foo")
    # '#' without preceding space is part of value
    assert config._parse_env_line("Y=foo#bar") == ("Y", "foo#bar")

    # no equals -> None
    assert config._parse_env_line("NOEQUAL") is None

    # empty key
    assert config._parse_env_line("=value") is None


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    config = reload_config_with_disable(monkeypatch)
    temp = tmp_path / ".env.test"
    temp.write_text(
        "\n".join(
            [
                "A=1",
                "B=2",
                "C='escaped\\'quote'",
                "OSVAR=should_override",
            ]
        )
    )
    # Set protected env keys as if OS provided them
    monkeypatch.setenv("OSVAR", "original")
    protected = frozenset(os.environ.keys())
    # Load without override: should set A,B,C but not overwrite existing OSVAR
    config._load_env_file(temp, override=False, protected=protected)
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "2"
    assert os.environ.get("C") == "escaped'quote"
    assert os.environ.get("OSVAR") == "original"

    # Now load with override=True but protected prevents OSVAR change
    temp.write_text("OSVAR=changed\nD=4\n")
    config._load_env_file(temp, override=True, protected=protected)
    assert os.environ.get("OSVAR") == "original"
    assert os.environ.get("D") == "4"

    # Clean up created keys
    for k in ("A", "B", "C", "D"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("OSVAR", raising=False)


def test_settings_require_and_env_validations(monkeypatch):
    config = reload_config_with_disable(monkeypatch)
    Settings = config.Settings

    s = Settings()
    # Missing required env should raise when accessed
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        _ = s.jquants_refresh_token

    # paper_fill_mode valid and invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    importlib.reload(config)
    s = config.Settings()
    assert s.paper_fill_mode == "instant"

    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    importlib.reload(config)
    s = config.Settings()
    assert s.paper_fill_mode == "partial"

    monkeypatch.setenv("PAPER_FILL_MODE", "INVALID_MODE")
    importlib.reload(config)
    s = config.Settings()
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode

    # env validation
    monkeypatch.setenv("KABUSYS_ENV", "live")
    importlib.reload(config)
    s = config.Settings()
    assert s.env == "live"
    assert s.is_live is True
    assert s.is_paper is False

    monkeypatch.setenv("KABUSYS_ENV", "unknown_env")
    importlib.reload(config)
    s = config.Settings()
    with pytest.raises(ValueError):
        _ = s.env

    # log level invalid
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    importlib.reload(config)
    s = config.Settings()
    assert s.log_level == "DEBUG"

    monkeypatch.setenv("LOG_LEVEL", "BAD")
    importlib.reload(config)
    s = config.Settings()
    with pytest.raises(ValueError):
        _ = s.log_level

    # Clean up env
    for key in ("PAPER_FILL_MODE", "KABUSYS_ENV", "LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)


def test_signal_queue_build_and_format_and_save(tmp_path):
    from kabusys.operations import signal_queue_report as sq

    # Create some signals
    signals = [
        {"code": "1234", "side": "buy", "target_size": None, "target_weight": None, "signal_rank": 1},
        {"code": "5678", "side": "sell", "target_size": 10, "target_weight": 0.1, "signal_rank": 2},
    ]
    report = sq.build_report(signals, report_date=date(2026, 4, 28))
    assert report.total_count == 2
    assert report.buy_count == 1
    assert report.sell_count == 1
    # Expect a warning about missing target_size for buy
    assert any("target_size 未設定" in w for w in report.warnings)

    cli = sq.format_cli_summary(report)
    assert "Signal Queue Confirmation" in cli
    assert "1234" in cli and "5678" in cli

    js = sq.format_json(report)
    parsed = json.loads(js)
    assert parsed["total_count"] == 2
    assert parsed["report_date"] == "2026-04-28"

    # Saving should create files
    out = sq.save_report(report, output_dir=tmp_path)
    assert (out / "summary.json").exists()
    assert (out / "report.md").exists()
    assert (out / "warnings.json").exists()

    # Invalid report_date format should raise
    bad = report
    bad.report_date = "2026_04_28"
    with pytest.raises(ValueError):
        sq.save_report(bad, output_dir=tmp_path)

    # Invalid calendar date
    bad.report_date = "2026-02-30"
    with pytest.raises(ValueError):
        sq.save_report(bad, output_dir=tmp_path)


def test_paper_verification_p95_and_build_date_filter_and_formatters():
    pv = importlib.import_module("kabusys.tools.paper_verification_report")
    # _p95 empty
    assert pv._p95([]) is None
    # _p95 known list
    vals = list(range(1, 101))  # 1..100
    assert pv._p95(vals) == 95

    # _build_date_filter
    clause, params = pv._build_date_filter("ts", None, None)
    assert clause == "" and params == []

    clause, params = pv._build_date_filter("ts", "2026-04-01", "2026-04-30")
    assert "ts >= ?" in clause and "ts <= ?" in clause
    assert params == ["2026-04-01", "2026-04-30"]

    # formatters
    assert pv._fmt_float(None) == "N/A"
    assert pv._fmt_float(12.3456, 2, " ms") == "12.35 ms"
    assert pv._fmt_int(None) == "N/A"
    assert pv._fmt_int(10) == "10"


def test_execution_startup_build_and_format():
    es = importlib.import_module("kabusys.operations.execution_startup_report")

    class DummyDiscrep:
        def __init__(self, code, b, l):
            self.code = code
            self.broker_qty = b
            self.local_qty = l
            self.diff = b - l

    class DummyRecon:
        def __init__(self, synced, no_status, discrepancies):
            self.orders_synced = synced
            self.orders_no_status = no_status
            self.position_discrepancies = discrepancies

    # BLOCKED due to orders_no_status
    dr = DummyRecon(10, 1, [])
    report = es.build_report(dr, startup_date=date(2026, 4, 28))
    assert report.status == es.STATUS_BLOCKED
    assert any("ステータス不明の注文" in w for w in report.warnings)

    # READY_WITH_WARNINGS due to discrepancies
    disc = [DummyDiscrep("9999", 10, 8)]
    dr2 = DummyRecon(5, 0, disc)
    report2 = es.build_report(dr2, startup_date=date(2026, 4, 28))
    assert report2.status == es.STATUS_READY_WITH_WARNINGS
    assert any("ポジション差分" in w for w in report2.warnings)

    # READY
    dr3 = DummyRecon(0, 0, [])
    report3 = es.build_report(dr3, startup_date=date(2026, 4, 28))
    assert report3.status == es.STATUS_READY

    # format_json returns JSON string matching fields
    js = es.format_json(report2)
    parsed = json.loads(js)
    assert parsed["status"] == es.STATUS_READY_WITH_WARNINGS


def test_night_batch_determine_and_generate_warnings():
    nb = importlib.import_module("kabusys.operations.night_batch_report")
    # Prepare JobRunResult
    JobRunResult = nb.JobRunResult
    UpdateCounts = nb.UpdateCounts
    NextDaySummary = nb.NextDaySummary

    now = datetime.now(timezone.utc)
    # Missing mandatory job -> BLOCKED
    jr1 = JobRunResult(job_name="data_update_job", status="success", started_at=now, finished_at=now, duration_sec=1.0, updated_rows={}, warnings=[], errors=[])
    # omit many mandatory jobs
    report = nb.build_report(job_results=[jr1], update_counts=UpdateCounts(prices_daily=1, features=1, signals=1, signal_queue=1, news_articles=0, ai_scores=0, fundamentals=0), next_day_summary=NextDaySummary(), run_date=date(2026,4,28), target_date=date(2026,4,29))
    assert report.status == nb.STATUS_BLOCKED
    assert any("必須ジョブが実行されませんでした" in w for w in report.warnings)

    # All mandatory present but one failed -> BLOCKED
    job_results = []
    for name in nb.MANDATORY_JOBS:
        status = "failed" if name == nb.MANDATORY_JOBS[0] else "success"
        job_results.append(JobRunResult(job_name=name, status=status, started_at=now, finished_at=now, duration_sec=1.0, updated_rows={}, warnings=[], errors=[]))
    report2 = nb.build_report(job_results=job_results, update_counts=UpdateCounts(prices_daily=1, features=1, signals=1, signal_queue=1, news_articles=0, ai_scores=0, fundamentals=0), next_day_summary=NextDaySummary(), run_date=date(2026,4,28), target_date=date(2026,4,29))
    assert report2.status == nb.STATUS_BLOCKED
    assert any("必須ジョブが失敗しました" in w for w in report2.warnings)

    # Warnings scenario: signals ==0 triggers READY_WITH_WARNINGS
    job_results_ok = [JobRunResult(job_name=n, status="success", started_at=now, finished_at=now, duration_sec=1.0, updated_rows={}, warnings=[], errors=[]) for n in nb.MANDATORY_JOBS]
    report3 = nb.build_report(job_results=job_results_ok, update_counts=UpdateCounts(prices_daily=1, features=1, signals=0, signal_queue=1, news_articles=0, ai_scores=0, fundamentals=0), next_day_summary=NextDaySummary(), run_date=date(2026,4,28), target_date=date(2026,4,29))
    assert report3.status == nb.STATUS_READY_WITH_WARNINGS
    assert any("signals が生成されていません" in w or "signals が生成されていません" in " ".join(report3.warnings) for w in report3.warnings) or any("signals" in w for w in report3.warnings)

    # Ready scenario
    report4 = nb.build_report(job_results=job_results_ok, update_counts=UpdateCounts(prices_daily=1, features=1, signals=1, signal_queue=1, news_articles=0, ai_scores=0, fundamentals=0), next_day_summary=NextDaySummary(), run_date=date(2026,4,28), target_date=date(2026,4,29))
    assert report4.status == nb.STATUS_READY
    assert isinstance(nb.format_cli_summary(report4), str)
    # JSON serialization should succeed
    js = nb.format_json(report4)
    _ = json.loads(js)


def test_performance_build_report_daily_weekly_monthly():
    pr = importlib.import_module("kabusys.operations.performance_report")
    from kabusys.operations.performance_report import DailyRow, WeeklyRow, MonthlyRow

    # Daily: three days
    rows = [
        DailyRow(date=date(2026,4,1), env="live", equity=100.0, daily_return=0.01, drawdown=-0.01, cumulative_return=None),
        DailyRow(date=date(2026,4,2), env="live", equity=110.0, daily_return=0.10, drawdown=-0.02, cumulative_return=None),
        DailyRow(date=date(2026,4,3), env="live", equity=105.0, daily_return=-0.04545, drawdown=-0.04545, cumulative_return=None),
    ]
    rep = pr.build_report(rows, report_type="daily", env="live", from_date=date(2026,4,1), to_date=date(2026,4,3))
    s = rep.summary
    assert s["total_trading_days"] == 3
    assert pytest.approx(s["equity_start"]) == 100.0
    assert pytest.approx(s["equity_end"]) == 105.0
    # cumulative return = 105/100 -1 = 0.05
    assert pytest.approx(s["cumulative_return"], rel=1e-6) == 0.05
    assert 0.0 <= s["win_rate"] <= 1.0

    # Weekly: build from daily via collect_weekly_rows requires DB; instead craft WeeklyRow
    wrows = [
        WeeklyRow(week_label="2026-W13", trading_days=3, equity_start=100.0, equity_end=110.0, weekly_return=0.1, max_drawdown=-0.02, win_days=2),
        WeeklyRow(week_label="2026-W14", trading_days=2, equity_start=110.0, equity_end=120.0, weekly_return=0.0909, max_drawdown=-0.01, win_days=2),
    ]
    repw = pr.build_report(wrows, report_type="weekly", env="live", from_date=date(2026,4,1), to_date=date(2026,4,14))
    sw = repw.summary
    assert sw["total_trading_days"] == 5
    assert sw["equity_start"] == 100.0
    assert sw["equity_end"] == 120.0

    # Monthly
    mrows = [
        MonthlyRow(month_label="2026-04", trading_days=5, equity_start=100.0, equity_end=150.0, monthly_return=0.5, max_drawdown=-0.1, win_days=3)
    ]
    repm = pr.build_report(mrows, report_type="monthly", env="live", from_date=date(2026,4,1), to_date=date(2026,4,30))
    sm = repm.summary
    assert sm["total_trading_days"] == 5
    assert sm["equity_start"] == 100.0
    assert sm["equity_end"] == 150.0
    assert sm["cumulative_return"] == pytest.approx(0.5)

    # Formatters produce strings
    md = pr.format_markdown(repm)
    assert "# 運用成績レポート" in md
    out_dir = pr.save_report(repm, output_dir=Path(tempfile_folder := Path.cwd() / "tmp_perf"))
    assert (out_dir / "report.md").exists()
    # Clean up created folder
    try:
        import shutil

        shutil.rmtree(tempfile_folder)
    except Exception:
        pass

# End of tests file.