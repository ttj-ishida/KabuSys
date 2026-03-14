# ConfigSchema.md

## 1. 目的

本ドキュメントは、日本株自動売買システムで使用する
**設定ファイル（Configuration）スキーマ** を定義する。

目的:

-   システム設定の一元管理
-   環境依存パラメータの分離
-   Strategy / Risk / Execution のパラメータ管理
-   実装変更なしでの設定変更

設定ファイルは **YAML形式** を採用する。

理由:

-   可読性が高い
-   Pythonとの親和性が高い
-   Git管理に適している

------------------------------------------------------------------------

# 2. 設定ファイル構成

    config/
    │
    ├ system_config.yaml
    ├ data_config.yaml
    ├ strategy_config.yaml
    ├ risk_config.yaml
    ├ execution_config.yaml
    └ monitoring_config.yaml

------------------------------------------------------------------------

# 3. system_config.yaml

システム全体設定。

``` yaml
environment: production

timezone: Asia/Tokyo

data_directory: data/

log_directory: logs/

database:
  type: duckdb
  path: data/trading.db

calendar:
  source: jquants
  table: market_calendar
```

説明

  key              description
  ---------------- ------------------------
  environment      実行環境
  timezone         タイムゾーン
  data_directory   データ保存ディレクトリ
  log_directory    ログディレクトリ
  database         DB設定
  calendar         JPXカレンダー設定

------------------------------------------------------------------------

# 4. data_config.yaml

データ取得設定。

``` yaml
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
```

------------------------------------------------------------------------

# 5. strategy_config.yaml

売買戦略パラメータ。

``` yaml
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
  max_influence: 0.10
```

説明

  key                   description
  --------------------- --------------------
  universe_size         投資対象銘柄数
  rebalance_frequency   リバランス頻度
  factors               ファクターウェイト
  ai_overlay            AIシグナル設定

------------------------------------------------------------------------

# 6. risk_config.yaml

リスク管理設定。

``` yaml
risk:

  max_position_size: 0.05

  max_portfolio_exposure: 1.0

  max_daily_loss: 0.02

  max_drawdown: 0.15

position_sizing:

  risk_per_trade: 0.01

  volatility_adjustment: true
```

説明

  key                      description
  ------------------------ -----------------
  max_position_size        1銘柄最大比率
  max_portfolio_exposure   総投資比率
  max_daily_loss           日次最大損失
  max_drawdown             最大DD
  risk_per_trade           1トレードリスク

------------------------------------------------------------------------

# 7. execution_config.yaml

発注システム設定。

``` yaml
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
```

説明

  key                        description
  -------------------------- ------------------
  api                        証券API
  retry_attempts             リトライ回数
  slippage                   想定スリッページ
  polling_interval_seconds   シグナル取得間隔

------------------------------------------------------------------------

# 8. monitoring_config.yaml

監視設定。

``` yaml
monitoring:

  dashboard: streamlit

alerts:

  slack_enabled: true

  max_drawdown_alert: 0.10

  execution_failure_alert: true

logging:

  level: INFO

  database: monitoring.db
```

------------------------------------------------------------------------

# 9. 設定読み込みインターフェース

Python例

``` python
import yaml

def load_config(path):

    with open(path) as f:
        return yaml.safe_load(f)
```

------------------------------------------------------------------------

# 10. 設定変更ポリシー

設定変更は以下ルールに従う。

1.  YAMLのみ変更
2.  Gitでバージョン管理
3.  変更履歴を残す

例

    git commit -m "change strategy parameters"

------------------------------------------------------------------------

# 11. 環境分離

将来拡張として

    config/
       production/
       staging/
       research/

を用意することも可能。

------------------------------------------------------------------------

# 12. まとめ

Config Schemaは以下を管理する。

-   システム設定
-   データ設定
-   戦略パラメータ
-   リスク制御
-   発注設定
-   監視設定

この構造により **コード変更なしで安全なシステム運用**が可能になる。
