"""
統計ユーティリティモジュール

data / research 双方から参照される汎用統計関数を提供する。
外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装する。
"""

from __future__ import annotations

from typing import Any


def zscore_normalize(
    records: list[dict[str, Any]],
    columns: list[str],
) -> list[dict[str, Any]]:
    """指定カラムを Zスコア正規化する（クロスセクション）。

    各カラムについて mean/std をクロスセクション（全銘柄）で計算し、
    (value - mean) / std に変換する。母標準偏差（n 分母）を使用する。

    std が 0 またはレコードが 1 件以下の場合は元の値を維持する。
    None 値はスキップして計算し、正規化後も None を返す。

    Args:
        records: ファクター計算関数の戻り値リスト。各要素はフラットな dict。
        columns: 正規化対象のカラム名リスト。

    Returns:
        正規化済みのレコードリスト（元のリストを変更しない）。
    """
    # フラットな dict のため浅いコピーで十分（deepcopy より軽量）
    result = [r.copy() for r in records]

    for col in columns:
        values = [r[col] for r in result if r.get(col) is not None]
        if len(values) <= 1:
            continue
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        if std == 0:
            continue
        for r in result:
            if r.get(col) is not None:
                r[col] = (r[col] - mean) / std

    return result
