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

## raw_prices（Raw Layer）

J-Quants から取得した生の日足株価データ。差分 API・Bulk API どちらも本テーブルに保存する。

  column       type     description
  ------------ -------- -----------------------------------------
  date         date     取引日
  code         string   銘柄コード
  open         float    始値（調整前）
  high         float    高値（調整前）
  low          float    安値（調整前）
  close        float    終値（調整前）
  volume       bigint   出来高（調整前）
  turnover     float    売買代金
  adj_factor   float    分割調整係数（Bulk CSV の AdjFactor。差分APIは NULL）
  fetched_at   timestamp 取込日時

主キー: `(date, code)`
取得元: J-Quants `/equities/bars/daily`（差分 API・Bulk 共通）

> **API 仕様**: `date` または `code` パラメータが必須。全銘柄取得時は `date=YYYY-MM-DD` で
> 1日ずつ呼び出す。パラメータの日付形式は `YYYY-MM-DD`。

Bulk CSV カラムマッピング:
  Date → date, Code → code, O → open, H → high, L → low, C → close
  Vo → volume, Va → turnover, AdjFactor → adj_factor
  ※ UL・LL・AdjO/H/L/C/Vo は Raw には保存しない（prices_daily は調整前価格を使用）

------------------------------------------------------------------------

## prices_daily（Processed Layer）

日足株価データ（整形済み）。戦略・バックテスト・research が参照する。

  column     type     description
  ---------- -------- -------------
  date       date     取引日
  code       string   銘柄コード
  open       float    始値（調整前）
  high       float    高値（調整前）
  low        float    安値（調整前）
  close      float    終値（調整前）
  volume     bigint   出来高
  turnover   float    売買代金

主キー: `(date, code)`
投入元: `raw_prices` からの ETL コピー（NOT NULL・low<=high を検証後に UPSERT）

注: 調整価格（分割対応）は raw_prices.adj_factor を使って算出する。
    DataPlatform §6.1 の補正ルールを参照。

------------------------------------------------------------------------

# 4. 銘柄マスタ

## stocks

全上場銘柄のマスタ情報。毎日 UPSERT する。
セクター集中制限（PortfolioConstruction Section 8）で参照する。

  column      type       description
  ----------- ---------- -------------
  code        string     銘柄コード（PRIMARY KEY）
  name        string     銘柄名
  market      string     市場区分（'Prime' / 'Standard' / 'Growth' / 'Other'）
  sector      string     TSE 33業種名
  updated_at  timestamp  最終更新日時

取得元（差分 API）: J-Quants `/listed/info`
  "Code" → code, "CompanyName" → name
  "MarketCode" → market（"0111"→Prime, "0121"→Standard, "0131"→Growth）
  "Sector33CodeName" → sector

取得元（Bulk API）: `/equities/master`
  Code → code, CoName → name, MktNm → market, S33Nm → sector

------------------------------------------------------------------------

# 4b. カレンダーデータ

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

## raw_financials（Raw Layer）

J-Quants から取得した生の財務データ。

  column             type      description
  ------------------ --------- -------------
  code               string    銘柄コード
  report_date        date      開示日
  period_type        string    会計期間タイプ（1Q/2Q/3Q/FY 等）
  revenue            float     売上
  operating_profit   float     営業利益
  net_income         float     純利益
  eps                float     EPS（1株当たり利益）
  roe                float     ROE
  bps                float     BPS（1株純資産）※ Issue #185 追加
  fetched_at         timestamp 取込日時

主キー: `(code, report_date, period_type)`
取得元: J-Quants `/fins/summary`（差分 API・Bulk 共通）
  Code→code, DiscDate→report_date, CurPerType→period_type
  Sales→revenue, OP→operating_profit, NP→net_income, EPS→eps
  NP/Eq→roe（ROE列は存在しないため純利益÷純資産で算出）
  bps=NULL（/fins/summary に BPS 列なし）

> **API 仕様**: `date` または `code` パラメータが必須。全銘柄取得時は `date=YYYY-MM-DD` で
> 1日ずつ呼び出す。パラメータの日付形式は `YYYY-MM-DD`。

------------------------------------------------------------------------

## fundamentals（Processed Layer）

