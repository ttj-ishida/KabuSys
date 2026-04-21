import os
import math
from unittest import mock

import pytest

# 自動 .env ロードを抑止しておく（テストの安定化）
os.environ.setdefault("KABUSYS_DISABLE_AUTO_ENV_LOAD", "1")

# インポート（テスト対象モジュール）
from kabusys.run_monitoring import _get_poll_interval
from kabusys.portfolio.portfolio_builder import (
    select_candidates,
    calc_equal_weights,
    calc_score_weights,
)
from kabusys.portfolio.risk_adjustment import (
    apply_sector_cap,
    calc_regime_multiplier,
)
from kabusys.portfolio.position_sizing import calc_position_sizes
from kabusys.config import (
    _parse_env_line,
    _load_env_file,
    Settings,
)
from kabusys.research.feature_exploration import calc_ic, rank

# process_priority のテストでモックするためインポート


# -----------------------
# run_monitoring._get_poll_interval
# -----------------------
@pytest.mark.parametrize(
    ("env_val", "expected"),
    [
        ("10", 10),
        (None, 60),  # デフォルト
    ],
)
def test_get_poll_interval_valid(monkeypatch, env_val, expected):
    if env_val is None:
        monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    else:
        monkeypatch.setenv("MONITOR_POLL_INTERVAL", env_val)
    assert _get_poll_interval() == expected


def test_get_poll_interval_invalid_nonint(monkeypatch, caplog):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "notint")
    caplog.clear()
    val = _get_poll_interval()
    assert val == 60
    # 警告ログが出ていること
    assert any(
        "MONITOR_POLL_INTERVAL の値が不正" in rec.message for rec in caplog.records
    )


def test_get_poll_interval_zero_or_negative(monkeypatch):
    for v in ("0", "-5"):
        monkeypatch.setenv("MONITOR_POLL_INTERVAL", v)
        assert _get_poll_interval() == 60


# -----------------------
# config._parse_env_line / _load_env_file
# -----------------------
def test_parse_env_line_basic():
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line("  export KEY2 = some ") == ("KEY2", "some")
    assert _parse_env_line("# comment") is None
    assert _parse_env_line("") is None
    assert _parse_env_line("NOEQ") is None


def test_parse_env_line_quoted_and_escaped():
    # シングルクォート内のエスケープ
    line = r"SECRET='pa\'ss\"word'"
    k, v = _parse_env_line(line)
    assert k == "SECRET"
    # エスケープがデコードされていること
    assert "pa'ss\"word" == v

    # ダブルクォートとインラインコメント
    line2 = 'FOO="a=b # not comment"  # trailing comment'
    k2, v2 = _parse_env_line(line2)
    assert k2 == "FOO"
    assert v2 == "a=b # not comment"


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    envfile = tmp_path / ".env.test"
    envfile.write_text(
        "\n".join(
            [
                "A=1",
                "B=from_file",
                "SECRET='x\\'y'",
                "SKIP_ME=noeq",
            ]
        )
    )
    # 初期 OS 環境
    monkeypatch.delenv("A", raising=False)
    monkeypatch.setenv("B", "os_b")
    # protected は既存の OS 環境キー集合として扱われる
    protected = frozenset(["B"])
    # override=False: 未設定のキーのみセット
    _load_env_file(envfile, override=False, protected=protected)
    assert os.environ.get("A") == "1"
    # B は既にあるので上書きされない
    assert os.environ.get("B") == "os_b"
    # override=True: protected に含まれるキーは上書きされない
    monkeypatch.setenv("B", "os_b2")
    _load_env_file(envfile, override=True, protected=protected)
    assert os.environ.get("B") == "os_b2"
    # SECRET がパースされている
    assert os.environ.get("SECRET") == "x'y"


# -----------------------
# Settings クラスの主要挙動
# -----------------------
def test_settings_env_and_flags(monkeypatch):
    monkeypatch.setenv("KABUSYS_ENV", "development")
    s = Settings()
    assert s.env == "development"
    assert s.is_dev
    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    s2 = Settings()
    assert s2.is_paper
    monkeypatch.setenv("KABUSYS_ENV", "live")
    s3 = Settings()
    assert s3.is_live


def test_settings_invalid_env(monkeypatch):
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env_value")
    s = Settings()
    with pytest.raises(ValueError):
        _ = s.env  # property アクセス時に例外


def test_settings_paper_fill_mode_valid_and_invalid(monkeypatch):
    monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
    s = Settings()
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert Settings().paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "INVALID")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode


# -----------------------
# portfolio_builder: select / weights
# -----------------------
def test_select_candidates_and_weights():
    signals = [
        {"code": "AAA", "score": 1.0, "signal_rank": 2},
        {"code": "BBB", "score": 2.0, "signal_rank": 1},
        {"code": "CCC", "score": 2.0, "signal_rank": 3},
    ]
    selected = select_candidates(signals, max_positions=2)
    # score 降順 -> BBB (2.0, rank1), CCC (2.0, rank3) が上位2件
    assert [s["code"] for s in selected] == ["BBB", "CCC"]

    eq_weights = calc_equal_weights(selected)
    assert math.isclose(eq_weights["BBB"], 0.5)
    assert math.isclose(eq_weights["CCC"], 0.5)

    # score_weights: sum(scores)=4.0 -> weights 2/4,2/4 -> 0.5 each
    sw = calc_score_weights(selected)
    assert pytest.approx(sw["BBB"]) == 0.5
    assert pytest.approx(sw["CCC"]) == 0.5

    # 全スコアが 0 の場合は等金額フォールバック
    zero_signals = [{"code": "X", "score": 0.0}, {"code": "Y", "score": 0.0}]
    with mock.patch("kabusys.portfolio.portfolio_builder.logger") as mocked_logger:
        w = calc_score_weights(zero_signals)
        assert w == {"X": 0.5, "Y": 0.5}
        # 警告が出ていること
        mocked_logger.warning.assert_called()


