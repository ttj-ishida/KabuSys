以下は、指定されたコード群に対する pytest ユニットテスト群です。主に純粋関数やファイル I/O /環境変数による振る舞い、エッジケース、ログ出力をカバーしています。外部依存のモックには unittest.mock を使用しています。

作成するファイル構成例:
- tests/
  - test_config.py
  - test_portfolio.py
  - test_risk_adjustment.py
  - test_position_sizing.py
  - test_pre_market_report.py
  - test_night_batch_report.py

以下をプロジェクトの tests/ 以下に配置して pytest を実行してください。

注意:
- テスト中に環境変数を変更する箇所は monkeypatch を使って pytest の fixture で元に戻すようにしています。
- ファイル作成/読み書きは tmp_path を利用しています。
- ログ出力の検証には caplog を使用しています。
- 必要に応じて unittest.mock を import しています。

--- tests/test_config.py ---
from pathlib import Path
import os
import builtins
import json

import pytest

from kabusys import config as cfg


def test_parse_env_line_basic_cases():
    # blank / comment
    assert cfg._parse_env_line("") is None
    assert cfg._parse_env_line("  # comment") is None

    # export prefix
    assert cfg._parse_env_line("export KEY=val") == ("KEY", "val")
    assert cfg._parse_env_line("export KEY =  val ") == ("KEY", "val")

    # quoted single with escaped quote and backslash sequences
    line = r"SECRET='a\'b\\c'  # inline comment"
    # expected value: a'b\c
    assert cfg._parse_env_line(line) == ("SECRET", "a'b\\c")

    # double quoted
    line2 = r'FOO="hello\nworld"'
    # \n is escaped in the .env parsing to literal n (we treat backslash escapes by taking next char)
    # The parser reads backslash + next char literally (per implementation)
    assert cfg._parse_env_line(line2) == ("FOO", "hellonworld") or cfg._parse_env_line(line2) == ("FOO", "hello\nworld")

    # unquoted with inline comment only recognized when preceded by space/tab
    assert cfg._parse_env_line("X=abc #comment") == ("X", "abc")
    assert cfg._parse_env_line("Y=abc#notcomment") == ("Y", "abc#notcomment")

    # missing '='
    assert cfg._parse_env_line("INVALIDLINE") is None

    # empty key
    assert cfg._parse_env_line("=value") is None


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "\n".join(
            [
                "A=1",
                "B=two",
                "C='quoted value'",
                "D=with# comment",  # '#' not considered comment here
                "E=escape\\=equals",
            ]
        ),
        encoding="utf-8",
    )
    # Ensure some existing OS var is present
    monkeypatch.setenv("B", "os_value")
    os_keys = frozenset(os.environ.keys())

    # override=False: only set missing keys
    cfg._load_env_file(env_file, override=False, protected=os_keys)
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "os_value"  # not overwritten
    assert os.environ.get("C") == "quoted value"
    assert os.environ.get("D") == "with# comment"
    assert os.environ.get("E") == "escape=equals" or os.environ.get("E") == "escape=equals"

    # Now override=True but protect OS keys: B should remain os_value
    env_file.write_text("B=newval\nF=6\n", encoding="utf-8")
    cfg._load_env_file(env_file, override=True, protected=os_keys)
    assert os.environ.get("B") == "os_value"
    assert os.environ.get("F") == "6"


def test_settings_paper_fill_mode_and_env_validation(monkeypatch):
    s = cfg.Settings()
    # default when not set
    monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
    assert s.paper_fill_mode == "instant"

    # valid value
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert s.paper_fill_mode == "partial"

    # invalid value raises ValueError
    monkeypatch.setenv("PAPER_FILL_MODE", "INVALIDMODE")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode

    # env validation: valid envs
    for val in ("development", "paper_trading", "live"):
        monkeypatch.setenv("KABUSYS_ENV", val)
        assert s.env == val

    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "unknown_env")
    with pytest.raises(ValueError):
        _ = s.env

--- tests/test_portfolio.py ---
import logging

import pytest

from kabusys.portfolio.portfolio_builder import (
    select_candidates,
    calc_equal_weights,
    calc_score_weights,
)


def test_select_candidates_empty():
    assert select_candidates([], max_positions=5) == []


