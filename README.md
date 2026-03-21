# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
Data（J-Quants からの市場データ・ニュース収集）、Research（ファクター計算・特徴量解析）、Strategy（特徴量合成・シグナル生成）、Execution（発注／監視）を想定したモジュール群を提供します。

現在のバージョン: 0.1.0

## 概要（Project Overview）

KabuSys は次の目的を持つ内部ライブラリです。

- J-Quants API から株価・財務・カレンダー等を取得し DuckDB に保存する ETL パイプライン
- 研究環境で計算した生ファクターを正規化・合成して戦略用特徴量を作成する機能
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成するロジック
- RSS ベースのニュース収集と記事→銘柄紐付け
- DuckDB ベースのスキーマ初期化・監査テーブル・実行層テーブル定義

設計上の特徴:

- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性を考慮した DB 保存（ON CONFLICT / INSERT DO UPDATE 等）
- 外部依存は最小化（標準ライブラリ中心＋必要なライブラリのみ）
- 明示的な環境変数設定を利用（.env / 環境変数から読み込み）

## 機能一覧（Features）

主な機能は以下の通りです。

- データ取得 / 保存
  - J-Quants API クライアント（差分取得・ページネーション・トークンリフレッシュ・レート制御）
  - raw_prices / raw_financials / market_calendar 等への冪等保存関数
- ETL パイプライン
  - 日次 ETL（市場カレンダー・株価・財務の差分更新、品質チェックのフック）
  - 個別ジョブ（prices / financials / calendar）
- データスキーマ
  - DuckDB 用のスキーマ初期化（Raw / Processed / Feature / Execution 層）
- 研究・ファクター関連
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング & シグナル生成
  - features テーブル作成（正規化・クリッピング・ユニバースフィルタ）
  - final_score 計算、BUY / SELL シグナル生成（Bear レジーム判定、エグジット判定含む）
- ニュース収集
  - RSS フィード取得（SSRF 対策・サイズ制限・XML セーフパーサ）
  - raw_news 保存、記事ID生成（URL 正規化→SHA-256）
  - 銘柄コード抽出・news_symbols への紐付け
- 監査ログ（audit）スキーマ（signal → order → execution のトレーサビリティ）

## 必要条件（Requirements）

- Python 3.10+
- パッケージ依存（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース 等）
- 環境変数に J-Quants / Slack / kabuステーション の認証情報

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

## セットアップ手順（Setup）

1. Python 環境を作成（推奨: venv / pyenv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にソースを editable インストールする場合:
     ```
     pip install -e .
     ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` と `.env.local` を置くことで自動読み込みされます。
   - 自動読み込みを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
     - KABU_API_PASSWORD : kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN : Slack Bot トークン（通知用）
     - SLACK_CHANNEL_ID : Slack のチャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - DUCKDB_PATH : データベースパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）

4. データベース初期化（DuckDB）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリが自動作成されます
     ```

## 使い方（Usage）

いくつかの主要な利用例を示します。

- 日次 ETL を実行（市場カレンダー・株価・財務を差分更新）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量を構築（features テーブルへ UPSERT）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"features upserted: {n}")
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 31))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄セット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants からの日足取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)
  ```

注意点:

- すべての公開 API は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取ることが多く、接続は init_schema / get_connection で取得します。
- run_daily_etl はエラーを個別にハンドルして可能な限り処理を継続し、ETLResult に問題概要を返します。
- テストや CI で自動的な .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

## 環境変数（主な設定項目）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (既定: data/kabusys.duckdb)
- SQLITE_PATH (既定: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

.env の自動読み込み順序:
- OS 環境変数 > .env.local > .env（ただし OS 変数は保護され上書きされません）
- プロジェクトルートはこのモジュールファイルの親ディレクトリから .git または pyproject.toml を探索して決定します。見つからない場合は自動ロードをスキップします。

## ディレクトリ構成（Directory Structure）

以下は本リポジトリ内の主要なモジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py

各ディレクトリの目的:

- data: データ取得／保存、DB スキーマ、ETL、ニュース収集、カレンダー管理などデータプラットフォーム機能を含む
- research: ファクター計算や解析ユーティリティ（研究用）
- strategy: 戦略側の特徴量合成とシグナル生成
- execution: 発注／実行に関するモジュール（将来的に拡張）

## 推奨ワークフロー（簡略）

1. 環境変数を設定（.env を作成）
2. DuckDB スキーマを初期化: init_schema()
3. 日次 ETL を実行: run_daily_etl()
4. 特徴量を構築: build_features()
5. シグナルを生成: generate_signals()
6. （Execution 層）シグナルを発注フローに渡す（現状は Execution 層の実装を拡張）

## トラブルシューティング

- DuckDB がインストールされていない / インポートエラーが出る場合は pip install duckdb を実行してください。
- .env が読み込まれない場合:
  - プロジェクトルートに .git または pyproject.toml が存在するか確認してください。
  - テスト実行時などに意図せず自動読み込みされたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の 401 が発生する場合は JQUANTS_REFRESH_TOKEN を確認してください。ライブラリは 401 受信時に自動リフレッシュ処理を行います（ただし設定が正しくないと失敗します）。

---

詳細な各モジュールの挙動やスキーマ仕様（DataSchema.md・StrategyModel.md 等の設計ドキュメント参照）に関しては、個別のドキュメント／コード内 docstring を参照してください。README に載せている使い方は最小限の開始手順です。必要であればサンプルスクリプトや CLI ラッパーの例を追加できます。