整形済み財務データ。戦略・research が参照する。

  column             type     description
  ------------------ -------- -------------
  code               string   銘柄コード
  report_date        date     決算日
  period_type        string   会計期間タイプ
  revenue            float    売上
  operating_profit   float    営業利益
  net_income         float    純利益
  eps                float    EPS
  roe                float    ROE

主キー: `(code, report_date, period_type)`
投入元: `raw_financials` からの ETL コピー

------------------------------------------------------------------------

## dividends

配当情報。J-Quants `/fins/dividend` から取得。

  column       type      description
  ------------ --------- ---------------------------------------
  code         string    銘柄コード
  pub_date     date      公告日（PRIMARY KEY の一部）
  ref_no       string    参照番号（PRIMARY KEY の一部）
  ex_date      date      権利落ち日（配当利回り集計の基準日）
  record_date  date      基準日
  pay_date     date      支払日
  div_rate     float     1株当たり配当金額（円）
  fetched_at   timestamp 取込日時

主キー: `(code, pub_date, ref_no)`
取得元（初回）: Bulk API `/fins/dividend` CSV（bootstrap）
取得元（差分）: `/fins/dividend` 差分 API（`run_dividends_etl()`）※ Issue #185 追加

> ⚠️ **プラン制限**: `/fins/dividend` は Standard プランでは利用不可（HTTP 403）。
> Premium プラン以上が必要。Standard プランでは `run_dividends_etl()` はスキップされ、
> `dividends` テーブルは Bootstrap CSV から投入済みのデータのみ保持する。

配当利回りの計算: `(直近12ヶ月の div_rate 合計 / close) × 100`（ex_date ベース集計）

------------------------------------------------------------------------

# 5b. 指数データ

## topix_daily（新規）

TOPIX 日足データ。以下の用途で使用する。

- `factor_research.calc_topix_relative()`: TOPIX 相対強度（Issue #257）の算出基準
- `feature_engineering.update_topix_ma()`: MA25/MA75/MA200 を計算して ma25/ma75/ma200 列に保存（Issue #349）
- `signal_generator._get_topix_size_multiplier()`: MA クロス判定（MA25/MA75/MA200）による発注サイズ縮小（Issue #349）

  column   type    description
  -------- ------- -----------
  date     date    取引日（PRIMARY KEY）
  open     float   始値
  high     float   高値
  low      float   安値
  close    float   終値
  ma25     float?  25 日移動平均（`update_topix_ma()` で事前計算、データ不足時 NULL）
  ma75     float?  75 日移動平均（同上）
  ma200    float?  200 日移動平均（同上）

取得元: Bulk API `/indices/bars/daily/topix`
  Date→date, O→open, H→high, L→low, C→close
  ma25/ma75/ma200 は `feature_engineering.update_topix_ma()` が日次バッチで補完する

------------------------------------------------------------------------

# 5c. Bootstrap 管理

## bootstrap_load_history

Bulk API からのファイル単位の処理状態を管理する。再実行時のスキップ制御に使用。

  column       type      description
  ------------ --------- -----------------------------------------
  file_key     string    Bulk API のファイルキー（PRIMARY KEY）
  endpoint     string    Bulk エンドポイント（例: /equities/bars/daily）
  file_name    string    ダウンロードファイル名
  status       string    pending / loaded / failed
  row_count    bigint    ロードしたレコード件数
  error_msg    string    失敗時のエラーメッセージ
  loaded_at    timestamp 処理完了日時

状態遷移:
  pending → loaded（正常完了）
  pending → failed（エラー）
  failed  → pending（手動リセット後に再実行）

------------------------------------------------------------------------

# 7. ニュースデータ

取得元: Yahoo News（RSS）。補助ニュース源として使用し、売買判断の主役にはしない。シグナルへの影響は AI スコア経由で最大 10% 以内に限定する。

## raw_news

収集したニュース記事の生データを保存するテーブル。`news_collector.py` が書き込む。Night Batch レポートの `UpdateCounts.raw_news` はこのテーブルの当日行数を集計する。

  column     type        description
  ---------- ----------- --------------
  id         string      記事ID
  datetime   timestamp   記事時刻
  source     string      ニュース媒体（例: Yahoo News）
  title      string      タイトル
  content    text        本文（RSS 要約。提供元規約に従い全文は保存しない）
  url        string      記事URL

