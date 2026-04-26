以下に、提示されたコード群に対する pytest ユニットテスト群を用意しました。主要な関数の正常系・異常系（エッジケース）をカバーし、外部依存（ファイル I/O / 環境変数 / psutil / OpenAI 相当）は unittest.mock を用いて差し替えています。テストは pytest を前提とします。

ファイル配置例:
- tests/
  - test_run_monitoring.py
  - test_run_execution.py
  - test_config.py
  - test_validate_config.py
  - test_config_setup.py
  - test_paper_verification_report.py
  - test_portfolio_builder.py
  - test_risk_adjustment.py
  - test_position_sizing.py
  - test_utils_logging_and_process.py

必要に応じてプロジェクトのルートに pytest.ini を配置してください（任意）。

各テストファイルの内容は以下のとおりです。適宜プロジェクト構成に合わせてパスを調整してください（tests ディレクトリ直下から kabusys パッケージを import できることを想定しています）。

---------------------------
tests/test_run_monitoring.py
---------------------------
from unittest import mock
import os
import logging

import pytest

from kabusys.run_monitoring import _get_poll_interval


def test_get_poll_interval_default(monkeypatch, caplog):
    # 環境変数未設定ならデフォルト
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    caplog.set_level(logging.WARNING)
    val = _get_poll_interval()
    assert isinstance(val, int)
    assert val == 60


def test_get_poll_interval_valid(monkeypatch):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "10")
    assert _get_poll_interval() == 10


def test_get_poll_interval_invalid_value(monkeypatch, caplog):
    # 非数値 -> デフォルトにフォールバック、警告ログ
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "invalid")
    caplog.set_level(logging.WARNING)
    val = _get_poll_interval()
    assert val == 60
    assert any("MONITOR_POLL_INTERVAL の値が不正" in rec.getMessage() for rec in caplog.records)


def test_get_poll_interval_zero_or_negative(monkeypatch, caplog):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    caplog.set_level(logging.WARNING)
    val = _get_poll_interval()
    assert val == 60
    assert any("MONITOR_POLL_INTERVAL の値が不正" in rec.getMessage() for rec in caplog.records)

---------------------------
tests/test_run_execution.py
---------------------------
from pathlib import Path
import yaml
import tempfile
from types import SimpleNamespace
import pytest
from kabusys.run_execution import _load_risk_config, _pos_value


def make_temp_yaml(tmp_path, data):
    p = tmp_path / "risk_config.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return p


def test_load_risk_config_success(tmp_path):
    data = {
        "risk": {
            "max_position_pct": 0.1,
            "max_utilization": 0.5,
            "rate_limit_per_sec": 5,
            "circuit_breaker_errors": 10,
            "circuit_breaker_window_sec": 60,
            "max_drawdown": 0.2,
        }
    }
    path = make_temp_yaml(tmp_path, data)
    cfg = _load_risk_config(Path(path), initial_portfolio_value=1_000_000.0)
    # 属性値を粗く確認（型と一部の値）
    assert hasattr(cfg, "max_position_pct")
    assert cfg.max_position_pct == pytest.approx(0.1)
    assert cfg.initial_portfolio_value == pytest.approx(1_000_000.0)


def test_load_risk_config_missing_file(tmp_path):
    p = tmp_path / "no_such_file.yaml"
    with pytest.raises(FileNotFoundError):
        _load_risk_config(p, initial_portfolio_value=100.0)


