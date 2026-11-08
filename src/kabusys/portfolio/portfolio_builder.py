"""銘柄選定・配分重み計算。

PortfolioConstruction.md Section 5〜7 に基づく純粋関数群。
DB 参照なし — メモリ内計算のみ。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PORTFOLIO_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "strategy_config.yaml"
_DEFAULT_MAX_POSITIONS = 10

VALID_ALLOCATION_METHODS = ("equal", "score", "risk_based")

# strategy_config.yaml の portfolio セクションが無い・不正な場合の既定値
# （calc_position_sizes / run_backtest の既定値と同じ）
DEFAULT_PORTFOLIO_CONFIG: dict[str, Any] = {
    "max_positions": _DEFAULT_MAX_POSITIONS,
    "allocation_method": "risk_based",
    "max_position_pct": 0.10,
    "max_utilization": 0.70,
    "risk_pct": 0.005,
}


def _valid_ratio(v: object, *, allow_one: bool) -> bool:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    return 0 < float(v) <= 1 if allow_one else 0 < float(v) < 1


def _valid_max_positions(v: object) -> bool:
    return (
        not isinstance(v, bool)
        and isinstance(v, (int, float))
        and (not isinstance(v, float) or v.is_integer())
        and int(v) >= 1
    )


def load_portfolio_config(path: Path | None = None) -> dict[str, Any]:
    """config/strategy_config.yaml の portfolio セクションから資金配分の設定を読み込む。

    返すキー: max_positions（保有銘柄数の上限）、allocation_method、
    max_position_pct（1 銘柄上限・総資産比）、max_utilization（保有全体の投資割合上限）、
    risk_pct（risk_based 時の 1 トレード許容リスク率）。
    ファイル不在・読み込み失敗・不正値は、キーごとに DEFAULT_PORTFOLIO_CONFIG にフォールバックする。
    """
    import yaml

    cfg_path = path if path is not None else _PORTFOLIO_CONFIG_PATH
    result: dict[str, Any] = dict(DEFAULT_PORTFOLIO_CONFIG)
    if not cfg_path.exists():
        logger.warning(
            "strategy_config.yaml が見つからないため、資金配分は既定値を使用します（max_positions=%d）",
            _DEFAULT_MAX_POSITIONS,
        )
        return result
    try:
        with open(cfg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        logger.warning(
            "strategy_config.yaml の読み込みに失敗したため、資金配分は既定値を使用します"
            "（max_positions=%d）",
            _DEFAULT_MAX_POSITIONS,
            exc_info=True,
        )
        return result
    if not isinstance(data, dict):
        logger.debug(
            "strategy_config.yaml のルートが dict でないため、資金配分は既定値を使用します"
        )
        return result
    p = data.get("portfolio")
    if not isinstance(p, dict):
        logger.debug(
            "portfolio セクションが存在しないか dict でないため、資金配分は既定値を使用します"
        )
        return result

    checks: dict[str, Callable[[object], bool]] = {
        "max_positions": _valid_max_positions,
        "allocation_method": lambda v: v in VALID_ALLOCATION_METHODS,
        "max_position_pct": lambda v: _valid_ratio(v, allow_one=True),
        "max_utilization": lambda v: _valid_ratio(v, allow_one=True),
        "risk_pct": lambda v: _valid_ratio(v, allow_one=False),
    }
    for key, is_valid in checks.items():
        v = p.get(key)
        if v is None:
            logger.debug("portfolio.%s が未設定のため、既定値 %r を使用します", key, result[key])
            continue
        if not is_valid(v):
            logger.warning(
                "portfolio.%s=%r は無効な値のため、既定値 %r を使用します", key, v, result[key]
            )
            continue
        result[key] = (
            int(v) if key == "max_positions" else (v if key == "allocation_method" else float(v))
        )
    return result


def apply_holding_limits(
    candidates: list[dict],
    current_positions: dict[str, int],
    price_map: dict[str, float],
    portfolio_value: float,
    available_cash: float,
    max_positions: int,
    max_utilization: float,
    sell_codes: set[str] | None = None,
) -> tuple[list[dict], float]:
    """保有全体に対する上限（保有銘柄数・投資割合）を BUY 候補と使える現金に反映する（Issue #437）。

    - 保有銘柄数: 既に保有している銘柄（売却予定を除く）を数え、空き枠の数だけ新規銘柄を残す。
      保有中の銘柄の候補（買い増し）は枠を使わないので残す。売却予定の銘柄の候補は除く。
    - 投資割合: 保有中の時価合計を差し引いた残り（総資産 × max_utilization − 保有時価）を
      使える現金の上限にする。

    保有銘柄の価格が分からない場合は、投資額を見積もれないため新規の買付をすべて止める（保守側）。

    Args:
        candidates:        スコア順に並んだ BUY 候補 [{code, score, signal_rank}, ...]
        current_positions: 現在の保有 {code: shares}
        price_map:         {code: price}（保有銘柄の時価評価に使う）
        portfolio_value:   総資産（円）
        available_cash:    使える現金（円）
        max_positions:     保有銘柄数の上限
        max_utilization:   保有全体の投資割合の上限（総資産比）
        sell_codes:        翌日売却予定の銘柄。保有数・投資額から除く。

    Returns:
        (上限を反映した候補, 上限を反映した使える現金)
    """
    excluded = sell_codes or set()
    held = {
        code for code, shares in current_positions.items() if shares > 0 and code not in excluded
    }

    invested = 0.0
    missing = sorted(code for code in held if not (price_map.get(code) or 0) > 0)
    if missing:
        logger.warning(
            "apply_holding_limits: 保有銘柄 %s の価格が分からないため、新規の買付を見送ります",
            ", ".join(missing),
        )
        return [], 0.0
    for code in held:
        invested += current_positions[code] * price_map[code]

    room = max(0.0, portfolio_value * max_utilization - invested)
    capped_cash = max(0.0, min(available_cash, room))

    slots = max(0, max_positions - len(held))
    out: list[dict] = []
    for c in candidates:
        code = c["code"]
        if code in excluded:
            continue
        if code in held:
            out.append(c)
        elif slots > 0:
            out.append(c)
            slots -= 1
    return out, capped_cash


def select_candidates(
    buy_signals: list[dict],
    max_positions: int = 10,
) -> list[dict]:
    """BUY シグナルをスコア降順に並べ、上位 max_positions 件を返す。

    Args:
        buy_signals: [{"code": str, "signal_rank": int, "score": float}, ...]
        max_positions: 最大保有銘柄数（PortfolioConstruction.md 推奨: 5〜15）

    Returns:
        スコア降順の候補リスト（重みなし）。
    """
    if not buy_signals:
        return []
    # score 降順、同点時は signal_rank 昇順（小さい方が優先）でタイブレーク
    sorted_signals = sorted(
        buy_signals,
        key=lambda s: (-s.get("score", 0.0), s.get("signal_rank", 0)),
    )
    return sorted_signals[:max_positions]


def calc_equal_weights(candidates: list[dict]) -> dict[str, float]:
    """等金額配分の重みを返す。

    Args:
        candidates: [{code, score, signal_rank}, ...]

    Returns:
        {code: weight}。candidates が空なら {}。各重みは 1/N。
    """
    if not candidates:
        return {}
    n = len(candidates)
    return {c["code"]: 1.0 / n for c in candidates}


def calc_score_weights(candidates: list[dict]) -> dict[str, float]:
    """スコア加重配分の重みを返す。

    weight_i = score_i / sum(scores)。
    全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックし WARNING を出す。

    Args:
        candidates: [{code, score, signal_rank}, ...]

    Returns:
        {code: weight}。candidates が空なら {}。
    """
    if not candidates:
        return {}

    total = sum(c.get("score", 0.0) for c in candidates)
    if total <= 0.0:
        logger.warning("calc_score_weights: 全銘柄のスコアが 0.0。等金額配分にフォールバック。")
        return calc_equal_weights(candidates)

    return {c["code"]: c.get("score", 0.0) / total for c in candidates}
