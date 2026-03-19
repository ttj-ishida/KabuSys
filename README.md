# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル算出、ニュース収集、カレンダー管理、監査ログなどを含むモジュール化された実装を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- DuckDB を中心としたローカルデータベース設計（冪等な INSERT/UPSERT を前提）
- 本番発注層（broker）への直接依存を持たない（execution 層と分離）
- 外部依存は最小限（duckdb, defusedxml 等）

---

## 機能一覧

- データ取得/保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー） — レート制御・リトライ・トークン自動更新対応
  - raw / processed / feature / execution 層を想定した DuckDB スキーマ定義と初期化
- ETL パイプライン
  - 差分更新（バックフィル対応）・カレンダー先読み・品質チェック（別モジュール）を含む日次 ETL
- 研究（research）用ユーティリティ
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 特徴量生成（feature engineering）
  - 生ファクターを正規化（Z スコア）して `features` テーブルへ保存
- シグナル生成
  - 正規化済みファクター + AI スコアを統合し final_score を計算、BUY/SELL を `signals` テーブルへ保存
  - Bear レジーム抑制、ストップロス等のエグジット判定
- ニュース収集
  - RSS 取得、記事正規化、記事ID生成（URL 正規化 + SHA-256）、raw_news と news_symbols への冪等保存
  - SSRF 対策、サイズ制限、XML パースの安全化（defusedxml）
- マーケットカレンダー管理
  - JPX カレンダー差分更新、営業日判定／前後営業日取得、期間内の営業日列挙
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティを確保する監査テーブル群

---

## 前提（Prerequisites）

- Python 3.10 以上（typing の `|` 表記等を使用）
- duckdb
- defusedxml
- （ネットワークで J-Quants や RSS にアクセスするため、適切なネットワーク環境と API トークンが必要）

必要なパッケージ例（最低限）:
- duckdb
- defusedxml

---

## セットアップ手順

1. 仮想環境を作成して有効化（例）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 必要パッケージをインストール
   - 最低限:
     - pip install duckdb defusedxml
   - プロジェクト配布に requirements.txt または pyproject.toml がある場合はそれに従ってください。
   - 開発インストール（パッケージがパッケージ化されている場合）:
     - pip install -e .

3. 環境変数設定
   - ルート（プロジェクトルートに .git または pyproject.toml がある場合）から `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
   - オプション/デフォルト:
     - KABUSYS_ENV — 開発環境フラグ（development / paper_trading / live）。デフォルト: development
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト: INFO
     - KABU_API_BASE_URL — kabu API の base URL。デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — 監視用 SQLite パス。デフォルト: data/monitoring.db

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN="あなたのリフレッシュトークン"
     KABU_API_PASSWORD="kabu_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C01234567"
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
     ```
   - これにより必要なテーブル・インデックスが作成されます（冪等）。

---

## 使い方（簡単な例）

以下はライブラリの主要なユースケースのサンプルコードです。実際はプロジェクトの CLI / ジョブとして組み込んで利用してください。

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（feature engineering）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 1))
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 1))
  print(f"signals generated: {total}")
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "6501"}  # 適宜用意する
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market_calendar saved: {saved}")
  ```

注意点：
- J-Quants API の呼び出しはレート制御され、リトライ・トークン更新の機能を備えています。ネットワーク接続と有効なトークンが必須です。
- ETL / API 呼び出しはネットワークエラーや API 側の問題を個別にハンドリングし、可能な限り処理を継続する設計です。ログを確認してください。

---

## 環境変数の自動読み込みについて

- モジュール kabusys.config はプロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `.env.local` は上書き（override=True）され、OS 環境変数は保護されます。
- 自動読み込みを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数／設定読み込みユーティリティ
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py — RSS 取得／前処理／DB保存
    - schema.py — DuckDB スキーマ定義と init_schema
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー更新／営業日判定ユーティリティ
    - audit.py — 監査ログ用テーブル定義
    - features.py — data 側の特徴量ユーティリティ公開
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティの計算
    - feature_exploration.py — 将来リターン, IC, 統計サマリ
  - strategy/
    - __init__.py — build_features / generate_signals を公開
    - feature_engineering.py — 特徴量の正規化・UPSERT 実装
    - signal_generator.py — final_score 計算と signals への書き込み
  - execution/
    - __init__.py — execution 関連（実装の起点。発注層の実装を想定）
  - monitoring/
    - （モニタリング用モジュールが想定されています）

各モジュールの役割は上の「機能一覧」を参照してください。実際のファイルは src/kabusys 以下に実装されています。

---

## ロギング・デバッグ

- 環境変数 LOG_LEVEL でログレベルを設定できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 各モジュールは標準 logging を使用しています。アプリケーション側で適切にハンドラを設定してログ出力先を制御してください。

---

## 開発上の注意

- DuckDB の SQL やトランザクションはコード内で直接実行され、初期化処理は冪等であることを前提にしています。既存データの上書きなどは仕様を理解した上で行ってください。
- NewsCollector では外部入力（XML, URL）を扱うため、SSRF 対策や XML パースの安全化（defusedxml）を行っています。テストではネットワークモックが有用です。
- シグナル生成周りは StrategyModel.md 等の仕様に依存する設計になっています。パラメータ（重み・閾値）は関数引数で上書き可能です。

---

必要であれば、README に含める CLI 実行例、より詳細な .env.example、または各モジュールの API リファレンス（関数毎の引数/戻り値・例外仕様）を追加で作成します。どの情報を優先して追記しますか？