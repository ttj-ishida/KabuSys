import os
from types import SimpleNamespace
from pathlib import Path
import json

import pytest

from kabusys.run_monitoring import _get_poll_interval
from kabusys.run_execution import _load_risk_config, _pos_value
from kabusys.config import _parse_env_line, _load_env_file, _require, Settings
import kabusys.validate_config as validate_config
from kabusys.operations.signal_queue_report import (
    build_report,
    format_cli_summary as sq_format_cli_summary,
    format_json as sq_format_json,
    format_markdown as sq_format_markdown,
    save_report as sq_save_report,
)
from datetime import date


def test_get_poll_interval_default_and_valid(monkeypatch):
    # default when unset
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    assert _get_poll_interval() == 60

    # valid positive integer
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "10")
    assert _get_poll_interval() == 10


def test_get_poll_interval_invalid_values(monkeypatch):
    # zero -> fallback
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    assert _get_poll_interval() == 60

    # negative -> fallback
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-5")
    assert _get_poll_interval() == 60

    # non-integer -> fallback
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "abc")
    assert _get_poll_interval() == 60


def write_yaml(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def make_valid_risk_yaml():
    return """
risk:
  max_position_pct: 0.5
  max_utilization: 0.8
  rate_limit_per_sec: 5
  circuit_breaker_errors: 3
  circuit_breaker_window_sec: 60
  max_drawdown: 0.2
"""


def make_invalid_yaml():
    return "this: [unbalanced"


def test_load_risk_config_happy(tmp_path):
    path = tmp_path / "risk_config.yaml"
    write_yaml(path, make_valid_risk_yaml())
    cfg = _load_risk_config(path, initial_portfolio_value=100000.0)
    assert cfg.max_position_pct == pytest.approx(0.5)
    assert cfg.initial_portfolio_value == pytest.approx(100000.0)
    assert cfg.rate_limit_per_sec == 5


def test_load_risk_config_missing_file(tmp_path):
    path = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError):
        _load_risk_config(path, initial_portfolio_value=1.0)


def test_load_risk_config_bad_yaml(tmp_path):
    path = tmp_path / "bad.yaml"
    write_yaml(path, make_invalid_yaml())
    with pytest.raises(ValueError):
        _load_risk_config(path, initial_portfolio_value=1.0)


def test_load_risk_config_missing_risk_key(tmp_path):
    path = tmp_path / "norisk.yaml"
    write_yaml(path, "notrisk: {}")
    with pytest.raises(KeyError):
        _load_risk_config(path, initial_portfolio_value=1.0)


def test_load_risk_config_invalid_ranges(tmp_path):
    # max_position_pct > max_utilization
    path = tmp_path / "badrange.yaml"
    write_yaml(
        path,
        """
risk:
  max_position_pct: 0.9
  max_utilization: 0.5
  rate_limit_per_sec: 5
  circuit_breaker_errors: 3
  circuit_breaker_window_sec: 60
  max_drawdown: 0.2
""",
    )
    with pytest.raises(ValueError):
        _load_risk_config(path, initial_portfolio_value=1.0)

    # rate_limit_per_sec < 1
    path2 = tmp_path / "badrate.yaml"
    write_yaml(
        path2,
        """
risk:
  max_position_pct: 0.5
  max_utilization: 0.7
  rate_limit_per_sec: 0
  circuit_breaker_errors: 3
  circuit_breaker_window_sec: 60
  max_drawdown: 0.2
""",
    )
    with pytest.raises(ValueError):
        _load_risk_config(path2, initial_portfolio_value=1.0)


def test_pos_value_prefers_current_price_and_fallbacks(caplog):
    class P:
        def __init__(self, qty, current_price, avg_price, code="X"):
            self.qty = qty
            self.current_price = current_price
            self.avg_price = avg_price
            self.code = code

    # current_price positive
    p1 = P(qty=10, current_price=100.0, avg_price=90.0)
    assert _pos_value(p1) == pytest.approx(1000.0)

    # current_price None, use avg_price
    p2 = P(qty=2, current_price=None, avg_price=50.0, code="Y")
    assert _pos_value(p2) == pytest.approx(100.0)

    # both prices invalid => returns 0 and logs a warning
    p3 = P(qty=5, current_price=0.0, avg_price=None, code="Z")
    caplog.clear()
    val = _pos_value(p3)
    assert val == 0.0
    # Expect a warning mentioning code Z
    found = any(
        "code=Z" in rec.getMessage() or "Z" in rec.getMessage()
        for rec in caplog.records
    )
    assert found


