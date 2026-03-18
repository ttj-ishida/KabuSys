"""特徴量ユーティリティの公開インターフェース。

data.stats モジュールの zscore_normalize を再エクスポートする。
"""

from kabusys.data.stats import zscore_normalize

__all__ = ["zscore_normalize"]
