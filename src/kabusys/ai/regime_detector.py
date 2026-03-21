"""
市場レジーム判定モジュール

ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と
マクロ経済ニュースの LLM センチメント（重み30%）を合成して
市場レジーム（'bull' / 'neutral' / 'bear'）を日次で判定する。

処理フロー:
  1. API キー解決（引数 or 環境変数 OPENAI_API_KEY）
  2. prices_daily から 1321 の終値を取得し ma200_ratio を計算
  3. raw_news からマクロキーワードでフィルタしたタイトルを取得
  4. OpenAI API（gpt-4o-mini）でマクロセンチメントを評価（記事あり時のみ）
  5. レジームスコアを合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
  6. market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）

設計方針:
  - datetime.today() / date.today() を参照しない（ルックアヘッドバイアス防止）
  - prices_daily クエリは date < target_date の排他条件でルックアヘッドを防止
  - API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）
  - OpenAI 呼び出し関数は news_nlp からインポートせず独自実装（モジュール結合防止）
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date
from typing import Any

import duckdb
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from kabusys.ai.news_nlp import calc_news_window

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_ETF_CODE: str = "1321"
_MA_WINDOW: int = 200
_MA_SCALE: float = 10.0
_MA_WEIGHT: float = 0.7
_MACRO_WEIGHT: float = 0.3
_BULL_THRESHOLD: float = 0.2
_BEAR_THRESHOLD: float = 0.2
_MAX_MACRO_ARTICLES: int = 20
_MODEL: str = "gpt-4o-mini"
_MAX_RETRIES: int = 3
_RETRY_BASE_SECONDS: float = 1.0

_MACRO_KEYWORDS: list[str] = [
    # 日本
    "日銀", "日本銀行", "金利", "利上げ", "利下げ", "政策金利",
    "為替", "円安", "円高", "為替介入", "インフレ", "物価", "GDP",
    # 米国・グローバル
    "Fed", "FOMC", "CPI", "PPI", "雇用統計", "失業率",
    "米国債", "リセッション", "景気後退",
]

_SYSTEM_PROMPT = (
    "あなたは日本株の市場アナリストです。"
    "以下のマクロ経済ニュースを読み、日本株市場全体のセンチメントを "
    "-1.0〜1.0 のスコアで評価してください。"
    "1.0=非常にポジティブ（強気）、0.0=中立、-1.0=非常にネガティブ（弱気）。"
    '出力は厳密なJSONのみとしてください: {"macro_sentiment": 0.0}'
)


# ---------------------------------------------------------------------------
# 内部関数
# ---------------------------------------------------------------------------

def _calc_ma200_ratio(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> float:
    """ETF 1321 の直近 _MA_WINDOW 日の終値から 200 日 MA 乖離を計算する。

    ルックアヘッドバイアス防止のため target_date 未満（排他）のデータのみ使用。
    データが _MA_WINDOW 日未満の場合は 1.0（中立）を返し WARNING ログを出す。

    Returns:
        ma200_ratio: 最新終値 / 200 日単純移動平均。中立時は 1.0。
    """
    rows = conn.execute(
        """
        SELECT close FROM prices_daily
        WHERE code = ? AND date < ?
        ORDER BY date DESC LIMIT ?
        """,
        [_ETF_CODE, target_date, _MA_WINDOW],
    ).fetchall()

    if not rows:
        logger.warning(
            "_calc_ma200_ratio: 1321 のデータなし target_date=%s, ma200_ratio=1.0 を使用",
            target_date,
        )
        return 1.0

    if len(rows) < _MA_WINDOW:
        logger.warning(
            "_calc_ma200_ratio: データ不足 %d 日 (必要: %d), ma200_ratio=1.0 を使用",
            len(rows),
            _MA_WINDOW,
        )
        return 1.0

    closes = [float(r[0]) for r in rows]
    # rows は DESC 順（最新が先頭）
    latest_close = closes[0]
    ma200 = sum(closes) / len(closes)
    return latest_close / ma200