# -----------------------
# risk_adjustment.apply_sector_cap / calc_regime_multiplier
# -----------------------
def test_apply_sector_cap_basic_and_sell_codes():
    candidates = [{"code": "A"}, {"code": "B"}, {"code": "C"}]
    sector_map = {"A": "Tech", "B": "Tech", "C": "Food"}
    portfolio_value = 1000000.0
    # 現在 A,B を大量保有して Tech が上限を超えるようにする
    current_positions = {"A": 1000, "B": 500}
    price_map = {"A": 100.0, "B": 100.0, "C": 10.0}
    # 1セクター上限 30% -> Tech exposure = (1000+500)*100 = 150000 -> 15% -> not blocked
    filtered = apply_sector_cap(
        candidates,
        sector_map,
        portfolio_value,
        current_positions,
        price_map,
        max_sector_pct=0.10,  # 10% にすると 150k / 1M = 15% -> blocked
    )
    # C (Food) は残り、Tech がブロックされるため only C remains
    assert all(c["code"] == "C" for c in filtered)

    # sell_codes に A を入れると exposure が減りブロックされなくなる
    filtered2 = apply_sector_cap(
        candidates,
        sector_map,
        portfolio_value,
        current_positions,
        price_map,
        max_sector_pct=0.10,
        sell_codes={"A"},
    )
    # now Tech exposure = B only => 50k -> 5% -> not blocked -> all candidates remain
    codes = {c["code"] for c in filtered2}
    assert codes == {"A", "B", "C"}


def test_calc_regime_multiplier_known_and_unknown(monkeypatch):
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == pytest.approx(0.7)
    assert calc_regime_multiplier("bear") == pytest.approx(0.3)
    # unknown regime: warning and fallback 1.0
    with mock.patch("kabusys.portfolio.risk_adjustment.logger") as mocked_logger:
        assert calc_regime_multiplier("weird") == 1.0
        mocked_logger.warning.assert_called()


# -----------------------
# position_sizing.calc_position_sizes（主なケース）
# -----------------------
def test_calc_position_sizes_equal_and_aggregate_scaling():
    # Simple equal weights case
    candidates = [{"code": "AAA"}, {"code": "BBB"}]
    weights = {"AAA": 0.5, "BBB": 0.5}
    portfolio_value = 100_0000.0  # 1,000,000
    available_cash = 200_000.0
    current_positions = {}
    open_prices = {"AAA": 1000.0, "BBB": 1000.0}
    # max_utilization default 0.7 used in function; but available_cash limits aggregate
    sizes = calc_position_sizes(
        weights,
        candidates,
        portfolio_value,
        available_cash,
        current_positions,
        open_prices,
        allocation_method="equal",
        lot_size=100,
    )
    # available_cash = 200_000 が制約: per stock = 200_000 / 2 = 100_000
    # shares = floor(100_000 / 1000) = 100 → 100株（1単元）
    assert sizes["AAA"] == 100
    assert sizes["BBB"] == 100

    # If available_cash smaller than total cost, aggregate scaling should reduce sizes
    small_cash = 100_000.0
    scaled = calc_position_sizes(
        weights,
        candidates,
        portfolio_value,
        small_cash,
        current_positions,
        open_prices,
        allocation_method="equal",
        lot_size=100,
    )
    # scaled total cost must not exceed small_cash
    total_cost = sum(scaled[c] * open_prices[c] for c in scaled)
    assert total_cost <= small_cash + 1e-6


def test_calc_position_sizes_risk_based_and_price_missing(caplog):
    candidates = [{"code": "X"}, {"code": "Y"}]
    weights = {}
    portfolio_value = 1_000_000
    available_cash = 500_000
    current_positions = {"X": 0}
    open_prices = {"X": 0.0}  # price missing / zero -> skip
    res = calc_position_sizes(
        weights,
        candidates,
        portfolio_value,
        available_cash,
        current_positions,
        open_prices,
        allocation_method="risk_based",
        lot_size=100,
    )
    # X skipped due to price 0, Y not in open_prices -> skipped -> empty dict
    assert res == {}


# -----------------------
# feature_exploration.rank / calc_ic
# -----------------------


def test_rank_with_ties():
    vals = [1.0, 2.0, 2.0, 4.0]
    r = rank(vals)
    # ranks should be [1, 2.5, 2.5, 4]
    assert pytest.approx(r[0]) == 1.0
    assert pytest.approx(r[1]) == 2.5
    assert pytest.approx(r[2]) == 2.5
    assert pytest.approx(r[3]) == 4.0


def test_calc_ic_basic_and_insufficient():
    factor = [
        {"code": "A", "mom_1m": 0.1},
        {"code": "B", "mom_1m": 0.2},
        {"code": "C", "mom_1m": 0.3},
    ]
    forward = [
        {"code": "A", "fwd_1d": 0.01},
        {"code": "B", "fwd_1d": -0.02},
        {"code": "C", "fwd_1d": 0.03},
    ]
    ic = calc_ic(factor, forward, "mom_1m", "fwd_1d")
    # Should return a finite float
    assert isinstance(ic, float)

    # insufficient pairs -> None
    ic2 = calc_ic(factor[:2], forward[:2], "mom_1m", "fwd_1d")
    assert ic2 is None