def test_parse_env_line_various_cases():
    assert _parse_env_line("") is None
    assert _parse_env_line("# comment") is None
    assert _parse_env_line("export KEY=value") == ("KEY", "value")
    assert _parse_env_line("KEY=123") == ("KEY", "123")
    # quoted with escapes
    s = r"SECRET='a\'b\nc'"
    parsed = _parse_env_line(s)
    assert parsed is not None
    k, v = parsed
    assert k == "SECRET"
    assert (
        "a'b" in v
    )  # escape handled, newline included as literal n by our simplistic parser? ensure substring

    # inline comment handling: comment only recognized if preceded by space/tab
    assert _parse_env_line("K=val#notcomment") == ("K", "val#notcomment")
    assert _parse_env_line("K=val #comment") == ("K", "val")


def test_load_env_file_behavior(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# sample",
                "A=1",
                "B=2",
                "EXPORT_ME=should",
                "QUOTED='with spaces'",
                "TO_OVERRIDE=orig",
            ]
        ),
        encoding="utf-8",
    )
    # set an existing env var to test override=False (should not overwrite)
    monkeypatch.setenv("TO_OVERRIDE", "orig")
    # protected contains existing os env keys: simulate with provided frozenset
    _load_env_file(env_file, override=False, protected=frozenset(os.environ.keys()))
    assert os.environ.get("A") == "1"
    assert os.environ.get("TO_OVERRIDE") == "orig"  # unchanged

    # Now test override True but protected prevents overwrite
    monkeypatch.setenv("TO_OVERRIDE", "orig2")
    _load_env_file(env_file, override=True, protected=frozenset(["TO_OVERRIDE"]))
    assert os.environ.get("TO_OVERRIDE") == "orig2"

    # override True without protection overwrites
    _load_env_file(env_file, override=True, protected=frozenset())
    assert os.environ.get("TO_OVERRIDE") == "orig"


def test_require_raises(monkeypatch):
    monkeypatch.delenv("SOME_MUST_EXIST", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_MUST_EXIST")
    monkeypatch.setenv("SOME_MUST_EXIST", "value")
    assert _require("SOME_MUST_EXIST") == "value"


def test_settings_paper_fill_mode_and_env_and_log_level(monkeypatch):
    # valid fill mode
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    s = Settings()
    assert s.paper_fill_mode == "instant"

    # invalid fill mode
    monkeypatch.setenv("PAPER_FILL_MODE", "badmode")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode

    # env valid
    monkeypatch.setenv("KABUSYS_ENV", "live")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    s2 = Settings()
    assert s2.env == "live"
    assert s2.is_live is True
    assert s2.log_level == "INFO"

    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "unknown-env")
    with pytest.raises(ValueError):
        _ = Settings().env

    # invalid log level
    monkeypatch.setenv("KABUSYS_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "nope")
    with pytest.raises(ValueError):
        _ = Settings().log_level


def test_settings_enable_ai_sentiment(monkeypatch):
    """ENABLE_AI_SENTIMENT の読み込みと デフォルト False を確認する。"""
    monkeypatch.delenv("ENABLE_AI_SENTIMENT", raising=False)
    assert Settings().enable_ai_sentiment is False

    # 許容リスト（True になる値）
    for val in ("true", "True", "TRUE", "1", "yes", "on"):
        monkeypatch.setenv("ENABLE_AI_SENTIMENT", val)
        assert Settings().enable_ai_sentiment is True, f"{val!r} should be True"

    # それ以外はすべて False（空文字・"off"・"disabled" も含む）
    for val in ("false", "0", "no", "", "off", "disabled", "FALSE"):
        monkeypatch.setenv("ENABLE_AI_SENTIMENT", val)
        assert Settings().enable_ai_sentiment is False, f"{val!r} should be False"


def test_intraday_determine_status_and_formatting():
    # Build a snapshot-like object with required attributes
    snap = SimpleNamespace(
        kill_switch_active=False,
        execution_pid_ok=True,
        drawdown_pct=None,
        order_error_count=0,
        stale_order_count=0,
        monitoring_pid_ok=True,
        process_ok=True,
        cpu_percent=12.34,
        memory_percent=None,
    )
    # status OK
    from kabusys.run_intraday_monitor import (
        _determine_status,
        format_cli_summary,
        STATUS_OK,
    )

    assert _determine_status(snap) == STATUS_OK
    formatted = format_cli_summary(snap)
    assert "KabuSys Intraday Monitor" in formatted
    assert "CPU" in formatted
    assert "Memory" in formatted

    # make it critical via kill switch
    snap.kill_switch_active = True
    snap.kill_switch_reason = "manual"
    from kabusys.run_intraday_monitor import STATUS_CRITICAL

    assert _determine_status(snap) == STATUS_CRITICAL
    fmt2 = format_cli_summary(snap)
    assert "Kill Switch" in fmt2
    assert "CRIT" in fmt2 or "🚫" in fmt2


def test_validate_config_checks_and_yaml(monkeypatch, tmp_path):
    # prepare a fake config dir and monkeypatch module variable
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "token_ok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw_ok")
    # create a tmp config dir and some files
    fake_config = tmp_path / "config"
    fake_config.mkdir()
    good_yaml = fake_config / "system_config.yaml"
    good_yaml.write_text("ok: true", encoding="utf-8")
    bad_yaml = fake_config / "risk_config.yaml"
    bad_yaml.write_text("{unclosed")
    # monkeypatch the module _CONFIG_DIR
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", fake_config)
    # Run validate
    errors, warnings, infos = validate_config.validate()
    # risk_config.yaml parse should produce an error
    # There should be at least one error due to bad yaml parse
    assert any("risk_config.yaml" in e for e in errors)
    # infos should include required env infos
    assert any("JQUANTS_BULK_API_KEY" in i for i in infos)