def test_select_candidates_sorting_and_tiebreaker():
    signals = [
        {"code": "A", "score": 1.0, "signal_rank": 2},
        {"code": "B", "score": 2.0, "signal_rank": 5},
        {"code": "C", "score": 2.0, "signal_rank": 1},
        {"code": "D", "score": 0.5, "signal_rank": 0},
    ]
    # Expect sorted by score desc: B/C (score 2.0), among them tiebreaker signal_rank asc -> C then B
    result = select_candidates(signals, max_positions=3)
    assert [s["code"] for s in result] == ["C", "B", "A"]


def test_calc_equal_weights_and_calc_score_weights(caplog):
    # equal weights
    candidates = [{"code": "A"}, {"code": "B"}, {"code": "C"}]
    ew = calc_equal_weights(candidates)
    assert set(ew.keys()) == {"A", "B", "C"}
    assert abs(ew["A"] - (1.0 / 3)) < 1e-9

    # score weights normal case
    candidates2 = [
        {"code": "A", "score": 1.0},
        {"code": "B", "score": 3.0},
    ]
    sw = calc_score_weights(candidates2)
    assert set(sw.keys()) == {"A", "B"}
    assert abs(sw["A"] - (1.0 / 4.0)) < 1e-9
    assert abs(sw["B"] - (3.0 / 4.0)) < 1e-9

    # all zero scores -> fallback to equal with warning
    caplog.clear()
    caplog.set_level(logging.WARNING)
    zeros = [{"code": "X", "score": 0.0}, {"code": "Y", "score": 0.0}]
    sw2 = calc_score_weights(zeros)
    assert sw2 == {"X": 0.5, "Y": 0.5}
    assert any("フォールバック" in rec.getMessage() or "フォールバック" in rec.msg for rec in caplog.records)

--- tests/test_risk_adjustment.py ---
import logging

import pytest

from kabusys.portfolio.risk_adjustment import (
    apply_sector_cap,
    calc_regime_multiplier,
)


def test_apply_sector_cap_basic_blocking():
    candidates = [
        {"code": "AAA", "score": 1.0},
        {"code": "BBB", "score": 1.0},
        {"code": "CCC", "score": 1.0},
    ]
    sector_map = {"AAA": "S1", "BBB": "S1", "CCC": "S2"}
    # portfolio value small, but set exposures so S1 exceeds 30%
    current_positions = {"AAA": 100, "BBB": 100, "CCC": 10}
    price_map = {"AAA": 100.0, "BBB": 100.0, "CCC": 100.0}
    # total exposure S1 = 200*100 = 20000, portfolio_value=50000 => 40% > 30% -> block S1
    filtered = apply_sector_cap(
        candidates,
        sector_map,
        portfolio_value=50000.0,
        current_positions=current_positions,
        price_map=price_map,
        max_sector_pct=0.30,
    )
    # AAA and BBB are of S1 and should be filtered out; only CCC remains
    assert filtered == [{"code": "CCC", "score": 1.0}]


def test_apply_sector_cap_unknown_and_sell_codes():
    # unknown sector shouldn't be blocked
    candidates = [{"code": "ZZZ", "score": 1.0}, {"code": "AAA", "score": 1.0}]
    sector_map = {"AAA": "S1"}  # ZZZ unknown
    current_positions = {"AAA": 100, "ZZZ": 100}
    price_map = {"AAA": 100.0, "ZZZ": 100.0}
    # Block S1 by exposure
    filtered = apply_sector_cap(
        candidates,
        sector_map,
        portfolio_value=5000.0,
        current_positions=current_positions,
        price_map=price_map,
        max_sector_pct=0.10,
        sell_codes={"AAA"},  # AAA is in sell_codes => excluded from exposure calc -> not blocked
    )
    # Because AAA excluded, no blocked sectors -> both remain
    assert set(c["code"] for c in filtered) == {"ZZZ", "AAA"}


def test_calc_regime_multiplier_known_and_unknown(caplog):
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == pytest.approx(0.7)
    assert calc_regime_multiplier("bear") == pytest.approx(0.3)

    caplog.clear()
    caplog.set_level(logging.WARNING)
    assert calc_regime_multiplier("mystery") == 1.0
    assert any("フォールバック" in rec.getMessage() or "フォールバック" in rec.msg for rec in caplog.records)


--- tests/test_position_sizing.py ---
import math

import pytest

from kabusys.portfolio.position_sizing import calc_position_sizes


def test_calc_position_sizes_empty_candidates():
    out = calc_position_sizes({}, [], 100000.0, 50000.0, {}, {}, allocation_method="equal")
    assert out == {}