> **注意**: テーブル名は `raw_news`。旧称 `news_articles` は廃止済み（Issue #286）。

------------------------------------------------------------------------

# 7b. 適時開示データ（Issue #198 / #199）

## raw_disclosures（Raw Layer）

TDnet 適時開示閲覧サービスおよび EDINET API から取得した開示情報を全件保存する。
「先に全件保存して後から参照する」方式。

  column          type      description
  --------------- --------- -------------------------------------------------------
  id              string    開示ID（PRIMARY KEY。TDnet: 開示番号 / EDINET: docID）
  disclosed_at    timestamp 開示日時（JST）
  code            string    銘柄コード（4桁。EDINET の場合は NULL: API は secCode（5桁: 4桁JPX + "0"）を返すが JPX コード変換は未実装）
  company_name    string    会社名
  title           string    開示表題
  document_url    string    開示資料URL / EDINET の xbrl/pdf URL
  document_type   string    書類種別（TDnet: 表題テキスト生値 / EDINET: docTypeCode 数値文字列 "120"〜"172"）
  source          string    'tdnet' / 'edinet'
  fetched_at      timestamp 取込日時

主キー: `(id)`
更新方式: `ON CONFLICT DO NOTHING`（同一 id の再取得は無視）
取得元(TDnet): 適時開示情報閲覧サービス（15:35 ジョブ）
取得元(EDINET): EDINET API v2 `/api/v2/documents.json`（15:40 ジョブ）

EDINET API v2 レスポンスフィールド補足（`edinet_collector.py` 実装対応）:
- `docTypeCode`: 書類種別コード（"120" 等）。実装で参照する正しいフィールド名（`docType` という名称ではない）
- `secCode`: 銘柄コード（5桁: 4桁 JPX コード + 末尾 "0"。例: `"49660"` → JPX `"4966"`）。現在の実装では `code=None` にマップ（変換未実装）
- `seqNumber`: 連番（`int` 型で返る）
- `withdrawalStatus`: "0" が有効書類、それ以外は取り下げ済み（除外対象）

------------------------------------------------------------------------

## disclosure_events（Processed Layer）

`raw_disclosures` を表題ベースのルールで分類したイベント評価テーブル。
ニュース NLP とは独立した「開示イベント評価」レイヤー。

  column           type      description
  ---------------- --------- -------------------------------------------------------
  id               string    PRIMARY KEY（= raw_disclosures.id）
  disclosed_at     timestamp 開示日時
  code             string    銘柄コード
  event_type       string    イベント分類（下表参照）
  event_score      float     ルールベーススコア（+1.0=ポジティブ / 0.0=中立 / -1.0=ネガティブ）
  buy_caution      boolean   新規買い注意フラグ（増資・訴訟等で True）
  hold_caution     boolean   保有継続注意フラグ
  review_required  boolean   要確認フラグ（下方修正・不祥事等）
  title            string    開示表題（参照用）
  source           string    'tdnet' / 'edinet'
  classified_at    timestamp 分類日時

主キー: `(id)`
更新方式: UPSERT（再分類時は上書き）

event_type 分類（初期対象）:

  event_type                  event_score  buy_caution  説明
  --------------------------- ------------ ------------ ---------------------------------
  earnings_report             0.0          False        決算短信（内容はNLPで評価）
  earnings_revision_up        +1.0         False        業績予想修正（上方）
  earnings_revision_down      -1.0         True         業績予想修正（下方）
  dividend_revision_up        +1.0         False        配当予想修正（増配）
  dividend_revision_down      -1.0         False        配当予想修正（減配）
  buyback                     +0.5         False        自己株式取得
  new_share_issuance          -0.5         True         株式発行・増資（希薄化）
  merger_acquisition          0.0          True         M&A / 資本業務提携（要確認）
  litigation_scandal          -1.0         True         訴訟・監理・不祥事系
  other                       0.0          False        上記以外

------------------------------------------------------------------------

# 8. ニュース銘柄マッピング

## news_symbols

  column    type     description
  --------- -------- -------------
  news_id   string   記事ID
  code      string   銘柄コード

