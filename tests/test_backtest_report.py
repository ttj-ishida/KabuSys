"""バックテストレポート モジュール テスト"""

from __future__ import annotations

import json
from datetime import date, timedelta


from kabusys.backtest.simulator import DailySnapshot, TradeRecord


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_history(
    values: list[float], start: date | None = None
) -> list[DailySnapshot]:
    base = start or date(2024, 1, 1)
    return [
        DailySnapshot(
            date=base + timedelta(days=i), cash=0.0, positions={}, portfolio_value=v
        )
        for i, v in enumerate(values)
    ]


def _make_trade(
    *,
    code: str = "1234",
    side: str = "sell",
    pnl: float | None = None,
    day_offset: int = 0,
    commission: float = 55.0,
) -> TradeRecord:
    return TradeRecord(
        date=date(2024, 1, 2) + timedelta(days=day_offset),
        code=code,
        side=side,
        shares=100,
        price=1000.0,
        commission=commission,
        realized_pnl=pnl,
    )


def _make_result(history, trades):
    """BacktestResult 相当の軽量オブジェクトを返す。"""
    from kabusys.backtest.metrics import calc_metrics
    from kabusys.backtest.engine import BacktestResult

    metrics = calc_metrics(history, trades)
    return BacktestResult(history=history, trades=trades, metrics=metrics)


# ---------------------------------------------------------------------------
# Task 1: metrics.py 拡張指標
# ---------------------------------------------------------------------------


def test_sharpe_uses_population_variance():
    """Sharpe は母分散（n 分母）で計算されることを固定系列で検証する。

    系列: [100, 110, 100]
    日次リターン: [+0.1, -1/11]
    mean = (0.1 - 1/11) / 2
    母分散 = Σ(r - mean)^2 / 2
    """
    import math
    from kabusys.backtest.metrics import _calc_sharpe

    history = _make_history([100.0, 110.0, 100.0])
    returns = [0.1, -1.0 / 11.0]
    n = len(returns)
    mean_r = sum(returns) / n
    # 母分散（n 分母）
    variance = sum((r - mean_r) ** 2 for r in returns) / n
    expected_sharpe = (mean_r / math.sqrt(variance)) * math.sqrt(252)
    assert abs(_calc_sharpe(history) - expected_sharpe) < 1e-9


def test_annual_volatility_flat_returns():
    """リターンが常に0のとき年率ボラティリティ = 0.0。"""
    from kabusys.backtest.metrics import calc_metrics

    history = _make_history([1_000_000] * 100)
    m = calc_metrics(history, [])
    assert m.annual_volatility == 0.0


def test_annual_volatility_nonzero():
    """変動のある系列では年率ボラティリティ > 0。"""
    from kabusys.backtest.metrics import calc_metrics

    values = [1_000_000 + (i % 2) * 10_000 for i in range(50)]
    history = _make_history(values)
    m = calc_metrics(history, [])
    assert m.annual_volatility > 0.0


def test_calmar_ratio_positive():
    """CAGR > 0 かつ MDD > 0 → Calmar Ratio = CAGR / MDD。"""
    from kabusys.backtest.metrics import _calc_calmar_ratio

    cagr = 0.20
    mdd = 0.10
    expected = 2.0
    assert abs(_calc_calmar_ratio(cagr, mdd) - expected) < 1e-9


def test_calmar_ratio_zero_mdd():
    """MDD = 0 のとき Calmar Ratio = 0.0（ゼロ除算回避）。"""
    from kabusys.backtest.metrics import _calc_calmar_ratio

    assert _calc_calmar_ratio(0.20, 0.0) == 0.0


def test_profit_factor_positive():
    """利益1000 損失-500 → Profit Factor = 2.0。"""
    from kabusys.backtest.metrics import calc_metrics

    history = _make_history([1_000_000, 1_000_000])
    trades = [
        _make_trade(pnl=1000.0, day_offset=0),
        _make_trade(pnl=-500.0, day_offset=1),
    ]
    m = calc_metrics(history, trades)
    assert abs(m.profit_factor - 2.0) < 1e-6


def test_profit_factor_no_losses():
    """損失トレードなし → Profit Factor = 0.0。"""
    from kabusys.backtest.metrics import calc_metrics

    history = _make_history([1_000_000, 1_000_000])
    trades = [_make_trade(pnl=500.0, day_offset=0)]
    m = calc_metrics(history, trades)
    assert m.profit_factor == 0.0