def _make_valid_risk_config_yaml() -> str:
    return """
risk:
  max_position_pct: 0.20
  max_utilization: 0.80
  max_drawdown: 0.20
  rate_limit_per_sec: 5
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
"""


def _make_risk_config_dir(tmp_path, risk_yaml: str) -> Path:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "risk_config.yaml").write_text(risk_yaml, encoding="utf-8")
    return cfg_dir


def test_check_risk_config_content_valid(monkeypatch, tmp_path):
    """有効な risk_config.yaml はエラーなしで通過すること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    cfg_dir = _make_risk_config_dir(tmp_path, _make_valid_risk_config_yaml())
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    risk_errors = [e for e in errors if "risk" in e.lower() or "max_" in e]
    assert risk_errors == [], f"想定外のエラー: {risk_errors}"


def test_check_risk_config_content_missing_risk_section(monkeypatch, tmp_path):
    """'risk' セクションがない場合はエラーになること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    cfg_dir = _make_risk_config_dir(tmp_path, "other: {}\n")
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    assert any("risk" in e for e in errors)


def test_check_risk_config_content_missing_key(monkeypatch, tmp_path):
    """必須キーが欠けている場合はエラーになること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_missing_key = """
risk:
  max_position_pct: 0.20
  max_utilization: 0.80
  max_drawdown: 0.20
  rate_limit_per_sec: 5
  # circuit_breaker_errors と circuit_breaker_window_sec を省略
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_missing_key)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    assert any("circuit_breaker_errors" in e for e in errors)
    assert any("circuit_breaker_window_sec" in e for e in errors)


def test_check_risk_config_content_out_of_range(monkeypatch, tmp_path):
    """max_position_pct > max_utilization の場合はエラーになること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_bad_range = """
risk:
  max_position_pct: 0.90
  max_utilization: 0.50
  max_drawdown: 0.20
  rate_limit_per_sec: 5
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_bad_range)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    assert any("max_position_pct" in e and "max_utilization" in e for e in errors)


def test_check_risk_config_content_zero_rate_limit(monkeypatch, tmp_path):
    """rate_limit_per_sec が 0 以下の場合はエラーになること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_bad_rate = """
risk:
  max_position_pct: 0.20
  max_utilization: 0.80
  max_drawdown: 0.20
  rate_limit_per_sec: 0
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_bad_rate)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    assert any("rate_limit_per_sec" in e for e in errors)


def test_check_risk_config_content_value_out_of_01(monkeypatch, tmp_path):
    """max_drawdown が (0, 1] 範囲外の場合はエラーになること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_bad = """