------------------------------------------------------------------------

# 9. AIスコア

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

# 10. 特徴量

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
  topix_rel_20    double   TOPIX相対強度・20日（銘柄21日リターン − TOPIX21日リターン。Zスコア正規化済み）
  topix_rel_60    double   TOPIX相対強度・60日（銘柄63日リターン − TOPIX63日リターン。Zスコア正規化済み）
  quality_score   double   財務品質スコア（op_margin / rev_growth_yoy / profit_growth_yoy の正規化後平均）

注記: topix_rel_20 / topix_rel_60 / quality_score はZスコア正規化（±3クリップ）後の値を保存する。
      raw値ではないため、直接の財務数値とは異なる。

------------------------------------------------------------------------

# 11. シグナル

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

# 12. シグナルキュー

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
    filled
    cancelled
    error
    failed

- `pending`    : 発注待ち（初期状態）
- `processing` : 発注処理中（ExecutionEngine がロック中）
- `filled`     : 約定済み
- `cancelled`  : キャンセル済み
- `error`      : システムエラーによる失敗
- `failed`     : 手動で失敗マーク（`mark_signal_failed.py` で設定）

Executionの処理フロー:
1. `SELECT * FROM signal_queue WHERE status = 'pending'`
2. `UPDATE ... SET status = 'processing' WHERE signal_id = ? (Lock)`
3. broker API へ発注
4. 約定確認後 `UPDATE ... SET status = 'filled'`

------------------------------------------------------------------------

# 13. ポートフォリオ

## portfolio_targets

発注前ポートフォリオ。

  column          type     description
  --------------- -------- --------------
  date            date     日付
  code            string   銘柄
  target_weight   float    目標ウェイト
  target_size     int      株数

------------------------------------------------------------------------

# 14. 注文

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

# 15. 約定

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

# 16. ポジション

## positions

  column          type     description
  --------------- -------- --------------
  date            date     日付
  code            string   銘柄
  position_size   int      保有株数
  avg_price       float    平均取得価格
  market_value    float    評価額

------------------------------------------------------------------------

# 17. パフォーマンス

## portfolio_performance

  column         type     description
  -------------- -------- --------------
  date           date     日付
  equity         float    総資産
  cash           float    現金
  drawdown       float    ドローダウン
  daily_return   float    日次リターン
  env            varchar  実行環境（"live" / "paper_trading"）デフォルト: "live"

------------------------------------------------------------------------

# 18. データフロー

## 初回 Bootstrap フロー

    J-Quants Bulk API
      /equities/bars/daily  → raw_prices → prices_daily
      /equities/master      →              stocks
      /fins/summary         → raw_financials → fundamentals
      /markets/calendar     →              market_calendar
      /fins/dividend        →              dividends（新規）
      /indices/bars/daily/topix →          topix_daily（新規）
    ↓ 処理状態記録
    bootstrap_load_history

## 日次差分更新フロー（通常運用）

    J-Quants 差分 API（15:30）
      /equities/bars/daily  → raw_prices → prices_daily  ※date 指定で1日ずつ取得
      /fins/summary         → raw_financials → fundamentals  ※同上
      /listed/info          →              stocks
      /market/trading_calendar →           market_calendar
    ※ /fins/dividend は Standard プランでは HTTP 403（Premium 以上が必要）
    ↓
    TDnet 適時開示（15:35）→ raw_disclosures（source='tdnet'）
    EDINET API（15:40）    → raw_disclosures（source='edinet'）
    raw_news（RSS取得、補助）
    ↓
    features（16:00）
    ↓
    disclosure_events（17:00）← raw_disclosures を分類
    ↓
    ai_scores / market_regime（18:00、ENABLE_AI_SENTIMENT=true 時のみ）
    ↓
    signals（20:00）← disclosure_events の buy_caution も参照
    ↓
    portfolio_targets
    ↓
    orders → trades → positions → portfolio_performance

------------------------------------------------------------------------

# 19. まとめ

本データスキーマは以下の領域をカバーする。

-   市場データ
-   AIデータ
-   戦略データ
-   執行データ
-   ポートフォリオデータ

この構造により
**バックテスト・研究・実運用を同一データ基盤で管理**できる。