def test_avg_holding_days_single_pair():
    """BUY 1/1 → SELL 1/11 → 保有10日。"""
    from kabusys.backtest.metrics import calc_metrics

    history = _make_history([1_000_000, 1_000_000])
    buy = TradeRecord(
        date=date(2024, 1, 1),
        code="1234",
        side="buy",
        shares=100,
        price=1000.0,
        commission=55.0,
        realized_pnl=None,
    )
    sell = TradeRecord(
        date=date(2024, 1, 11),
        code="1234",
        side="sell",
        shares=100,
        price=1050.0,
        commission=55.0,
        realized_pnl=5000.0,
    )
    m = calc_metrics(history, [buy, sell])
    assert m.avg_holding_days == 10.0


def test_avg_holding_days_no_pairs():
    """sell のみ（BUY なし）→ 平均保有日数 = 0.0。"""
    from kabusys.backtest.metrics import calc_metrics

    history = _make_history([1_000_000, 1_000_000])
    trades = [_make_trade(pnl=500.0, day_offset=0)]
    m = calc_metrics(history, trades)
    assert m.avg_holding_days == 0.0


# ---------------------------------------------------------------------------
# Task 2: build_report()
# ---------------------------------------------------------------------------


def test_build_report_returns_backtest_report():
    """build_report() が BacktestReport を返す。"""
    from kabusys.backtest.report import build_report, BacktestReport

    history = _make_history([1_000_000] * 200)
    trades = [
        _make_trade(pnl=10_000.0, day_offset=0),
        _make_trade(pnl=-5_000.0, day_offset=1),
    ]
    result = _make_result(history, trades)
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 7, 18)
    )
    assert isinstance(report, BacktestReport)


def test_build_report_run_id_auto_generated():
    """run_id を省略すると UUID 形式の文字列が設定される。"""
    from kabusys.backtest.report import build_report

    history = _make_history([1_000_000] * 10)
    result = _make_result(history, [])
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 1, 10)
    )
    import re

    assert re.match(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        report.meta.run_id,
    )


def test_build_report_run_id_custom():
    """run_id を指定するとそれが使われる。"""
    from kabusys.backtest.report import build_report

    history = _make_history([1_000_000] * 10)
    result = _make_result(history, [])
    report = build_report(
        result,
        run_id="test-run-001",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
    )
    assert report.meta.run_id == "test-run-001"


def test_build_report_headline_total_return():
    """final_value = 1.1 * initial_cash → total_return ≈ 0.10。"""
    from kabusys.backtest.report import build_report

    initial = 10_000_000.0
    final = 11_000_000.0
    n = 200
    # 徐々に増加する history
    step = (final - initial) / (n - 1)
    values = [initial + step * i for i in range(n)]
    history = _make_history(values)
    result = _make_result(history, [])
    report = build_report(
        result,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 7, 18),
        initial_cash=initial,
    )
    assert abs(report.headline.total_return - 0.10) < 1e-6


def test_build_report_final_value_uses_latest_date():
    """history が日付順でなくても final_value は最新日付のポートフォリオ値を使う。"""
    from kabusys.backtest.report import build_report

    # 逆順の history（古い日付が末尾）
    history = [
        DailySnapshot(
            date=date(2024, 3, 1), cash=0.0, positions={}, portfolio_value=12_000_000.0
        ),
        DailySnapshot(
            date=date(2024, 1, 1), cash=0.0, positions={}, portfolio_value=10_000_000.0
        ),
        DailySnapshot(
            date=date(2024, 2, 1), cash=0.0, positions={}, portfolio_value=11_000_000.0
        ),
    ]
    result = _make_result(history, [])
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 3, 1)
    )
    assert report.headline.final_value == 12_000_000.0


def test_build_report_trade_section_win_rate():
    """3勝1敗 → win_rate = 0.75。"""
    from kabusys.backtest.report import build_report

    history = _make_history([1_000_000] * 50)
    trades = [
        _make_trade(pnl=1000.0, day_offset=0),
        _make_trade(pnl=2000.0, day_offset=1),
        _make_trade(pnl=3000.0, day_offset=2),
        _make_trade(pnl=-500.0, day_offset=3),
    ]
    result = _make_result(history, trades)
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 2, 19)
    )
    assert abs(report.trades.win_rate - 0.75) < 1e-9


