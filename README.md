KabuSys — 日本株向けデータ基盤・自動売買ライブラリ
=================================

概要
----
KabuSys は日本株を対象とした自動売買システム／データ基盤のコアライブラリです。  
主に以下を提供します。

- J-Quants API 経由でのデータ収集（株価日足、財務、カレンダー）
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL（差分取得・保存・品質チェック）パイプライン
- RSS ベースのニュース収集と銘柄紐付け
- 研究用ファクター計算（Momentum / Volatility / Value 等）と統計ユーティリティ
- 監査ログ（signal → order → execution のトレース）スキーマ
- 設定管理（.env 自動ロード、必須環境変数検査）

設計上のポイント
- DuckDB を永続層に採用し、SQL（ウィンドウ関数等）で効率的に計算。
- ETLは差分更新・冪等保存（ON CONFLICT）・品質チェックを組み合わせた堅牢設計。
- J-Quants クライアントはレートリミット制御、リトライ、トークン自動更新を内蔵。
- NewsCollector は SSRF / XML Bomb / サイズ上限等の安全対策を実装。

機能一覧
--------
主要な機能（モジュール別）

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数検査（settings オブジェクト）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット・リトライ・トークン管理

- kabusys.data.schema
  - DuckDB のスキーマ定義（raw_prices, prices_daily, features, signal_queue, audit 等）
  - init_schema(db_path) で初期化

- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl: 日次 ETL（差分取得 + 品質チェック）の統合エントリポイント

- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection
  - 記事ID生成、前処理、銘柄コード抽出、冪等保存、SSRF対策等

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（ETL 後の品質検査）

- kabusys.data.stats / features
  - zscore_normalize（クロスセクション Z スコア正規化）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - DuckDB の prices_daily / raw_financials を使ったファクター計算

- kabusys.data.audit
  - 監査ログ（signal_events, order_requests, executions）スキーマと初期化ユーティリティ

セットアップ手順
----------------
前提
- Python 3.9+（typing の一部機能を使用）
- ネットワークアクセス（J-Quants API、RSS 等）
- J-Quants のリフレッシュトークンを入手済み

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（代表）
   - duckdb
   - defusedxml
   例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください）

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数（settings で参照・必須チェックされるもの）:

     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID

   - 任意・デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) 既定: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) 既定: INFO
     - KABU_API_BASE_URL 既定: http://localhost:18080/kabusapi
     - DUCKDB_PATH 既定: data/kabusys.duckdb
     - SQLITE_PATH 既定: data/monitoring.db

   サンプル .env（例）
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

4. データベース初期化
   Python REPL やスクリプトで以下を実行して DuckDB スキーマを作成します。

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

使い方（クイックスタート）
------------------------

1) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）

from kabusys.data import schema, pipeline
conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
# result は ETLResult 型。to_dict() で詳細取得可能。

2) J-Quants から単体データ取得→保存（テスト用途など）

from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=..., date_to=...)
conn = schema.get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)

3) ニュース収集ジョブ

from kabusys.data import news_collector
conn = schema.get_connection("data/kabusys.duckdb")
# sources は {name: url} の dict、省略時はデフォルトの Yahoo Finance を使用
results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})

4) 研究 / ファクター計算例

from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024, 1, 10))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m","mom_3m"])

5) 監査DB 初期化（監査専用 DB が必要な場合）

from kabusys.data import audit
conn = audit.init_audit_db("data/audit.duckdb")

設定周りの注意
--------------
- 環境変数は .env / .env.local から自動読み込みされます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings.jquants_refresh_token 等は未設定だと ValueError を送出します。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければなりません。

安全性・運用上の注意
--------------------
- J-Quants クライアントは 120 req/min の制限を想定しており、内部でスロットリングしています。大量取得時は注意してください。
- ETL 保存は冪等（ON CONFLICT）を意識した実装になっており、再実行で重複挿入されません。
- NewsCollector は SSRF・XML Bomb・gzip-bomb・大容量レスポンス等の対策を実装していますが、外部フィードの取り扱いは運用での監視が必要です。
- 本ライブラリは「発注（本番）」ロジックを含む領域があるため、本番口座（live）モードでの利用は十分な検証と安全対策（リスク制御、モニタリング）を行ってください。

ディレクトリ構成
----------------
（主要ファイル／モジュールの一覧）

src/kabusys/
- __init__.py
- config.py                     — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント（取得／保存）
  - news_collector.py          — RSS ニュース収集・保存
  - schema.py                  — DuckDB スキーマ定義・初期化
  - pipeline.py                — ETL パイプライン（差分更新 / run_daily_etl）
  - features.py                — 特徴量ユーティリティ（再エクスポート）
  - stats.py                   — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py     — カレンダー更新・営業日判定
  - audit.py                   — 監査ログテーブル初期化
  - etl.py                     — ETLResult の再エクスポート
  - quality.py                 — 品質チェック
- research/
  - __init__.py
  - feature_exploration.py     — 将来リターン計算・IC・統計サマリー
  - factor_research.py         — Momentum / Volatility / Value 計算
- strategy/                     — 戦略関連（未実装のプレースホルダ）
- execution/                    — 発注周り（未実装のプレースホルダ）
- monitoring/                   — モニタリング（未実装のプレースホルダ）
- __init__.py

開発・拡張
-----------
- 新しい ETL ジョブや品質チェックを追加する場合、既存の差分ロジック・backfill の考え方に従って実装してください。
- DuckDB のスキーマを変更する場合は schema._ALL_DDL に追加し、init_schema を通じて適用してください（互換性に注意）。
- research モジュールは標準ライブラリのみで計算できるよう設計されています。外部ライブラリ導入時は依存管理を明確に。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報やコントリビューションルールはプロジェクトルートの該当ファイル（LICENSE, CONTRIBUTING）に従ってください。

連絡
----
不具合報告や使い方の質問は issue を立ててください。README の改善提案も歓迎します。

以上が KabuSys の概要と導入・利用ガイドです。追加したいサンプルや補足（例: docker / systemd バッチ設定、より具体的な .env.example）などがあれば教えてください。