def test_load_risk_config_bad_yaml(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("::: not yaml :::", encoding="utf-8")
    with pytest.raises(ValueError):
        _load_risk_config(Path(p), initial_portfolio_value=100.0)


def test_pos_value_uses_current_if_positive():
    p = SimpleNamespace(code="0001", current_price=200.0, avg_price=100.0, qty=3)
    assert _pos_value(p) == pytest.approx(3 * 200.0)


def test_pos_value_falls_back_to_avg():
    p = SimpleNamespace(code="0002", current_price=None, avg_price=50.0, qty=4)
    assert _pos_value(p) == pytest.approx(4 * 50.0)


def test_pos_value_zero_or_invalid_logs_warning(caplog):
    caplog.set_level("WARNING")
    p = SimpleNamespace(code="0003", current_price=0.0, avg_price=None, qty=5)
    assert _pos_value(p) == 0.0
    assert any("ポジション評価額を 0 として扱います" in rec.getMessage() for rec in caplog.records)

---------------------------
tests/test_config.py
---------------------------
import os
from pathlib import Path
from unittest import mock
import pytest

from kabusys.config import _parse_env_line, _load_env_file, Settings


def test_parse_env_line_comments_and_blank():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    assert _parse_env_line("KEY=val") == ("KEY", "val")


def test_parse_env_line_export_format():
    assert _parse_env_line("export FOO=bar") == ("FOO", "bar")


def test_parse_env_line_quoted_and_escaped():
    # シングルクォート内のエスケープ処理
    line = r"SECRET='ab\'c\\d'"
    res = _parse_env_line(line)
    assert res == ("SECRET", "ab'c\\d")
    # ダブルクォート
    line2 = r'VAL="x\"y"'
    res2 = _parse_env_line(line2)
    assert res2 == ("VAL", 'x"y')


def test_parse_env_line_unquoted_with_inline_comment():
    assert _parse_env_line("A=hello # comment") == ("A", "hello")
    # シャープが文字列中（スペースなし）ならコメントとみなさない
    assert _parse_env_line("B=hello#notcomment") == ("B", "hello#notcomment")


def test_load_env_file_sets_env_vars(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("X=1\nY=two\n", encoding="utf-8")
    # start with empty env for these keys
    monkeypatch.delenv("X", raising=False)
    monkeypatch.delenv("Y", raising=False)
    _load_env_file(Path(p), override=False, protected=frozenset())
    assert os.environ.get("X") == "1"
    assert os.environ.get("Y") == "two"


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("X=1\nY=2\n", encoding="utf-8")
    # simulate existing OS env protected keys
    monkeypatch.setenv("Y", "original")
    protected = frozenset(os.environ.keys())
    # override=True but protected prevents overwriting Y
    _load_env_file(Path(p), override=True, protected=protected)
    assert os.environ.get("X") == "1"
    assert os.environ.get("Y") == "original"


def test_settings_env_validation(monkeypatch):
    monkeypatch.setenv("KABUSYS_ENV", "development")
    s = Settings()
    assert s.env == "development"
    # invalid env raises
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = Settings().env


def test_settings_paper_fill_mode_valid_and_invalid(monkeypatch):
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert Settings().paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "invalid_mode")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode

---------------------------
tests/test_validate_config.py
---------------------------
import os
from kabusys import validate_config
import pytest


def test_validate_missing_required_vars(monkeypatch):
    # ensure required vars are unset
    for v in ("JQUANTS_REFRESH_TOKEN", "KABU_API_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    errs, warns, infos = validate_config.validate()
    assert any("必須環境変数が未設定です" in e for e in errs)


def test_validate_env_and_log_level(monkeypatch):
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "token")
    monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
    monkeypatch.setenv("KABUSYS_ENV", "live")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    errs, warns, infos = validate_config.validate()
    # live produces a warning
    assert any("KABUSYS_ENV=live" in w or "本番環境" in w for w in warns) or any("KABUSYS_ENV: live" in i for i in infos)

---------------------------
tests/test_config_setup.py
---------------------------
from pathlib import Path
import tempfile
from kabusys import config_setup
import pytest


def test_read_write_env(tmp_path):
    p = tmp_path / ".env.test"
    values = {
        "JQUANTS_REFRESH_TOKEN": "tok",
        "JQUANTS_BULK_API_KEY": "bulk",
        "KABU_API_PASSWORD": "pwd",
        "KABU_API_BASE_URL": "http://example",
        "KABUSYS_ENV": "development",
        "LOG_LEVEL": "INFO",
        "KILL_FLAG_CLEAR_ON_START": "0",
    }
    config_setup._write_env(p, values)
    read = config_setup._read_env(p)
    # written keys should be readable (note: values written may include defaults)
    assert read.get("KABU_API_PASSWORD") == values["KABU_API_PASSWORD"]
    assert read.get("KABUSYS_ENV") == values["KABUSYS_ENV"]

---------------------------
tests/test_paper_verification_report.py
---------------------------
import math
from kabusys.tools.paper_verification_report import _p95, _build_date_filter, _fmt_float, _fmt_int


def test_p95_empty():
    assert _p95([]) is None


def test_p95_single_and_multiple():
    assert _p95([5.0]) == 5.0
    vals = list(range(1, 101))  # 1..100
    p95 = _p95(vals)
    # 95th percentile index as implemented (ceil(100*0.95)-1 = 95-1 = 94) => value 95
    assert p95 == 95


def test_build_date_filter_combinations():
    clause, params = _build_date_filter("ts", None, None)
    assert clause == "" and params == []
    clause, params = _build_date_filter("ts", "2020-01-01", None)
    assert "ts >= ?" in clause and params == ["2020-01-01"]
    clause, params = _build_date_filter("ts", None, "2020-01-02")
    assert "ts <= ?" in clause and params == ["2020-01-02"]
    clause, params = _build_date_filter("ts", "a", "b")
    assert "AND" in clause and params == ["a", "b"]


def test_fmt_helpers():
    assert _fmt_float(None) == "N/A"
    assert _fmt_float(1.2345, 2, " %") == "1.23 %"
    assert _fmt_int(None) == "N/A"
    assert _fmt_int(5) == "5"

---------------------------
tests/test_portfolio_builder.py
---------------------------
from kabusys.portfolio.portfolio_builder import select_candidates, calc_equal_weights, calc_score_weights
import pytest


def test_select_candidates_sorting_and_limit():
    signals = [
        {"code": "A", "score": 1.0, "signal_rank": 2},
        {"code": "B", "score": 2.0, "signal_rank": 1},
        {"code": "C", "score": 2.0, "signal_rank": 0},
    ]
    res = select_candidates(signals, max_positions=2)
    # score desc: B and C tie; tie-breaker signal_rank ascending -> C then B but top 2 -> C, B
    assert [s["code"] for s in res] == ["C", "B"]


def test_calc_equal_weights_and_score_weights():
    candidates = [{"code": "A", "score": 0.0}, {"code": "B", "score": 0.0}]
    ew = calc_equal_weights(candidates)
    assert ew == {"A": 0.5, "B": 0.5}
    # all-zero scores -> fallback to equal weights with warning
    sw = calc_score_weights(candidates)
    assert sw == ew


def test_calc_score_weights_normal():
    candidates = [{"code": "A", "score": 1.0}, {"code": "B", "score": 3.0}]
    sw = calc_score_weights(candidates)
    assert pytest.approx(sw["A"] + sw["B"]) == 1.0
    assert sw["B"] > sw["A"]

---------------------------
tests/test_risk_adjustment.py
---------------------------
from kabusys.portfolio.risk_adjustment import apply_sector_cap, calc_regime_multiplier


def test_apply_sector_cap_blocks_overexposed_sector():
    candidates = [{"code": "AAA", "score": 1, "signal_rank": 0}, {"code": "BBB", "score": 1, "signal_rank": 0}]
    sector_map = {"AAA": "S1", "BBB": "S2"}
    portfolio_value = 1000.0
    # current positions: S1 has high exposure
    current_positions = {"AAA": 10, "BBB": 1}
    price_map = {"AAA": 100.0, "BBB": 10.0}
    filtered = apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, max_sector_pct=0.5)
    # sector S1 exposure = 10*100=1000 -> 1000/1000 == 1.0 >= 0.5 -> AAA should be excluded
    assert all(c["code"] != "AAA" for c in filtered)
    assert any(c["code"] == "BBB" for c in filtered)


