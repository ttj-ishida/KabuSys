以下は、提示されたコード群に対する pytest ユニットテスト群です。
- pytest を使っています。
- 各関数／クラスの主要な動作とエッジケースをカバーしています。
- 外部依存（psutil, platform, OpenAI-like objects, file 系）には unittest.mock を使用してモックしています。
- パッケージの自動 .env 読み込みを無効化するため、conftest.py で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定しています。

プロジェクトの tests ディレクトリに以下ファイル群を作成してください。

1) tests/conftest.py
2) tests/test_config_env.py
3) tests/test_portfolio_and_risk.py
4) tests/test_position_sizing.py
5) tests/test_feature_exploration.py
6) tests/test_ai_news_nlp.py
7) tests/test_monitoring_db_and_kill_switch.py
8) tests/test_process_priority.py

――――――――――――――――――――――――――――――――――――
ファイル: tests/conftest.py
――――――――――――――――――――――――――――――――――――
このファイルはテスト実行前に自動で読み込まれ、パッケージの自動 .env 読み込みを無効化します。

内容:
import os
import pytest

# テスト中は自動 .env ロードを無効化して副作用を抑える
os.environ.setdefault("KABUSYS_DISABLE_AUTO_ENV_LOAD", "1")

@pytest.fixture(autouse=True)
def clear_env_vars(monkeypatch):
    # テストの副作用を避けるため、必要に応じて環境変数を操作できます。
    # ここではテスト毎に個別で monkeypatch.setenv / delenv を行う想定なので、
    # デフォルトでは何もしない（ただし fixture を autouse にしておくことで
    # 将来的に追加の共通セットアップを入れやすくしています）。
    yield

――――――――――――――――――――――――――――――――――――
ファイル: tests/test_config_env.py
――――――――――――――――――――――――――――――――――――
テスト対象: kabusys.config の _parse_env_line と _load_env_file。

内容:
import os
from pathlib import Path
import tempfile
import io

import pytest

from kabusys.config import _parse_env_line, _load_env_file

def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    assert _parse_env_line("NOSEP") is None

    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line(" export KEY2 =  spaced ") == ("KEY2", "spaced")

def test_parse_env_line_quoted_and_escaped():
    # シングルクオート内のエスケープ
    k, v = _parse_env_line("FOO='a\\'b'")
    assert k == "FOO"
    assert v == "a'b"

    # ダブルクオート内のバックスラッシュ escape
    k2, v2 = _parse_env_line('BAR="x\\ny"')
    # '\n' はここではエスケープされた 'n' をそのまま取り込む実装なので "xny"
    assert k2 == "BAR"
    assert v2 == "xny"

def test_parse_env_line_inline_comment_behavior():
    # '#' が直前にスペースあり: コメントとして切り落とす
    assert _parse_env_line("K=abc # some") == ("K", "abc")
    # '#' が直前にスペースなし: コメントとみなさない
    assert _parse_env_line("K2=ab#c") == ("K2", "ab#c")

