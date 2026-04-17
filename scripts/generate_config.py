# scripts/generate_config.py
"""config/*.yaml テンプレートを生成するスクリプト。

使い方:
    python scripts/generate_config.py               # 存在しないファイルのみ生成
    python scripts/generate_config.py --overwrite   # 既存ファイルを上書き

documents/01_Data/config_schema.md に沿った安全側（保守的）な初期値を使用する。
"""
from __future__ import annotations

import argparse
import sys
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
  name: momentum_strategy
  universe_size: 500
  rebalance_frequency: daily

factors:
  momentum_20_weight: 0.5
  momentum_60_weight: 0.3
  volume_factor_weight: 0.2

ai_overlay:
  enabled: true
  # AIオーバーレイの影響度上限（RiskManagement.md §6 に準拠）
  max_influence: 0.10
""",
    "risk_config.yaml": """\
# risk_config.yaml — リスク管理設定（安全側の初期値）
risk:
  # 1銘柄最大ウェイト（ポートフォリオ対比）
  max_position_size: 0.05
  # ポートフォリオ総投資比率上限
  max_portfolio_exposure: 1.0
  # 日次最大損失率（超過で Kill Switch 検討）
  max_daily_loss: 0.02
  # 最大ドローダウン（超過で Kill Switch 自動発動）
  max_drawdown: 0.15

position_sizing:
  risk_per_trade: 0.01
  volatility_adjustment: true
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
    parser = argparse.ArgumentParser(
        description="config/*.yaml テンプレートを生成する"
    )
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