risk:
  max_position_pct: 0.20
  max_utilization: 0.80
  max_drawdown: 1.5
  rate_limit_per_sec: 5
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_bad)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    assert any("max_drawdown" in e for e in errors)


def test_check_risk_config_bool_rejected_as_ratio(monkeypatch, tmp_path):
    """bool 値を比率フィールドに使った場合はエラーになること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_bool = """
risk:
  max_position_pct: true
  max_utilization: 0.80
  max_drawdown: 0.20
  rate_limit_per_sec: 5
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_bool)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    assert any("bool" in e or "max_position_pct" in e for e in errors)


def test_check_risk_config_bool_rejected_as_int(monkeypatch, tmp_path):
    """bool 値を整数フィールドに使った場合はエラーになること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_bool = """
risk:
  max_position_pct: 0.20
  max_utilization: 0.80
  max_drawdown: 0.20
  rate_limit_per_sec: true
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_bool)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    assert any("bool" in e or "rate_limit_per_sec" in e for e in errors)


def test_check_risk_config_float_for_int_rejected(monkeypatch, tmp_path):
    """小数値を整数フィールドに使った場合はエラーになること（例: 1.7）。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_float = """
risk:
  max_position_pct: 0.20
  max_utilization: 0.80
  max_drawdown: 0.20
  rate_limit_per_sec: 1.7
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_float)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    assert any("rate_limit_per_sec" in e or "小数" in e for e in errors)


def test_check_risk_config_unknown_key_warns(monkeypatch, tmp_path):
    """未知のキーが含まれている場合は警告になること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_extra = """
risk:
  max_position_pct: 0.20
  max_utilization: 0.80
  max_drawdown: 0.20
  rate_limit_per_sec: 5
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
  unknown_future_param: 999
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_extra)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, warnings, _ = validate_config.validate()
    risk_errors = [e for e in errors if "risk" in e.lower() or "max_" in e]
    assert risk_errors == [], f"想定外のエラー: {risk_errors}"
    assert any("unknown_future_param" in w for w in warnings)


def test_check_risk_config_relation_error_has_risk_prefix(monkeypatch, tmp_path):
    """max_position_pct > max_utilization のエラーメッセージに risk. 接頭辞があること。"""
    monkeypatch.setenv("JQUANTS_BULK_API_KEY", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    yaml_bad = """
risk:
  max_position_pct: 0.90
  max_utilization: 0.50
  max_drawdown: 0.20
  rate_limit_per_sec: 5
  circuit_breaker_errors: 10
  circuit_breaker_window_sec: 60
"""
    cfg_dir = _make_risk_config_dir(tmp_path, yaml_bad)
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", cfg_dir)
    errors, _, _ = validate_config.validate()
    relation_errors = [
        e for e in errors if "max_position_pct" in e and "max_utilization" in e
    ]
    assert relation_errors, "max_position_pct > max_utilization のエラーが見つからない"
    assert all("risk.max_position_pct" in e for e in relation_errors)
    assert all("risk.max_utilization" in e for e in relation_errors)


def build_sample_signals():
    return [
        {
            "code": "AAA",
            "side": "buy",
            "target_size": None,
            "target_weight": 0.1,
            "signal_rank": 1,
        },
        {
            "code": "BBB",
            "side": "sell",
            "target_size": 100,
            "target_weight": None,
            "signal_rank": 2,
        },
    ]


def test_signal_queue_report_build_and_format_and_save(tmp_path):
    signals = build_sample_signals()
    rpt = build_report(signals, report_date=date(2026, 4, 28))
    assert rpt.total_count == 2
    assert rpt.buy_count == 1
    assert rpt.status == "READY"
    # warnings should include missing target_size for buy
    assert any("target_size" in w for w in rpt.warnings)

    cli = sq_format_cli_summary(rpt)
    assert "Signal Queue Confirmation" in cli
    assert "total" in cli

    js = sq_format_json(rpt)
    parsed = json.loads(js)
    assert parsed["total_count"] == rpt.total_count

    md = sq_format_markdown(rpt)
    assert "# Signal Queue Confirmation" in md

    # save_report writes files and returns run_dir
    run_dir = sq_save_report(rpt, output_dir=tmp_path / "artifacts")
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "warnings.json").exists()

    # invalid report_date raises
    bad = rpt
    bad.report_date = "invalid-date"
    with pytest.raises(ValueError):
        sq_save_report(bad, output_dir=tmp_path / "artifacts2")
