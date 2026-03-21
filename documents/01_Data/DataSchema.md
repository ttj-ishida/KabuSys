# DataSchema.md

## 1. 目的

本ドキュメントは、日本株自動売買システムで使用する
**データスキーマ（Data Schema）** を定義する。

目的:

-   データ保存構造の統一
-   バックテスト再現性の確保
-   戦略・AI・Execution間のデータ連携
-   データ品質管理

本システムでは以下を前提とする。

-   データ保存: **Parquet**
-   分析DB: **DuckDB**
-   単一Windowsノード構成

------------------------------------------------------------------------

# 2. データレイヤー

データは3層構造で管理する。

    Raw Layer
    ↓
    Processed Layer
    ↓
    Feature Layer

  Layer       内容
  ----------- --------------------
  Raw         取得したデータ
  Processed   整形済み市場データ
  Feature     戦略・AI用特徴量

------------------------------------------------------------------------

# 3. 市場データ

## prices_daily

日足株価データ。

  column     type     description
  ---------- -------- -------------
  date       date     取引日
  code       string   銘柄コード
  open       float    始値
  high       float    高値
  low        float    安値
  close      float    終値
  volume     float    出来高
  turnover   float    売買代金

主キー

    (date, code)

------------------------------------------------------------------------

# 4. カレンダーデータ

## market_calendar

JPXのカレンダー情報（祝日・半休・SQ等）。

  column           type     description
  ---------------- -------- --------------------
  date             date     日付
  is_trading_day   boolean  営業日フラグ
  is_half_day      boolean  半日取引フラグ
  is_sq_day        boolean  メジャーSQフラグ
  holiday_name     string   祝日名

取得元: J-Quants

------------------------------------------------------------------------

# 5. 財務データ

## fundamentals

  column             type     description
  ------------------ -------- -------------
  code               string   銘柄コード
  report_date        date     決算日
  revenue            float    売上
  operating_profit   float    営業利益
  net_income         float    純利益
  eps                float    EPS
  roe                float    ROE

------------------------------------------------------------------------

# 5. ニュースデータ

## news_articles

  column     type        description
  ---------- ----------- --------------
  id         string      記事ID
  datetime   timestamp   記事時刻
  source     string      ニュース媒体
  title      string      タイトル
  content    text        本文
  url        string      記事URL

------------------------------------------------------------------------

# 6. ニュース銘柄マッピング

## news_symbols

  column    type     description
  --------- -------- -------------
  news_id   string   記事ID
  code      string   銘柄コード

------------------------------------------------------------------------

# 7. AIスコア

## ai_scores

銘柄ごとのAI分析結果。

  column            type     description
  ----------------- -------- ----------------------------------------
  date              date     評価日
  code              string   銘柄コード
  sentiment_score   float    ニュースセンチメント（score_news が生成）
  regime_score      float    市場レジーム（現在は NULL。market_regime を参照）
  ai_score          float    総合AIスコア

注: regime_score は market_regime テーブルで管理する設計に変更。
    ai_scores.regime_score カラムは将来の拡張用として保持するが現在は使用しない。

------------------------------------------------------------------------

## market_regime

市場全体のレジーム判定結果（日次・1行）。score_regime() が生成。

  column            type      description
  ----------------- --------- ------------------------------------------
  date              date      判定日（PRIMARY KEY）
  regime_score      float     市場レジームスコア（-1.0〜1.0）
  regime_label      string    'bull' / 'neutral' / 'bear'
  ma200_ratio       float     ETF1321終値 / 200日移動平均（診断用）
  macro_sentiment   float     LLMマクロニューススコア（診断用）
  created_at        timestamp 書込み日時

判定ロジック:
  regime_score = clip(0.7 * (ma200_ratio - 1.0) * 10 + 0.3 * macro_sentiment, -1, 1)
  score >= +0.2 → 'bull'（積極的な買い戦略を許可）
  score <= -0.2 → 'bear'（新規買いシグナルを全遮断）
  それ以外      → 'neutral'

------------------------------------------------------------------------

# 8. 特徴量

## features

戦略用ファクター。

  column          type     description
  --------------- -------- ----------------
  date            date     日付
  code            string   銘柄コード
  momentum_20     float    20日モメンタム
  momentum_60     float    60日モメンタム
  volatility_20   float    20日ボラ
  volume_ratio    float    出来高比率

------------------------------------------------------------------------

# 9. シグナル

## signals

戦略が生成する売買シグナル。

  column   type     description
  -------- -------- -------------
  date     date     取引日
  code     string   銘柄
  side     string   buy / sell
  score    float    戦略スコア
  rank     int      ランキング

------------------------------------------------------------------------

# 10. シグナルキュー

## signal_queue

Executionへ引き渡すための冪等な発注指示キュー。

  column         type        description
  -------------- ----------- --------------------------
  signal_id      string      シグナル一意のID
  date           date        取引日
  code           string      銘柄コード
  side           string      buy/sell
  size           int         株数
  order_type     string      成行/指値等の種別
  price          float       指値価格（成行時はnull等）
  status         string      処理状態
  created_at     timestamp   作成日時
  processed_at   timestamp   処理完了日時

状態（status）の遷移:

    pending
    processing
    executed
    cancelled
    error

Executionの処理フロー:
1. `SELECT * FROM signal_queue WHERE status = 'pending'`
2. `UPDATE ... SET status = 'processing' WHERE signal_id = ? (Lock)`
3. broker API へ発注
4. `UPDATE ... SET status = 'executed'`

------------------------------------------------------------------------

# 11. ポートフォリオ

## portfolio_targets

発注前ポートフォリオ。

  column          type     description
  --------------- -------- --------------
  date            date     日付
  code            string   銘柄
  target_weight   float    目標ウェイト
  target_size     int      株数

------------------------------------------------------------------------

# 11. 注文

## orders

  column     type        description
  ---------- ----------- -------------
  order_id   string      注文ID
  datetime   timestamp   注文時刻
  code       string      銘柄
  side       string      buy/sell
  size       int         株数
  price      float       指値
  status     string      状態

状態例

    created
    sent
    filled
    cancelled
    rejected

------------------------------------------------------------------------

# 12. 約定

## trades

  column     type        description
  ---------- ----------- -------------
  trade_id   string      約定ID
  order_id   string      注文ID
  datetime   timestamp   約定時刻
  code       string      銘柄
  price      float       約定価格
  size       int         約定株数

------------------------------------------------------------------------

# 13. ポジション

## positions

  column          type     description
  --------------- -------- --------------
  date            date     日付
  code            string   銘柄
  position_size   int      保有株数
  avg_price       float    平均取得価格
  market_value    float    評価額

------------------------------------------------------------------------

# 14. パフォーマンス

## portfolio_performance

  column         type    description
  -------------- ------- --------------
  date           date    日付
  equity         float   総資産
  cash           float   現金
  drawdown       float   ドローダウン
  daily_return   float   日次リターン

------------------------------------------------------------------------

# 15. データフロー

    Market Data / News
    ↓
    prices_daily / news_articles
    ↓
    features / ai_scores
    ↓
    signals
    ↓
    portfolio_targets
    ↓
    orders
    ↓
    trades
    ↓
    positions
    ↓
    portfolio_performance

------------------------------------------------------------------------

# 16. まとめ

本データスキーマは以下の領域をカバーする。

-   市場データ
-   AIデータ
-   戦略データ
-   執行データ
-   ポートフォリオデータ

この構造により
**バックテスト・研究・実運用を同一データ基盤で管理**できる。