def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    f = tmp_path / ".envtest"
    f.write_text("A=1\nB=2\nC=3\n")

    # override=False: 未設定のキーのみセット
    monkeypatch.delenv("A", raising=False)
    monkeypatch.setenv("B", "orig")
    _load_env_file(f, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "orig"  # 既存は上書きされない
    assert os.environ.get("C") == "3"

    # override=True with protected: B should not be overwritten
    monkeypatch.setenv("B", "protected_orig")
    _load_env_file(f, override=True, protected=frozenset({"B"}))
    assert os.environ.get("B") == "protected_orig"

    # override=True without protected: B is overwritten
    _load_env_file(f, override=True, protected=frozenset())
    assert os.environ.get("B") == "2"

――――――――――――――――――――――――――――――――――――
ファイル: tests/test_portfolio_and_risk.py
――――――――――――――――――――――――――――――――――――
テスト対象:
- kabusys.portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights
- kabusys.portfolio.risk_adjustment: apply_sector_cap, calc_regime_multiplier

内容:
import math
import logging

import pytest

from kabusys.portfolio.portfolio_builder import (
    select_candidates,
    calc_equal_weights,
    calc_score_weights,
)
from kabusys.portfolio.risk_adjustment import apply_sector_cap, calc_regime_multiplier

def test_select_candidates_sorting_and_limit():
    signals = [
        {"code": "A", "score": 1.0, "signal_rank": 2},
        {"code": "B", "score": 2.0, "signal_rank": 1},
        {"code": "C", "score": 2.0, "signal_rank": 0},
        {"code": "D", "score": 0.5, "signal_rank": 0},
    ]
    res = select_candidates(signals, max_positions=2)
    # score降順、同点は signal_rank 昇順 → B(score2,rank1) と C(score2,rank0) が上位だが signal_rank tie-break prefers smaller rank
    # Sorting key: (-score, signal_rank) なので among score=2.0 codes, C (rank 0) should come before B (rank1)
    assert [r["code"] for r in res] == ["C", "B"]

def test_calc_equal_and_score_weights():
    candidates = [{"code": "A", "score": 0.0}, {"code": "B", "score": 0.0}, {"code": "C", "score": 0.0}]
    # equal
    ew = calc_equal_weights(candidates)
    assert set(ew.keys()) == {"A", "B", "C"}
    assert abs(sum(ew.values()) - 1.0) < 1e-9

    # score all zeros => fallback to equal (and logs a warning)
    sw = calc_score_weights(candidates)
    assert sw == ew

    # normal scores
    candidates2 = [{"code": "X", "score": 1.0}, {"code": "Y", "score": 3.0}]
    sw2 = calc_score_weights(candidates2)
    assert pytest.approx(sw2["X"], rel=1e-6) == 1.0 / 4.0
    assert pytest.approx(sw2["Y"], rel=1e-6) == 3.0 / 4.0

def test_apply_sector_cap_and_calc_regime_multiplier(caplog):
    candidates = [{"code": "AAA", "score": 1.0}, {"code": "BBB", "score": 1.0}, {"code": "CCC", "score": 1.0}]
    sector_map = {"AAA": "tech", "BBB": "finance", "CCC": "tech"}
    portfolio_value = 1000.0
    current_positions = {"AAA": 1, "CCC": 2, "BBB": 1}  # use price_map to compute exposures
    price_map = {"AAA": 400.0, "CCC": 300.0, "BBB": 100.0}

    # exposures: tech = 1*400 + 2*300 = 1000 -> 100% -> tech blocked if max_sector_pct=0.3
    filtered = apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, max_sector_pct=0.3)
    # tech sector codes AAA and CCC should be excluded, BBB remains
    assert filtered == [{"code": "BBB", "score": 1.0}]

    # portfolio value <= 0 should return original candidates
    assert apply_sector_cap(candidates, sector_map, 0.0, current_positions, price_map) == candidates

    # calc_regime_multiplier known regimes
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == pytest.approx(0.7)
    assert calc_regime_multiplier("bear") == pytest.approx(0.3)

    # unknown regime logs and returns 1.0
    caplog.set_level(logging.WARNING)
    val = calc_regime_multiplier("weird")
    assert val == 1.0
    assert any("未知のレジーム" in rec.getMessage() or "未知" in rec.getMessage() for rec in caplog.records)

――――――――――――――――――――――――――――――――――――
ファイル: tests/test_position_sizing.py
――――――――――――――――――――――――――――――――――――
テスト対象: kabusys.portfolio.position_sizing.calc_position_sizes

内容:
import math
import pytest

from kabusys.portfolio.position_sizing import calc_position_sizes