def test_calc_regime_multiplier_known_and_unknown(caplog):
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == pytest.approx(0.7)
    caplog.set_level("WARNING")
    # unknown regime logs warning and returns 1.0
    assert calc_regime_multiplier("weird") == 1.0
    assert any("未知のレジーム" in r.getMessage() for r in caplog.records)

---------------------------
tests/test_position_sizing.py
---------------------------
from kabusys.portfolio.position_sizing import calc_position_sizes
import pytest


def test_calc_position_sizes_empty_candidates():
    out = calc_position_sizes({}, [], 1000, 1000, {}, {}, allocation_method="equal")
    assert out == {}


def test_calc_position_sizes_equal_and_lot_rounding():
    candidates = [{"code": "AAA"}]
    weights = {"AAA": 1.0}
    open_prices = {"AAA": 123.45}
    # high portfolio so target_shares large but rounded to lot 100 and _max_per_stock may cap
    out = calc_position_sizes(weights, candidates, portfolio_value=1_000_000, available_cash=1_000_000, current_positions={}, open_prices=open_prices, allocation_method="equal", lot_size=100)
    # shares must be a multiple of lot_size or empty
    for v in out.values():
        assert v % 100 == 0


def test_calc_position_sizes_risk_based_skips_invalid_price(caplog):
    candidates = [{"code": "C"}]
    out = calc_position_sizes({}, candidates, portfolio_value=1000000, available_cash=1000000, current_positions={}, open_prices={"C": 0}, allocation_method="risk_based")
    assert out == {}


