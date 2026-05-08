"""core/interfaces — Core が Addon に公開する接続点の定義。"""

from __future__ import annotations

import duckdb

from kabusys.core.interfaces.regime import (
    DatabaseRegimeProvider,
    NullRegimeProvider,
    RegimeProvider,
)

__all__ = [
    "RegimeProvider",
    "NullRegimeProvider",
    "DatabaseRegimeProvider",
    "build_regime_provider",
]


def build_regime_provider(
    conn: duckdb.DuckDBPyConnection | None,
    enabled: bool,
) -> RegimeProvider:
    """ENABLE_AI_SENTIMENT フラグに基づいて RegimeProvider を返す。"""
    if enabled:
        if conn is None:
            raise ValueError("enabled=True の場合は conn が必要です。")
        return DatabaseRegimeProvider(conn)
    return NullRegimeProvider()
