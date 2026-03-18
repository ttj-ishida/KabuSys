# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータレイヤに、J-Quants API からのデータ取得、ETL、品質チェック、ニュース収集、ファクター計算（リサーチ）や発注監査ログ用スキーマなど、トレードシステムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務データ / 市場カレンダー取得）
  - 取得データの DuckDB への冪等保存（ON CONFLICT を利用）
  - API のレートリミット・リトライ・トークン自動リフレッシュ対応

- ETL パイプライン
  - 差分更新（最終取得日からの差分 + バックフィル）
  - 日次 ETL エントリポイント（カレンダー → 株価 → 財務 → 品質チェック）

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付不整合チェック
  - QualityIssue を返す設計（Fail-Fast ではなく問題を集約）

- ニュース収集
  - RSS フィード取得・前処理（URL 除去、正規化）・DuckDB への冪等保存
  - SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）

- リサーチ / 特徴量計算
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算（forward returns）と IC（Spearman rank）計算
  - Z スコア正規化ユーティリティ

- スキーマ管理 / 監査ログ
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ（signal → order_request → execution のトレーサビリティ）

- 設定管理
  - .env / .env.local / OS 環境変数からの読み込み（プロジェクトルート検出による自動ロード）
  - 必須設定は settings オブジェクト経由で取得

---

## セットアップ手順

前提: Python 3.9+（typing の一部記法を使用）、pip が利用可能

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows では .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限必要な主要依存
     - duckdb
     - defusedxml
   - 例:
     pip install duckdb defusedxml

   （本リポジトリをパッケージ化している場合は、pip install -e . でインストール可能な想定です）

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動的に読み込まれます（既存 OS 環境変数が優先、.env.local が .env を上書き）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）

   - オプション
     - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL             : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

4. DuckDB スキーマの初期化
   - 例（Python REPL / スクリプト）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # ":memory:" を渡すとインメモリ DB

---

## 使い方（代表的な例）

以下に代表的な利用例を示します。

- 設定オブジェクトの参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（カレンダー・株価・財務の差分取得と品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別 ETL ジョブ
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  # 同様に run_financials_etl / run_calendar_etl

- ニュース収集（RSS）ジョブ
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 抽出に使用する有効銘柄コードセット（省略可）
  res = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  # res は各ソースの新規保存件数を返す dict

- J-Quants API クライアント利用（生データ取得）
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を利用して id token を取得
  quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- リサーチ / ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  # conn は DuckDB 接続
  momentum = calc_momentum(conn, target_date=date(2024,1,31))
  volatility = calc_volatility(conn, target_date=date(2024,1,31))
  value = calc_value(conn, target_date=date(2024,1,31))
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31))
  ic = calc_ic(factor_records=momentum, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")

- データ品質チェック
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2024,1,31))
  for i in issues:
      print(i)

---

## 設定（.env の例）

.env.example（抜粋）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

※シークレットはリポジトリにコミットしないでください。

---

## 主要モジュール一覧（簡易説明）

- kabusys.config
  - settings: 環境変数経由の設定取得。自動で .env/.env.local をロード（プロジェクトルート判定）。
- kabusys.data.jquants_client
  - J-Quants API クライアント：fetch_* / save_* 関数、get_id_token
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema(), get_connection()
- kabusys.data.pipeline
  - ETL 実行: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - RSS フィード取得・前処理・保存・銘柄抽出
- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.data.stats / kabusys.data.features
  - 統計ユーティリティ（zscore_normalize）
- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary など）
- kabusys.data.audit
  - 発注〜約定の監査スキーマ（signal_events, order_requests, executions）

---

## ディレクトリ構成

リポジトリの主要なファイル構成（抜粋）:

src/
  kabusys/
    __init__.py
    config.py
    execution/                # 発注実行関連（未実装フック等）
    strategy/                 # 戦略関連（未実装フック等）
    monitoring/               # 監視系モジュール（プレースホルダ）
    data/
      __init__.py
      jquants_client.py       # J-Quants クライアント + 保存ユーティリティ
      news_collector.py       # RSS ニュース収集
      schema.py               # DuckDB スキーマ定義/初期化
      pipeline.py             # ETL パイプライン
      quality.py              # データ品質チェック
      stats.py                # 統計ユーティリティ（zscore_normalize）
      features.py             # features 公開インターフェース
      calendar_management.py  # マーケットカレンダー管理 / バッチジョブ
      etl.py                  # ETL インターフェース再エクスポート
      audit.py                # 監査ログテーブル初期化
    research/
      __init__.py
      feature_exploration.py  # 将来リターン / IC / サマリー等
      factor_research.py      # momentum/volatility/value の実装

---

## 注意事項 / 設計ポリシー（要点）

- 本ライブラリは本番口座への直接発注を行うモジュールと、データ収集／研究モジュールを分離する設計を採っています。research や data モジュールは発注 API にアクセスしない点に留意してください。
- DuckDB への書き込みは冪等性（ON CONFLICT）を重視しています。
- J-Quants API のレート制限（120 req/min）やエラーリトライ、401 時のトークンリフレッシュを組み込み済みです。
- ニュース収集は SSRF 対策、XML の安全パース、受信サイズ制限等の安全対策を実装しています。
- 環境変数は必須項目があり、settings オブジェクトが未設定の場合は ValueError を投げます（実行前に .env を準備してください）。

---

必要であれば、運用手順（cron/CIでの ETL 実行、監視アラートの送り方、Slack 通知の実装例）、さらに詳細な開発者向けガイド（テスト方法、モック化ポイント、パフォーマンスチューニング）も追加できます。どの情報が必要か教えてください。