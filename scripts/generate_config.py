# scripts/generate_config.py
"""config/*.yaml テンプレートを生成するスクリプト。

使い方:
    python scripts/generate_config.py               # 存在しないファイルのみ生成
    python scripts/generate_config.py --overwrite   # 既存ファイルを上書き

documents/01_Data/config_schema.md に沿った安全側（保守的）な初期値を使用する。
"""

from __future__ import annotations

import argparse
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _PROJECT_ROOT / "config"

# ---------------------------------------------------------------------------
# テンプレート定義（config_schema.md §3〜§8 に準拠、安全側の初期値）
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, str] = {
    "system_config.yaml": """\
# system_config.yaml — システム全体設定
# 環境: development / paper_trading / live
environment: development

timezone: Asia/Tokyo

data_directory: data/

log_directory: logs/

database:
  type: duckdb
  path: data/kabusys.duckdb

calendar:
  source: jquants
  table: market_calendar
""",
    "data_config.yaml": """\
# data_config.yaml — データ取得設定
market_data:
  provider: jquants
  price_table: prices_daily
  fundamental_table: fundamentals

news_data:
  provider: yahoo_news
  table: news_articles

feature_store:
  table: features

ai_scores:
  table: ai_scores
""",
    "strategy_config.yaml": """\
# strategy_config.yaml — 売買戦略パラメータ
strategy:
  weights:
    momentum: 0.40
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
  threshold: 0.60
  stop_loss_rate: -0.08
  min_holding_days: 5
  max_holding_days: 60
  trailing_stop_atr_mult: 2.0
  reentry_cooldown_days: 5
  gap_up_threshold: 0.05
  gap_down_threshold: -0.03
value_score:
  weights:
    per: 0.50
    pbr: 0.30
    div_yield: 0.20
  normalization:
    per_mid: 20.0
    pbr_mid: 1.5
    div_yield_max: 3.0
""",
    "risk_config.yaml": """\
# risk_config.yaml — リスク管理設定
# キー名は RiskConfig データクラスのフィールド名に対応する
risk:
  # 1銘柄最大投資比率（総資産比）。max_utilization 以下に設定すること
  max_position_pct: 0.20
  # 全ポジション投下上限（現金最低20%維持）
  max_utilization: 0.80
  # キルスイッチ発動ドローダウン閾値
  max_drawdown: 0.20
  # API レート制限（毎秒）
  rate_limit_per_sec: 5
  # サーキットブレーカー発動エラー数上限
  circuit_breaker_errors: 10
  # サーキットブレーカーカウントウィンドウ（秒）
  circuit_breaker_window_sec: 60
""",
    "execution_config.yaml": """\
# execution_config.yaml — 発注システム設定
broker:
  api: kabu_station
  account_type: margin
  retry_attempts: 3

execution:
  order_type: limit
  slippage: 0.001
  timeout_seconds: 10

signal_queue:
  table: signal_queue
  polling_interval_seconds: 5
""",
    "monitoring_config.yaml": """\
# monitoring_config.yaml — 監視設定
monitoring:
  dashboard: streamlit

alerts:
  line_enabled: true
  max_drawdown_alert: 0.10
  execution_failure_alert: true

logging:
  level: INFO
  database: data/monitoring.db
""",
}


def generate(overwrite: bool = False) -> int:
    """テンプレートを config/ に生成する。生成したファイル数を返す。"""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    for filename, content in _TEMPLATES.items():
        path = _CONFIG_DIR / filename
        if path.exists() and not overwrite:
            print(f"  SKIP    config/{filename} (既存・--overwrite で上書き可)")
            continue
        already_exists = path.exists()
        path.write_text(content, encoding="utf-8")
        action = "OVERWRITE" if already_exists else "CREATE  "
        print(f"  {action} config/{filename}")
        generated += 1
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="config/*.yaml テンプレートを生成する")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="既存ファイルを上書きする（デフォルト: スキップ）",
    )
    args = parser.parse_args()

    print(f"config/ テンプレートを生成します: {_CONFIG_DIR}")
    count = generate(overwrite=args.overwrite)
    print(f"完了: {count} ファイルを生成しました。")
    if count == 0 and not args.overwrite:
        print("ヒント: 既存ファイルを上書きする場合は --overwrite を指定してください。")


if __name__ == "__main__":
    main()
