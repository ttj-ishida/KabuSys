"""backtest_summarizer.py — バックテスト結果から AI system prompt 用 Markdown を生成する。"""

from __future__ import annotations

import json
import logging

import duckdb

logger = logging.getLogger(__name__)


def load_latest_summary(conn: duckdb.DuckDBPyConnection) -> str | None:
    """backtest_runs の最新1件から system prompt 用 Markdown を生成する。

    バックテスト結果がない場合は None を返す。
    params_json が不正な場合はパラメータ行をスキップし、クラッシュしない。

    Args:
        conn: DuckDB 接続。backtest_runs テーブルを参照する。

    Returns:
        Markdown 形式の文字列、またはデータなしの場合は None。
    """
    try:
        row = conn.execute("""
            SELECT run_id, start_date, end_date,
                   cagr, sharpe, max_drawdown, win_rate,
                   payoff_ratio, profit_factor, total_trades,
                   params_json
            FROM backtest_runs
            ORDER BY created_at DESC
            LIMIT 1
        """).fetchone()
    except Exception as e:
        logger.warning("load_latest_summary: backtest_runs 読み込みエラー: %s", e)
        return None

    if row is None:
        return None

    run_id = str(row[0])
    start_date = str(row[1])
    end_date = str(row[2])
    cagr: float | None = row[3]
    sharpe: float | None = row[4]
    max_dd: float | None = row[5]
    win_rate: float | None = row[6]
    payoff: float | None = row[7]
    profit_factor: float | None = row[8]
    total_trades: int | None = row[9]
    params_json_str: str | None = row[10]

    def _pct(v: float | None) -> str:
        return f"{v:+.2%}" if v is not None else "N/A"

    def _f(v: float | None, prec: int = 3) -> str:
        return f"{v:.{prec}f}" if v is not None else "N/A"

    lines = [
        f"## 最新バックテスト結果（run_id: {run_id}, {start_date}〜{end_date}）",
        "",
        "| 指標 | 値 |",
        "|------|-----|",
        f"| CAGR | {_pct(cagr)} |",
        f"| Sharpe Ratio | {_f(sharpe)} |",
        f"| Max Drawdown | {_pct(max_dd)} |",
        f"| Win Rate | {_pct(win_rate)} |",
        f"| Payoff Ratio | {_f(payoff)} |",
        f"| Profit Factor | {_f(profit_factor)} |",
        f"| Total Trades | {total_trades if total_trades is not None else 'N/A'} |",
    ]

    params: dict = {}
    if params_json_str:
        try:
            parsed = json.loads(params_json_str)
            if isinstance(parsed, dict):
                params = parsed
        except (json.JSONDecodeError, TypeError):
            logger.warning("load_latest_summary: params_json のパースに失敗しました")

    if params:
        weights = params.get("weights", {})
        buy_parts = [
            f"weights={weights}",
            f"threshold={params.get('threshold', 'N/A')}",
            f"sector_boost={params.get('sector_boost', 'N/A')}",
            f"sector_quartile={params.get('sector_quartile', 'N/A')}",
        ]
        risk_parts = [
            f"stop_loss_rate={params.get('stop_loss_rate', 'N/A')}",
            f"trailing_stop_atr_mult={params.get('trailing_stop_atr_mult', 'N/A')}",
            f"gap_up_threshold={params.get('gap_up_threshold', 'N/A')}",
            f"gap_down_threshold={params.get('gap_down_threshold', 'N/A')}",
            f"min_holding_days={params.get('min_holding_days', 'N/A')}",
            f"max_holding_days={params.get('max_holding_days', 'N/A')}",
            f"topix_drawdown_threshold={params.get('topix_drawdown_threshold', 'N/A')}",
            f"topix_size_multiplier_bear={params.get('topix_size_multiplier_bear', 'N/A')}",
        ]
        lines += [
            "",
            "### 戦略パラメータ",
            f"**購入ロジック**: {', '.join(buy_parts)}",
            "",
            f"**リスク・フィルター**: {', '.join(risk_parts)}",
        ]

    return "\n".join(lines)