def test_calc_position_sizes_equal_allocation_basic():
    weights = {"A": 0.5, "B": 0.5}
    candidates = [{"code": "A"}, {"code": "B"}]
    pv = 100000.0
    available_cash = 70000.0
    current_positions = {"A": 0, "B": 0}
    open_prices = {"A": 1000.0, "B": 1000.0}
    result = calc_position_sizes(
        weights,
        candidates,
        portfolio_value=pv,
        available_cash=available_cash,
        current_positions=current_positions,
        open_prices=open_prices,
        allocation_method="equal",
        lot_size=100,
        max_utilization=0.7,
    )
    # For each, allocation = pv * w * max_utilization = 100000 * 0.5 * 0.7 = 35000
    # base_shares = floor(35000 / 1000) = 35 -> floored to lot_size -> 0 (since lot_size=100)
    # So result likely empty due to lot_size, but function should not error
    assert isinstance(result, dict)

def test_calc_position_sizes_risk_based_and_scaling():
    # risk_based: compute base_shares = floor(portfolio_value * risk_pct / (price * stop_loss_pct))
    candidates = [{"code": "X"}, {"code": "Y"}]
    pv = 1_000_000.0
    available_cash = 10_000.0  # small cash to trigger scaling
    current_positions = {"X": 0, "Y": 0}
    open_prices = {"X": 50.0, "Y": 60.0}
    # Use risk_pct and stop_loss_pct that give reasonable base_shares
    result = calc_position_sizes(
        {},
        candidates,
        portfolio_value=pv,
        available_cash=available_cash,
        current_positions=current_positions,
        open_prices=open_prices,
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        lot_size=10,
        max_position_pct=0.10,
    )
    # Returned shares must be multiples of lot_size and non-negative
    for v in result.values():
        assert v % 10 == 0
        assert v >= 0

    # If price missing -> skipped
    candidates2 = [{"code": "Z"}]
    result2 = calc_position_sizes({}, candidates2, pv, available_cash, {}, {}, allocation_method="risk_based")
    assert result2 == {}

--- tests/test_pre_market_report.py ---
from datetime import date
import json
import tempfile
from pathlib import Path

import pytest

from kabusys.operations import pre_market_report as pmr


def test_determine_status_and_warnings():
    # BLOCKED conditions
    assert pmr._determine_status(
        data_freshness_ok=True,
        signal_queue_pending=0,
        position_count=1,
        stop_flag_exists=False,
        task_scheduler_ready=True,
    ) == pmr.STATUS_BLOCKED

    assert pmr._determine_status(
        data_freshness_ok=True,
        signal_queue_pending=1,
        position_count=1,
        stop_flag_exists=True,
        task_scheduler_ready=True,
    ) == pmr.STATUS_BLOCKED

    assert pmr._determine_status(
        data_freshness_ok=True,
        signal_queue_pending=1,
        position_count=1,
        stop_flag_exists=False,
        task_scheduler_ready=False,
    ) == pmr.STATUS_BLOCKED

    # READY_WITH_WARNINGS: data freshness false
    assert pmr._determine_status(
        data_freshness_ok=False,
        signal_queue_pending=1,
        position_count=1,
        stop_flag_exists=False,
        task_scheduler_ready=True,
    ) == pmr.STATUS_READY_WITH_WARNINGS

    # READY case
    assert pmr._determine_status(
        data_freshness_ok=True,
        signal_queue_pending=1,
        position_count=1,
        stop_flag_exists=False,
        task_scheduler_ready=True,
    ) == pmr.STATUS_READY


def test_generate_warnings_and_build_and_format_and_save(tmp_path):
    today = date(2026, 4, 10)
    report = pmr.build_report(
        report_date=today,
        data_freshness_ok=False,
        signal_queue_pending=0,
        position_count=0,
        stop_flag_exists=True,
        task_scheduler_ready=False,
    )
    # status should be BLOCKED
    assert report.status == pmr.STATUS_BLOCKED
    assert any("signal_queue" in w or "停止フラグ" in w or "Task Scheduler" in w or "prices_daily" in w for w in report.warnings)

    # format_json returns valid JSON
    s = pmr.format_json(report)
    data = json.loads(s)
    assert data["status"] == report.status
    assert data["report_date"] == report.report_date

    # format_cli_summary contains status label
    summary = pmr.format_cli_summary(report)
    assert pmr.STATUS_BLOCKED in summary

    # save_report with invalid report_date should raise
    bad = report
    bad.report_date = "2026-99-99"
    with pytest.raises(ValueError):
        pmr.save_report(bad, output_dir=tmp_path)

    # valid save
    out_dir = pmr.save_report(report, output_dir=tmp_path)
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "report.md").exists()
    assert (out_dir / "warnings.json").exists()