def test_calc_position_sizes_scaling_by_available_cash():
    candidates = [{"code": "A"}, {"code": "B"}]
    weights = {"A": 0.5, "B": 0.5}
    open_prices = {"A": 100.0, "B": 100.0}
    # set available_cash smaller than required to force scaling
    out = calc_position_sizes(weights, candidates, portfolio_value=1000000, available_cash=5000, current_positions={}, open_prices=open_prices, allocation_method="equal", lot_size=1)
    # should return integer shares (maybe empty or reduced)
    assert isinstance(out, dict)
    for v in out.values():
        assert isinstance(v, int)


---------------------------
tests/test_utils_logging_and_process.py
---------------------------
import logging
import os
from pathlib import Path
from unittest import mock

import pytest

from kabusys.utils.logging_setup import setup_logging
from kabusys.utils import process_priority


def test_setup_logging_creates_handlers(tmp_path, capsys):
    # create a directory
    log_dir = tmp_path / "logs"
    setup_logging(app_name="testapp", log_dir=log_dir, level="DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    # must contain at least one handler (StreamHandler)
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)


def test_setup_logging_dir_creation_failure(monkeypatch, capsys):
    # force mkdir to fail
    def fake_mkdir(*args, **kwargs):
        raise OSError("no perms")
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    # call and ensure it doesn't raise
    setup_logging(app_name="testapp2", log_dir=Path("/unlikely/path"), level="INFO")
    # should at least have StreamHandler
    root = logging.getLogger()
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)


def test_set_process_priority_invalid_level():
    with pytest.raises(ValueError):
        process_priority.set_process_priority("invalid_level")


def test_set_process_priority_calls_psutil(monkeypatch):
    # mock psutil.Process with nice method
    fake = mock.MagicMock()
    fake.pid = 1234
    fake.nice = mock.MagicMock()
    monkeypatch.setattr("kabusys.utils.process_priority.psutil.Process", lambda: fake)
    monkeypatch.setattr("kabusys.utils.process_priority.platform.system", lambda: "Linux")
    # should not raise
    process_priority.set_process_priority("high")
    # Linux -> called nice with _LINUX_NICE["high"] (-10)
    # We cannot import _LINUX_NICE here, but ensure nice called once
    assert fake.nice.call_count == 1


def test_set_cpu_affinity_invalid_and_none(monkeypatch):
    fake = mock.MagicMock()
    fake.pid = 1
    fake.cpu_affinity = mock.MagicMock()
    monkeypatch.setattr("kabusys.utils.process_priority.psutil.Process", lambda: fake)
    # None -> no-op
    process_priority.set_cpu_affinity(None)
    # invalid value (<1) raises
    with pytest.raises(ValueError):
        process_priority.set_cpu_affinity(0)
    # valid sets cpu_affinity (mock psutil.cpu_count)
    monkeypatch.setattr("kabusys.utils.process_priority.psutil.cpu_count", lambda: 4)
    process_priority.set_cpu_affinity(2)
    assert fake.cpu_affinity.call_count == 1

# End of tests

注意事項・補足:
- 上記テスト群はプロジェクトのルートから pytest を実行することを想定しています（kabusys パッケージが import 可能であること）。
- テストでは一部外部モジュール（psutil、yaml、duckdb、openai 等）を実際には使わない / モックしているため、テスト実行にあたって必須でない場合があります。もしテスト実行環境に実際のモジュールが無く import エラーになる場合は、pytest 実行時に PYTHONPATH をプロジェクトに合わせるか、必要モジュールをインストールしてください。
- OpenAI 呼び出しや duckdb を直接コールする重い処理はテストでモックする想定です（ここでは該当関数のユニットテストを中心に作成しています）。score_news や regime_detector のような外部 API を呼ぶ実装のユニットテストを追加する場合は、_call_openai_api を patch してレスポンスをシミュレートしてください。
- もし特定の関数のみテストが必要であれば（あるいはテストをもっと絞ってほしい場合は）対象箇所を教えてください。テストの粒度を調整して再作成します。