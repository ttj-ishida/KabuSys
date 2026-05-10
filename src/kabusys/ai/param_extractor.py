"""param_extractor.py — AI 返答テキストから JSON ブロックを抽出・ホワイトリスト検証する。"""

from __future__ import annotations

import json
import logging
import re

_logger = logging.getLogger(__name__)

ALLOWED_KEYS = frozenset(
    {
        "weights",
        "threshold",
        "sector_boost",
        "sector_quartile",
        "stop_loss_rate",
        "trailing_stop_atr_mult",
        "gap_up_threshold",
        "gap_down_threshold",
        "min_holding_days",
        "max_holding_days",
        "topix_drawdown_threshold",
        "topix_size_multiplier_bear",
    }
)

ALLOWED_WEIGHT_KEYS = frozenset(
    {
        "momentum",
        "value",
        "volatility",
        "liquidity",
        "news",
    }
)

_VALUE_RANGES: dict[str, tuple[float, float]] = {
    "threshold": (0.0, 1.0),
    "sector_boost": (0.0, 1.0),
    "sector_quartile": (0.01, 0.99),
    "stop_loss_rate": (-1.0, -0.001),
    "trailing_stop_atr_mult": (0.1, 10.0),
    "gap_up_threshold": (0.0, 1.0),
    "gap_down_threshold": (-1.0, 0.0),
    "min_holding_days": (0.0, 365.0),
    "max_holding_days": (1.0, 365.0),
    "topix_drawdown_threshold": (-1.0, -0.001),
    "topix_size_multiplier_bear": (0.01, 1.0),
}

_INT_KEYS = frozenset({"min_holding_days", "max_holding_days"})


def extract_params(text: str) -> dict | None:
    """AI 返答テキストの ```json ... ``` ブロックを抽出し、ホワイトリスト検証済み dict を返す。

    - JSON ブロックが存在しない場合は None。
    - 複数ブロックがある場合は最後のブロックを使用する。
    - ホワイトリスト外キーはそのキーのみ除外し警告ログを出す。
    - weights は ALLOWED_WEIGHT_KEYS のキーのみ許可。
    - 値域外の値はそのキーを除外し警告ログを出す。
    - 有効なキーが 1 つも残らない場合は None。
    """
    blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not blocks:
        return None

    try:
        data = json.loads(blocks[-1])
    except (json.JSONDecodeError, TypeError):
        _logger.warning("extract_params: JSON パースに失敗しました")
        return None

    if not isinstance(data, dict):
        _logger.warning("extract_params: JSON がオブジェクトではありません")
        return None

    result: dict = {}

    for key, value in data.items():
        if key not in ALLOWED_KEYS:
            _logger.warning("extract_params: ホワイトリスト外キーを除外: %s", key)
            continue

        if key == "weights":
            if not isinstance(value, dict):
                _logger.warning("extract_params: weights の値が dict ではありません")
                continue
            filtered: dict = {}
            for wk, wv in value.items():
                if wk not in ALLOWED_WEIGHT_KEYS:
                    _logger.warning("extract_params: 未知の weight キーを除外: %s", wk)
                    continue
                if (
                    not isinstance(wv, (int, float))
                    or isinstance(wv, bool)
                    or not (0.0 <= float(wv) <= 1.0)
                ):
                    _logger.warning("extract_params: weight 値が値域外: %s=%s", wk, wv)
                    continue
                filtered[wk] = float(wv)
            if filtered:
                result["weights"] = filtered
            continue

        lo, hi = _VALUE_RANGES[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            _logger.warning("extract_params: 数値でない値を除外: %s=%s", key, value)
            continue

        if key in _INT_KEYS:
            if isinstance(value, float) and value != int(value):
                _logger.warning(
                    "extract_params: 整数でない float を除外: %s=%s", key, value
                )
                continue
            v: int | float = int(value)
        else:
            v = float(value)
        if not (lo <= float(v) <= hi):
            _logger.warning(
                "extract_params: 値域外の値を除外: %s=%s (範囲: %s〜%s)", key, v, lo, hi
            )
            continue
        result[key] = v

    return result if result else None
