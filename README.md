# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API からの市場データ取得、RSS ニュース収集、データ品質チェック、特徴量作成、ETL パイプライン、監査ログなどの機能を提供します。

バージョン: 0.1.0

## 概要

KabuSys は次の要件を満たすことを目標に設計されています。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたスキーマ定義・冪等保存（ON CONFLICT）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策・gzip / xml 安全対策）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ETL 日次パイプライン（差分取得・バックフィル、品質チェック）
- 研究用のファクター計算・特徴量分析（モメンタム、ボラティリティ、バリュー、IC 計算 等）
- 監査ログ用スキーマ（シグナル → 発注 → 約定 をトレース）

設計方針として、本番発注 API への直接アクセスは避け、データ処理と戦略評価は DuckDB / ローカル処理で完結するようになっています。

## 主な機能一覧

- data
  - jquants_client: J-Quants API からのデータ取得／保存（株価 / 財務 / カレンダー）
  - news_collector: RSS 取得、前処理、DuckDB への冪等保存、銘柄抽出
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 差分 ETL / 日次 ETL 実行（品質チェック統合）
  - quality: 欠損・重複・スパイク・日付不整合チェック
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）初期化
  - stats / features: Z スコア正規化などの統計ユーティリティ
- research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・ファクター統計サマリー
- strategy / execution / monitoring: 将来的な戦略・発注・監視モジュールのプレースホルダ

## 動作要件

- Python >= 3.10（型アノテーションで `X | Y` 構文を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセスが必要（J-Quants API、RSS フィード）

（プロジェクトで使用する追加パッケージは環境に応じて requirements.txt を用意してください）

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate

3. 必要なライブラリをインストール

   pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそちらを使用）

4. 環境変数を設定（.env ファイル推奨）
   プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注周りで使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意（デフォルトあり）:
   - KABUS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   例 `.env`（簡易）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. DuckDB スキーマの初期化

   Python REPL またはスクリプトから:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # path は settings.duckdb_path を使ってもよい

   これにより必要なテーブル・インデックスが作成されます（冪等）。

## 使い方（代表的な API）

以下は簡単な利用例です。実行する前に環境変数が正しく設定され、DuckDB スキーマが初期化されていることを確認してください。

- 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得と品質チェック）

  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブを実行する

  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # スキーマは既に初期化済みとする
  # known_codes は銘柄抽出に使う正当な銘柄コード集合（例: set(["7203", "6758", ...])）
  res = news_collector.run_news_collection(conn, known_codes=None)
  print(res)

- 研究用ファクター計算（例: モメンタム）

  from datetime import date
  from kabusys.data import schema
  from kabusys.research import calc_momentum
  conn = schema.get_connection("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024, 1, 5))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

- J-Quants から日足を直接取得して保存（テスト）

  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect(":memory:")
  # schema.init_schema(conn) のようにスキーマを準備してから利用してください
  data = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, data)

## 環境変数の自動読み込みについて

- プロジェクトルート配下の `.env` と `.env.local` を自動的に読み込みます（優先順位: OS 環境変数 > .env.local > .env）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env` のパースはシェル形式に似た柔軟な仕様に対応しています（export プレフィックス、クォート、インラインコメントの扱いなど）。

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（src/kabusys 以下）と役割の概要です。

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数/設定管理（Settings クラス）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + DuckDB 保存ユーティリティ
  - news_collector.py — RSS 取得・前処理・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - quality.py — データ品質チェック
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - audit.py — 監査ログスキーマ初期化
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - features.py — features API（zscore の再エクスポート）
  - etl.py — ETLResult の公開エントリ
- src/kabusys/research/
  - __init__.py — 研究用ユーティリティのエクスポート
  - feature_exploration.py — 将来リターン / IC / summary
  - factor_research.py — モメンタム / ボラティリティ / バリュー等の計算
- src/kabusys/strategy/ (プレースホルダ)
- src/kabusys/execution/ (プレースホルダ)
- src/kabusys/monitoring/ (プレースホルダ)

## 開発メモ / 実装上の注意点

- DuckDB に保存する際は多くの箇所で ON CONFLICT DO UPDATE / DO NOTHING を使用して冪等性を担保しています。
- J-Quants API のレート制御（120 req/min）は内部 RateLimiter により管理されます。HTTP 429 / 408 / 5xx に対してはリトライ（指数バックオフ）を行います。401 はトークン自動リフレッシュを試みます。
- news_collector では SSRF 対策（リダイレクト時のホスト検査）、XML の安全パーサ（defusedxml）、受信サイズ制限などの安全対策を導入しています。
- ファイル日付やタイムスタンプは基本的に UTC を想定して扱う設計になっています（監査ログ等）。
- 型アノテーションは Python 3.10 以降の構文を使用しています。

## 例: よくあるワークフロー

1. 環境変数を設定（.env）
2. DuckDB スキーマ初期化: schema.init_schema(settings.duckdb_path)
3. 夜間 Cron で run_daily_etl を実行してデータを蓄積
4. 研究環境で research.calc_* を用いて特徴量や IC を評価
5. 戦略実装により signals を生成、監査ログに記録、発注キューを作る

---

ご不明点や README に追記したい内容（例: 詳細な API リファレンスや運用手順）があれば教えてください。README を特定の運用フロー（例: Docker / CI / systemd ユニット）に合わせて拡張できます。