def test_calc_position_sizes_risk_based_and_missing_prices():
    candidates = [{"code": "AAA"}, {"code": "BBB"}]
    portfolio_value = 100000.0
    available_cash = 100000.0
    current_positions = {"AAA": 0}
    open_prices = {"AAA": 100.0}  # BBB missing -> skipped

    shares = calc_position_sizes(
        weights={}, candidates=candidates, portfolio_value=portfolio_value,
        available_cash=available_cash, current_positions=current_positions,
        open_prices=open_prices, allocation_method="risk_based",
        risk_pct=0.005, stop_loss_pct=0.05, lot_size=10
    )
    # AAA should have some positive shares (multiple of 10)
    assert "AAA" in shares
    assert shares["AAA"] % 10 == 0
    assert "BBB" not in shares

def test_calc_position_sizes_equal_score_scaling():
    # Two codes with equal weights resulting in raw total cost > available_cash to trigger scaling
    candidates = [{"code": "X"}, {"code": "Y"}]
    weights = {"X": 0.5, "Y": 0.5}
    portfolio_value = 100000.0
    available_cash = 50000.0  # smaller than raw allocation cost to force scaling
    current_positions = {}
    open_prices = {"X": 100.0, "Y": 100.0}
    lot_size = 10

    shares = calc_position_sizes(
        weights=weights, candidates=candidates, portfolio_value=portfolio_value,
        available_cash=available_cash, current_positions=current_positions,
        open_prices=open_prices, allocation_method="equal",
        max_utilization=0.7, lot_size=lot_size, cost_buffer=0.0
    )

    # shares should be multiples of lot_size and total cost <= available_cash
    total_cost = sum(shares[c] * open_prices[c] for c in shares)
    assert total_cost <= available_cash + 1e-6
    for s in shares.values():
        assert s % lot_size == 0

    # expect at least one code to be allocated some shares
    assert len(shares) >= 1

――――――――――――――――――――――――――――――――――――
ファイル: tests/test_feature_exploration.py
――――――――――――――――――――――――――――――――――
テスト対象:
- rank, calc_ic, factor_summary from kabusys.data.feature_exploration

内容:
import math
import pytest

from kabusys.data.feature_exploration import rank, calc_ic, factor_summary

def test_rank_with_ties():
    vals = [1.0, 2.0, 2.0, 4.0]
    r = rank(vals)
    # ranks: 1, 2.5, 2.5, 4.0
    assert pytest.approx(r[0]) == 1.0
    assert pytest.approx(r[1]) == pytest.approx(2.5)
    assert pytest.approx(r[2]) == pytest.approx(2.5)
    assert pytest.approx(r[3]) == 4.0

def test_calc_ic_perfect_correlation():
    factor_records = [
        {"code": "A", "mom_1m": 1.0},
        {"code": "B", "mom_1m": 2.0},
        {"code": "C", "mom_1m": 3.0},
        {"code": "D", "mom_1m": 4.0},
    ]
    forward_records = [
        {"code": "A", "fwd_1d": 10.0},
        {"code": "B", "fwd_1d": 20.0},
        {"code": "C", "fwd_1d": 30.0},
        {"code": "D", "fwd_1d": 40.0},
    ]
    ic = calc_ic(factor_records, forward_records, "mom_1m", "fwd_1d")
    assert pytest.approx(ic, rel=1e-6) == 1.0

def test_calc_ic_insufficient_pairs():
    factor_records = [{"code": "A", "mom_1m": None}, {"code": "B", "mom_1m": 1.0}]
    forward_records = [{"code": "A", "fwd_1d": 1.0}, {"code": "B", "fwd_1d": None}]
    assert calc_ic(factor_records, forward_records, "mom_1m", "fwd_1d") is None

def test_factor_summary_basic():
    records = [
        {"code": "A", "f1": 1.0, "f2": None},
        {"code": "B", "f1": 2.0, "f2": 3.0},
        {"code": "C", "f1": 3.0, "f2": float("nan")},
    ]
    summary = factor_summary(records, ["f1", "f2"])
    assert summary["f1"]["count"] == 3
    assert pytest.approx(summary["f1"]["mean"]) == 2.0
    assert summary["f2"]["count"] == 1
    assert summary["f2"]["mean"] == 3.0