# ---------------------------------------------------------------------------
# Task 3: format_cli_summary()
# ---------------------------------------------------------------------------


def test_format_cli_summary_contains_cagr():
    """CLI サマリに CAGR 行が含まれる。"""
    from kabusys.backtest.report import build_report, format_cli_summary

    history = _make_history([1_000_000] * 200)
    result = _make_result(history, [])
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 7, 18)
    )
    text = format_cli_summary(report)
    assert "CAGR" in text


def test_format_cli_summary_contains_run_id():
    """CLI サマリに run_id が含まれる。"""
    from kabusys.backtest.report import build_report, format_cli_summary

    history = _make_history([1_000_000] * 200)
    result = _make_result(history, [])
    report = build_report(
        result,
        run_id="abc-123",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 7, 18),
    )
    text = format_cli_summary(report)
    assert "abc-123" in text


def test_format_cli_summary_contains_warnings():
    """Warning がある場合、CLI サマリに含まれる。"""
    from kabusys.backtest.report import build_report, format_cli_summary

    history = _make_history([1_000_000] * 10)  # 短期間 → warning 発生
    result = _make_result(history, [])
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 1, 10)
    )
    text = format_cli_summary(report)
    assert "Warnings" in text or "Warning" in text or "[!]" in text


# ---------------------------------------------------------------------------
# Task 4: format_json()
# ---------------------------------------------------------------------------


def test_format_json_is_valid_json():
    """format_json() は有効な JSON を返す。"""
    from kabusys.backtest.report import build_report, format_json

    history = _make_history([1_000_000] * 200)
    result = _make_result(history, [])
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 7, 18)
    )
    text = format_json(report)
    parsed = json.loads(text)
    assert isinstance(parsed, dict)


def test_format_json_contains_expected_keys():
    """JSON に meta / headline / trades / performance / warnings キーが含まれる。"""
    from kabusys.backtest.report import build_report, format_json

    history = _make_history([1_000_000] * 200)
    result = _make_result(history, [])
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 7, 18)
    )
    parsed = json.loads(format_json(report))
    for key in ("meta", "headline", "trades", "performance", "warnings"):
        assert key in parsed


def test_format_json_run_id_roundtrip():
    """JSON に run_id が正しくシリアライズされる。"""
    from kabusys.backtest.report import build_report, format_json

    history = _make_history([1_000_000] * 200)
    result = _make_result(history, [])
    report = build_report(
        result,
        run_id="round-trip-id",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 7, 18),
    )
    parsed = json.loads(format_json(report))
    assert parsed["meta"]["run_id"] == "round-trip-id"


# ---------------------------------------------------------------------------
# Task 5: format_markdown()
# ---------------------------------------------------------------------------


def test_format_markdown_contains_sections():
    """Markdown に主要セクション見出しが含まれる。"""
    from kabusys.backtest.report import build_report, format_markdown

    history = _make_history([1_000_000] * 200)
    result = _make_result(history, [])
    report = build_report(
        result, start_date=date(2024, 1, 1), end_date=date(2024, 7, 18)
    )
    md = format_markdown(report)
    for section in (
        "Overview",
        "Scope",
        "Headline Metrics",
        "Equity",
        "Trade Analysis",
    ):
        assert section in md


def test_format_markdown_monthly_returns_table():
    """複数月のデータがあれば Markdown に Monthly Returns テーブルが含まれる。"""
    from kabusys.backtest.report import build_report, format_markdown

    # 3ヶ月分の history を生成
    start = date(2024, 1, 1)
    values = [1_000_000 + i * 100 for i in range(91)]
    history = _make_history(values, start=start)
    result = _make_result(history, [])
    report = build_report(result, start_date=start, end_date=start + timedelta(days=90))
    md = format_markdown(report)
    assert "Monthly Returns" in md


# ---------------------------------------------------------------------------
# Task 6: save_report()
# ---------------------------------------------------------------------------


