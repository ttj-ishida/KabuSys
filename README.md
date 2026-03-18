KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株のデータ収集・ETL、特徴量生成、リサーチ、監査ログ、発注トレースなどを含む自動売買プラットフォームのコアライブラリ群です。DuckDB をデータ層に用い、J-Quants API など外部データソースからの安全な取得・保存・品質チェックを行うことを目的としています。  
設計方針として「冪等性（idempotency）」「Look-ahead バイアス対策」「外部 API への堅牢なリトライ/レート制御」「DB による明示的なスキーマ管理」を重視しています。

主な機能
---------
- 環境設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須パラメータの明示的チェック
- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日を基に差分を自動算出）
  - 市場カレンダー先読み、バックフィル対応
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の一括実行（run_daily_etl）
- ニュース収集
  - RSS フィード取得（gzip 対応）、XML セキュリティ対策（defusedxml）
  - URL 正規化・トラッキングパラメタ除去、SSRF 対策、受信サイズ制限
  - raw_news への冪等保存、記事と銘柄コードの紐付け
- データスキーマ管理
  - DuckDB 用の詳細なスキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - スキーマ初期化ユーティリティ（init_schema 等）
  - 監査ログ用スキーマ（トレーサビリティ）
- リサーチ / 特徴量
  - Momentum / Volatility / Value 等のファクター計算（DuckDB に対する SQL ベース）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- マーケットカレンダー管理
  - 営業日判定、前後営業日検索、夜間バッチ更新ジョブ
- 監視・監査
  - 発注／約定のトレーサビリティテーブル群と初期化関数

セットアップ
----------
必要条件（代表的なもの）
- Python 3.9+
- DuckDB
- defusedxml

推奨インストール例:
- 仮想環境を作成して依存をインストールする:
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
  - pip install duckdb defusedxml

環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API 用パスワード（発注系を使う場合）
  - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- 任意 / デフォルトあり:
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB など（デフォルト data/monitoring.db）

.env 自動読み込みについて
- パッケージ起点（__file__ の親階層）から .git もしくは pyproject.toml を探索してプロジェクトルートを検出し、.env → .env.local の順で自動読み込みします。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡単な .env の例
（実運用では機密情報を適切に管理してください）
- JQUANTS_REFRESH_TOKEN=your_refresh_token_here
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development

使い方（コード例）
-----------------
以下は代表的な使い方の抜粋です。実際は適切なログ設定・例外処理を行ってください。

1) DuckDB スキーマ初期化
- 全テーブルを初期化して接続を取得する:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 監査ログ専用 DB を初期化:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

2) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn)  # target_date を指定可能
- result は ETLResult オブジェクト（処理サマリ・品質問題の一覧等）

3) ニュース収集（RSS）ジョブ
- from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
- results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})

4) J-Quants API を直接使ってデータ取得/保存
- from kabusys.data import jquants_client as jq
- records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
- saved = jq.save_daily_quotes(conn, records)

5) リサーチ / ファクター計算
- from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- momentum = calc_momentum(conn, target_date=date(2024,2,1))
- forward = calc_forward_returns(conn, target_date=date(2024,2,1))
- ic = calc_ic(factor_records=momentum, forward_records=forward, factor_col="mom_1m", return_col="fwd_1d")
- summary = factor_summary(momentum, ["mom_1m","ma200_dev"])

6) マーケットカレンダー操作
- from kabusys.data.calendar_management import calendar_update_job, is_trading_day, next_trading_day
- saved = calendar_update_job(conn)
- is_td = is_trading_day(conn, date(2024,2,1))
- next_td = next_trading_day(conn, date(2024,2,1))

注意点・設計上の特徴
-------------------
- DuckDB を用いたローカル DB により「クエリで高速に集計・ウィンドウ計算」が可能です。初期化関数は冪等（存在するテーブルは作成スキップ）です。
- J-Quants クライアントはレート制限・リトライ・トークン自動更新等の堅牢性対策を実装しています。API 呼び出しは最小限の外部依存（標準ライブラリの urllib）で実装されています。
- ニュース収集は SSRF・XML Bomb 等の攻撃を考慮した実装（defusedxml、受信サイズ上限、ホストのプライベート判定等）です。
- ETL は Fail-Fast ではなく「問題を収集して呼び出し元に返す」アプローチを採っています（品質チェックで重大度に応じた判定が可能）。
- 環境の自動読み込みは CI/テストで不要な場合に無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョン、公開サブパッケージ）
- config.py — 環境変数 / 設定読み込み・バリデーション（settings）
- data/  — データ層（取得・ETL・スキーマ・品質チェック等）
  - jquants_client.py — J-Quants API クライアント（取得/保存）
  - news_collector.py — RSS ニュース収集・解析・保存
  - schema.py — DuckDB の DDL 定義と初期化関数
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - features.py / etl.py / audit.py — 補助モジュール（公開 API 等）
- research/
  - __init__.py — 研究用 API エクスポート
  - feature_exploration.py — 将来リターン・IC・統計サマリー実装
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
- strategy/ — 戦略関連（現在はパッケージプレースホルダ）
- execution/ — 発注・執行関連（パッケージプレースホルダ）
- monitoring/ — 監視関連（パッケージプレースホルダ）

今後の拡張ポイント（案）
------------------------
- strategy / execution 層の実装（ポジション管理・資金管理ルール）
- Slack 通知や監視ダッシュボードの統合（settings から Slack 設定を利用）
- CI 向けのテストヘルパー（duckdb の :memory: を用いたユニットテスト）
- より多様なデータソース（他 API やファイルインポート）の追加

サポート
-------
- コード内の docstring（日本語）に各関数の使い方・設計意図が記載されています。実装の挙動や引数・戻り値はそれらを参照してください。

ライセンス
---------
- 本リポジトリにライセンスファイルが含まれている場合はそちらに従ってください（README には明示していません）。

以上が KabuSys の簡潔な README です。必要であれば「セットアップ手順（依存パッケージの exact requirements.txt）」や「運用手順（cron ジョブ例、Dockerfile、systemd サービス定義）」のテンプレートも作成します。どの情報がさらに必要か教えてください。