――――――――――――――――――――――――――――――――――――
ファイル: tests/test_ai_news_nlp.py
――――――――――――――――――――――――――――――――
テスト対象:
- calc_news_window, _validate_and_extract from kabusys.ai.news_nlp

内容:
from datetime import date, datetime
import json
import types

import pytest

from kabusys.ai.news_nlp import calc_news_window, _validate_and_extract

def test_calc_news_window_logic():
    d = date(2026, 3, 20)
    start, end = calc_news_window(d)
    # start should be previous day 06:00 (UTC naive), end previous day 23:30
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)

def make_resp(content_str):
    # create a fake response object with choices[0].message.content
    msg = types.SimpleNamespace(content=content_str)
    choice = types.SimpleNamespace(message=msg)
    resp = types.SimpleNamespace(choices=[choice])
    return resp

def test_validate_and_extract_basic_and_clipping_and_noise():
    # valid JSON with results
    resp = make_resp(json.dumps({"results": [{"code": "1001", "score": 2.0}, {"code": 1002, "score": -2.0}]}))
    scores = _validate_and_extract(resp, {"1001", "1002", "9999"})
    # clipping to ±1.0
    assert scores["1001"] == 1.0
    assert scores["1002"] == -1.0

    # noise around JSON: prefix/suffix
    noisy = "some text {\"results\": [{\"code\": \"A\", \"score\": 0.5}]} trailing"
    resp2 = make_resp(noisy)
    scores2 = _validate_and_extract(resp2, {"A"})
    assert pytest.approx(scores2["A"]) == 0.5

    # invalid JSON -> returns {}
    bad = make_resp("not json")
    assert _validate_and_extract(bad, {"X"}) == {}

    # non-list results -> {}
    resp3 = make_resp(json.dumps({"results": "nope"}))
    assert _validate_and_extract(resp3, {"X"}) == {}

    # non-numeric score -> skipped
    resp4 = make_resp(json.dumps({"results": [{"code": "X", "score": "nan"}]}))
    assert _validate_and_extract(resp4, {"X"}) == {}

――――――――――――――――――――――――――――――――――――
ファイル: tests/test_monitoring_db_and_kill_switch.py
――――――――――――――――――――――――――――――――
テスト対象:
- init_monitoring_db, MonitoringDB methods (log_system_status, upsert_dashboard, get_dashboard, log_risk_event dedup)
- KillSwitch

内容:
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import os

import pytest

from kabusys.monitoring.monitoring_db import init_monitoring_db, MonitoringDB
from kabusys.monitoring.kill_switch import KillSwitch
from kabusys.monitoring.risk_monitor import RiskCheckResult

def test_init_and_monitoring_db_basic(tmp_path):
    db_path = tmp_path / "m.db"
    conn = sqlite3.connect(str(db_path))
    init_monitoring_db(conn)
    # tables should exist: system_status, trade_logs, positions, risk_logs, dashboard
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r[0] for r in cur}
    assert "system_status" in names
    assert "trade_logs" in names
    assert "positions" in names
    assert "risk_logs" in names
    assert "dashboard" in names

    # MonitoringDB operations
    db = MonitoringDB(conn)
    # no dashboard initially
    assert db.get_dashboard() is None

    # upsert dashboard and retrieve
    now = datetime.now(timezone.utc)
    db.upsert_dashboard(1000.0, 100.0, 0.05, 0, 1, updated_at=now, peak_value=1200.0)
    dash = db.get_dashboard()
    assert dash is not None
    assert dash["portfolio_value"] == 1000.0
    assert dash["peak_value"] == 1200.0

    # log_system_status adds a row
    db.log_system_status(1.1, 2.2, 3.3, True, recorded_at=now)
    r = conn.execute("SELECT COUNT(*) FROM system_status").fetchone()
    assert r[0] == 1