def test_save_report_creates_files(tmp_path):
    """save_report() で 4 ファイルが生成される。"""
    from kabusys.backtest.report import build_report, save_report

    history = _make_history([1_000_000] * 200)
    trades = [
        _make_trade(pnl=500.0, day_offset=0),
        _make_trade(side="buy", pnl=None, day_offset=1),
    ]
    result = _make_result(history, trades)
    report = build_report(
        result,
        run_id="test-save",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 7, 18),
    )
    run_dir = save_report(report, result, output_dir=tmp_path)

    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "trades.csv").exists()
    assert (run_dir / "daily_equity.csv").exists()


def test_save_report_run_dir_name(tmp_path):
    """保存先ディレクトリ名が run_id と一致する。"""
    from kabusys.backtest.report import build_report, save_report

    history = _make_history([1_000_000] * 10)
    result = _make_result(history, [])
    report = build_report(
        result,
        run_id="my-run-42",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
    )
    run_dir = save_report(report, result, output_dir=tmp_path)
    assert run_dir.name == "my-run-42"


def test_save_report_trades_csv_has_header(tmp_path):
    """trades.csv に正しいヘッダー行が含まれる。"""
    from kabusys.backtest.report import build_report, save_report

    history = _make_history([1_000_000] * 10)
    result = _make_result(history, [])
    report = build_report(
        result,
        run_id="csv-test",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
    )
    run_dir = save_report(report, result, output_dir=tmp_path)
    header = (run_dir / "trades.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "date" in header and "code" in header and "realized_pnl" in header


def test_save_report_equity_csv_has_header(tmp_path):
    """daily_equity.csv に正しいヘッダー行が含まれる。"""
    from kabusys.backtest.report import build_report, save_report

    history = _make_history([1_000_000] * 10)
    result = _make_result(history, [])
    report = build_report(
        result,
        run_id="equity-test",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
    )
    run_dir = save_report(report, result, output_dir=tmp_path)
    header = (run_dir / "daily_equity.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "date" in header and "portfolio_value" in header


def test_save_report_buy_realized_pnl_none_is_empty(tmp_path):
    """BUY トレードの realized_pnl=None は CSV で空欄として出力される。"""
    from kabusys.backtest.report import build_report, save_report

    history = _make_history([1_000_000] * 10)
    buy_trade = _make_trade(side="buy", pnl=None, day_offset=0)
    result = _make_result(history, [buy_trade])
    report = build_report(
        result,
        run_id="none-pnl-test",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
    )
    run_dir = save_report(report, result, output_dir=tmp_path)
    rows = (run_dir / "trades.csv").read_text(encoding="utf-8").splitlines()
    # header + 1 data row
    assert len(rows) == 2
    assert rows[1].endswith(",")  # 末尾が空欄（ "None" でない）
    assert "None" not in rows[1]


# ---------------------------------------------------------------------------
# Task 7: _generate_warnings()
# ---------------------------------------------------------------------------


def test_warning_few_trades():
    """総トレード数 < 10 のとき警告が生成される。"""
    from kabusys.backtest.report import _generate_warnings

    history = _make_history([1_000_000] * 400)
    trades = [_make_trade(pnl=500.0, day_offset=i) for i in range(5)]  # 5件のみ
    result = _make_result(history, trades)
    warnings = _generate_warnings(result)
    assert any("トレード数" in w for w in warnings)


def test_warning_short_period():
    """検証期間 < 180日のとき警告が生成される。"""
    from kabusys.backtest.report import _generate_warnings

    history = _make_history([1_000_000] * 50)  # 50日のみ
    result = _make_result(history, [])
    warnings = _generate_warnings(result)
    assert any("期間" in w for w in warnings)


def test_warning_single_stock_dominance():
    """1銘柄が総利益の 50% 超 → 警告が生成される。"""
    from kabusys.backtest.report import _generate_warnings

    history = _make_history([1_000_000] * 400)
    trades = [
        _make_trade(code="1234", pnl=9000.0, day_offset=0),  # 90%
        _make_trade(code="5678", pnl=1000.0, day_offset=1),  # 10%
    ]
    result = _make_result(history, trades)
    warnings = _generate_warnings(result)
    assert any("1234" in w for w in warnings)


def test_no_warnings_healthy_run():
    """十分なトレード数・期間・分散がある場合は警告なし。"""
    from kabusys.backtest.report import _generate_warnings

    history = _make_history([1_000_000] * 400)
    # 10銘柄、均等に利益
    trades = [
        _make_trade(code=str(1000 + i), pnl=1000.0, day_offset=i) for i in range(10)
    ]
    result = _make_result(history, trades)
    warnings = _generate_warnings(result)
    assert warnings == []


# ---------------------------------------------------------------------------
# Task 8: _calc_monthly_returns()
# ---------------------------------------------------------------------------


def test_calc_monthly_returns_two_months():
    """2ヶ月分のデータから月次リターンが1件生成される。"""
    from kabusys.backtest.report import _calc_monthly_returns

    start = date(2024, 1, 1)
    # 1月末: 1,000,000 → 2月末: 1,100,000 → +10%
    history = []
    for i in range(31):  # 1月
        history.append(
            DailySnapshot(
                date=start + timedelta(days=i),
                cash=0.0,
                positions={},
                portfolio_value=1_000_000.0,
            )
        )
    for i in range(28):  # 2月
        history.append(
            DailySnapshot(
                date=date(2024, 2, 1) + timedelta(days=i),
                cash=0.0,
                positions={},
                portfolio_value=1_100_000.0,
            )
        )

    monthly = _calc_monthly_returns(history)
    assert len(monthly) == 1
    assert monthly[0].year == 2024
    assert monthly[0].month == 2
    assert abs(monthly[0].return_pct - 10.0) < 1e-6


def test_calc_monthly_returns_single_month():
    """1ヶ月以下のデータでは月次リターンは空。"""
    from kabusys.backtest.report import _calc_monthly_returns

    history = _make_history([1_000_000] * 30)
    monthly = _calc_monthly_returns(history)
    assert monthly == []


def test_calc_monthly_returns_empty():
    """空の history では月次リターンは空。"""
    from kabusys.backtest.report import _calc_monthly_returns

    monthly = _calc_monthly_returns([])
    assert monthly == []


def test_sharpe_variance_zero_returns_zero():
    """history が2日分（returns=1件）で variance=0 のとき Sharpe = 0.0。"""
    from kabusys.backtest.metrics import _calc_sharpe

    history = _make_history([1_000_000, 1_100_000])
    assert _calc_sharpe(history) == 0.0


def test_sharpe_zero_prev_value_no_zerodivision():
    """前日ポートフォリオ値が 0 のスナップショットを含む場合にゼロ除算が発生しない。"""
    from kabusys.backtest.metrics import _calc_sharpe
    from datetime import date

    history = [
        DailySnapshot(
            date=date(2024, 1, 1), cash=0.0, positions={}, portfolio_value=0.0
        ),
        DailySnapshot(
            date=date(2024, 1, 2), cash=0.0, positions={}, portfolio_value=1_000_000.0
        ),
        DailySnapshot(
            date=date(2024, 1, 3), cash=0.0, positions={}, portfolio_value=1_100_000.0
        ),
    ]
    result = _calc_sharpe(history)
    assert isinstance(result, float)


def test_max_drawdown_reverse_order_history():
    """逆順の history を calc_metrics に渡しても MDD が正しく計算される。"""
    from kabusys.backtest.metrics import calc_metrics

    # 昇順: [1_000_000, 900_000, 1_100_000] → MDD = (1_000_000 - 900_000) / 1_000_000 = 10%
    history_fwd = _make_history([1_000_000.0, 900_000.0, 1_100_000.0])
    history_rev = list(reversed(history_fwd))
    m_fwd = calc_metrics(history_fwd, [])
    m_rev = calc_metrics(history_rev, [])
    assert abs(m_fwd.max_drawdown - m_rev.max_drawdown) < 1e-9
    assert abs(m_fwd.max_drawdown - 0.1) < 1e-9


def test_save_report_equity_csv_is_date_sorted(tmp_path):
    """daily_equity.csv が日付昇順で出力される。"""
    from kabusys.backtest.report import build_report, save_report
    import csv as csv_mod

    history = list(reversed(_make_history([1_000_000.0, 1_050_000.0, 1_100_000.0])))
    result = _make_result(history, [])
    report = build_report(
        result,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 3),
        initial_cash=1_000_000.0,
    )
    run_dir = save_report(report, result, output_dir=tmp_path)
    with open(run_dir / "daily_equity.csv", encoding="utf-8") as f:
        rows = list(csv_mod.DictReader(f))
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates)
