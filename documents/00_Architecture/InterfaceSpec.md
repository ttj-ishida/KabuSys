# InterfaceSpec.md

## 1. 目的

本ドキュメントは、日本株自動売買システムにおける
**モジュール間インターフェース仕様** を定義する。

目的:

-   各コンポーネント間のデータ受け渡しを明確化
-   実装時の依存関係を整理
-   Strategy / AI / Portfolio / Execution の結合を緩くする
-   将来的なモジュール差し替えを容易にする

対象コンポーネント:

-   Data Platform
-   Feature / Strategy
-   AI Model
-   Portfolio Construction
-   Execution Engine
-   Monitoring

------------------------------------------------------------------------

# 2. 全体インターフェース構造

システムは以下のデータインターフェースで接続される。

    Data Platform
        ↓
    Feature / Strategy
        ↓
    AI Model (overlay)
        ↓
    Strategy Signals
        ↓
    Portfolio Construction
        ↓
    Signal Queue
        ↓
    Execution Engine
        ↓
    Broker API

各コンポーネントは **ファイル /
テーブルベースのインターフェース**で接続する。

------------------------------------------------------------------------

# 3. Data → Strategy

## Input

    prices_daily
    features
    ai_scores

## Interface

``` python
def load_market_data(date: str) -> DataFrame:
    """
    指定日の市場データを取得
    """
```

Output

    DataFrame
    index: code
    columns:
        close
        volume
        momentum_20
        volatility_20
        ai_score

------------------------------------------------------------------------

# 4. Strategy → Portfolio

Strategy Engine は売買候補銘柄を出力する。

## Interface

``` python
def generate_signals(date: str) -> DataFrame:
    """
    売買シグナルを生成
    """
```

Output schema

  column   description
  -------- -------------
  date     取引日
  code     銘柄
  side     buy/sell
  score    戦略スコア
  rank     ランキング

保存先

    signals_table
    または
    signals.parquet

------------------------------------------------------------------------

# 5. Portfolio → Execution

Portfolio Construction は **発注可能なポートフォリオ**を生成する。

## Interface

``` python
def build_portfolio(signals: DataFrame, capital: float) -> DataFrame:
    """
    シグナルからポートフォリオを生成
    """
```

Output schema

  column        description
  ------------- ----------------
  date          日付
  code          銘柄
  target_size   株数
  order_type    market / limit
  price         指値

保存先

    signal_queue

------------------------------------------------------------------------

# 6. Signal Queue → Execution

Execution Engine は **Pull型**でSignal Queueを読み込む。

## Interface

``` python
def fetch_pending_orders() -> DataFrame:
    """
    未処理シグナルを取得
    """
```

Signal Queue schema

  column         description
  -------------- -----------------------------
  signal_id      シグナルID
  date           日付
  code           銘柄
  side           buy/sell
  size           株数
  price          指値
  order_type     market/limit
  status         pending/processing/executed
  created_at     作成時刻
  processed_at   処理時刻

------------------------------------------------------------------------

# 7. Execution → Broker

Execution Engine は kabuステーションAPIを利用する。

## Interface

``` python
def send_order(order: dict) -> str:
    """
    発注処理
    return order_id
    """
```

Order payload

    {
        "code": "7203",
        "side": "buy",
        "qty": 100,
        "price": 2500,
        "order_type": "limit"
    }

------------------------------------------------------------------------

# 8. Execution → Monitoring

Execution Engine は状態を Monitoring に送信する。

## Interface

``` python
def log_trade_event(event: dict):
    """
    取引ログを保存
    """
```

保存テーブル

    orders
    trades
    positions

------------------------------------------------------------------------

# 9. Monitoring → Alert

異常検知時の通知インターフェース。

``` python
def send_alert(message: str):
    """
    Slack通知
    """
```

対象イベント

-   注文失敗
-   Execution停止
-   最大DD超過
-   API接続エラー

------------------------------------------------------------------------

# 10. Runtime Interface

Runtime Scheduler が各サービスを起動する。

    night_batch()
        ↓
    feature_generation()
        ↓
    ai_analysis()
        ↓
    generate_signals()
        ↓
    build_portfolio()
        ↓
    update_signal_queue()

Market Hours

    execution_loop()
    monitoring_loop()

------------------------------------------------------------------------

# 11. インターフェース設計原則

1.  **Loose Coupling**\
    各モジュールはデータファイル / DBテーブルで接続する

2.  **Fail Safe**\
    AIが停止してもStrategyは動作する

3.  **Idempotent**\
    同じ処理を複数回実行しても安全

4.  **Traceability**\
    すべての注文とシグナルはログで追跡可能

------------------------------------------------------------------------

# 12. まとめ

インターフェース設計は以下の構造を採用する。

    Data Platform
        ↓
    Strategy
        ↓
    Portfolio
        ↓
    Signal Queue
        ↓
    Execution
        ↓
    Broker

この設計により **モジュール独立性と安全な自動売買実行**を実現する。