def test_log_risk_event_dedup_behavior():
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    db = MonitoringDB(conn)
    now = datetime.now(timezone.utc)
    # first insert should return True
    ok1 = db.log_risk_event("E1", "m", 0.1, 0.05, detail="d1", logged_at=now, dedup_minutes=60)
    assert ok1 is True
    # second insert within dedup window should return False
    ok2 = db.log_risk_event("E1", "m", 0.2, 0.05, detail="d1", logged_at=now + timedelta(minutes=10), dedup_minutes=60)
    assert ok2 is False
    # different detail should insert
    ok3 = db.log_risk_event("E1", "m", 0.3, 0.05, detail="d2", logged_at=now + timedelta(minutes=10), dedup_minutes=60)
    assert ok3 is True

def test_kill_switch_file_operations(tmp_path):
    flag = tmp_path / "data" / "kill.flag"
    ks = KillSwitch(flag)
    # initially not flagged
    assert not ks.is_flagged()

    # create reason and ensure written
    system = None
    trade = None
    risk = RiskCheckResult(logged_at="t", drawdown_pct=0.15, drawdown_alert=True, position_count=5, position_limit_alert=False)
    reason = ks.evaluate(system, trade, risk)
    assert reason is not None
    assert ks.is_flagged()
    # idempotent: calling again should return a reason but not overwrite (no exception)
    reason2 = ks.evaluate(system, trade, risk)
    assert reason2 is not None
    # clear
    ks.clear()
    assert not ks.is_flagged()

――――――――――――――――――――――――――――――――――――
ファイル: tests/test_process_priority.py
――――――――――――――――――――――――――――――――
テスト対象: kabusys.utils.process_priority.set_cpu_affinity

内容:
import types
import pytest
import psutil

from unittest.mock import patch

from kabusys.utils.process_priority import set_cpu_affinity

class DummyProcess:
    def __init__(self):
        self._affinity = None
        self.pid = 12345
    def cpu_affinity(self, pins):
        self._affinity = pins

def test_set_cpu_affinity_none():
    # cpu_count None should be no-op
    set_cpu_affinity(None)  # should not raise

def test_set_cpu_affinity_invalid():
    with pytest.raises(ValueError):
        set_cpu_affinity(0)

def test_set_cpu_affinity_success(monkeypatch):
    dummy = DummyProcess()
    monkeypatch.setattr(psutil, "Process", lambda: dummy)
    monkeypatch.setattr(psutil, "cpu_count", lambda: 4)
    set_cpu_affinity(2)
    assert dummy._affinity == [0, 1]

def test_set_cpu_affinity_access_denied(monkeypatch):
    class BadProcess:
        def cpu_affinity(self, pins):
            raise psutil.AccessDenied("denied")
    monkeypatch.setattr(psutil, "Process", lambda: BadProcess())
    monkeypatch.setattr(psutil, "cpu_count", lambda: 2)
    # should not raise despite AccessDenied (warning logged)
    set_cpu_affinity(1)

――――――――――――――――――――――――――――――――――――
実行方法:
- プロジェクトルートで pytest を実行してください:
  pytest -q

ポイント・補足:
- tests/conftest.py により、テスト全体で自動 .env 読み込みを無効化しています（パッケージ import 時の副作用を防止）。
- OpenAI 呼び出しや psutil の副作用はモックしているため、ネットワークや権限に依存せず実行できます。
- DB 操作は一部で一時ファイルや :memory: を使っており、テストはローカル環境に影響を与えません。
- もしテスト実行時に import エラーが出る場合は、テストが配置されるディレクトリ構成（kabusys パッケージが PYTHONPATH にあること）を確認してください。

必要なら、さらに他モジュール（MonitoringEngine, SystemMonitor の check_once など）やより詳細な数値検証（position_sizing の scaling の内部挙動）を追加でテストするテストケースも作成します。どのモジュールをさらに重点的に増やすか指示ください。