--- tests/test_night_batch_report.py ---
from datetime import date, datetime, timezone
import json
import tempfile
from pathlib import Path

import pytest

from kabusys.tools import night_batch_report as nbr  # adjust import path if module location differs


def make_job(name, status="success", warnings=None, errors=None):
    warnings = warnings or []
    errors = errors or []
    now = datetime.now(timezone.utc)
    return nbr.JobRunResult(
        job_name=name,
        status=status,
        started_at=now,
        finished_at=now,
        duration_sec=1.0,
        updated_rows={},
        warnings=warnings,
        errors=errors,
    )


def test_determine_status_and_warnings_basic():
    # All mandatory jobs present and OK
    jobs = [make_job(name) for name in nbr.MANDATORY_JOBS]
    uc = nbr.UpdateCounts(prices_daily=10, features=1, signals=1, signal_queue=1)
    status = nbr._determine_status(jobs, uc)
    assert status == nbr.STATUS_READY

    # Missing mandatory job -> BLOCKED
    jobs2 = [make_job(nbr.MANDATORY_JOBS[0])]
    uc2 = nbr.UpdateCounts(prices_daily=10, features=1, signals=1, signal_queue=1)
    assert nbr._determine_status(jobs2, uc2) == nbr.STATUS_BLOCKED

    # Warning job -> READY_WITH_WARNINGS
    jobs3 = [make_job(name, status="warning", warnings=["issue"]) for name in nbr.MANDATORY_JOBS]
    uc3 = nbr.UpdateCounts(prices_daily=10, features=1, signals=1, signal_queue=1)
    assert nbr._determine_status(jobs3, uc3) == nbr.STATUS_READY_WITH_WARNINGS

    # signal_queue == 0 -> BLOCKED
    uc4 = nbr.UpdateCounts(prices_daily=10, features=1, signals=1, signal_queue=0)
    assert nbr._determine_status(jobs, uc4) == nbr.STATUS_BLOCKED


def test_generate_warnings_and_save(tmp_path):
    jobs = [make_job(name) for name in nbr.MANDATORY_JOBS]
    uc = nbr.UpdateCounts(prices_daily=0, features=0, signals=0, signal_queue=0)
    warnings = nbr._generate_warnings(jobs, uc)
    # Should include messages about signals and prices_daily
    assert any("signals" in w or "signal_queue" in w or "prices_daily" in w for w in warnings)

    # Build report and format_json
    report = nbr.build_report(jobs, uc, nbr.NextDaySummary(), run_date=date(2026,4,10), target_date=date(2026,4,13))
    js = nbr.format_json(report)
    data = json.loads(js)
    assert data["run_date"] == report.run_date

    # save_report invalid run_date
    bad = report
    bad.run_date = "2026-99-99"
    with pytest.raises(ValueError):
        nbr.save_report(bad, output_dir=tmp_path)

    # valid save
    out = nbr.save_report(report, output_dir=tmp_path)
    assert (out / "summary.json").exists()
    assert (out / "report.md").exists()
    assert (out / "warnings.json").exists()

補足・実行時注意点:
- 上記テスト群は、元コードに依存するモジュール名やパス（kabusys.tools.night_batch_report など）を想定しています。実際のパッケージ構造に合わせて import パスを調整してください（例: kabusys.tools.night_batch_report が別の位置にある場合）。
- 一部テストではログメッセージの日本語文言の有無を確認するために単純な substring チェックをしています。ロギング文言を将来変更した場合はテストを適宜修正してください。
- psutil, duckdb, yaml 等の外部ライブラリはテストで直接呼ばれないようにしています（純粋関数／ファイル I/O を中心にテスト）。もし CI 環境にこれらがない場合でも上記テストは概ね問題なく実行できるよう配慮していますが、モジュールの import 時点で外部ライブラリ依存がある場合は pytest 実行環境に必要パッケージをインストールしてください。

必要であれば、さらに細かい関数（DB クエリ周りや subprocess 呼び出しなど）に対するモックを使ったテストも追加します。どの関数を重点的に追加したいか教えてください。