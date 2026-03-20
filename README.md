# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査/スキーマ管理などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を想定したコンポーネント群です。

- J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に保存する（差分取得・冪等保存）。
- 収集データの品質チェック・カレンダー管理。
- 研究（research）で算出した生ファクターを正規化・合成して features テーブルを作成（feature_engineering）。
- features と AI スコアを統合して売買シグナルを生成（signal_generator）。
- RSS からニュースを収集し記事と銘柄の紐付けを行う（news_collector）。
- DuckDB スキーマ定義・初期化、監査ログテーブルなどの管理。

設計上のポイント:
- DuckDB をコア DB として利用（オンディスク/インメモリどちらも可）。
- 冪等性（ON CONFLICT / upsert）とトランザクションを重視。
- ルックアヘッドバイアス回避のため「target_date 時点のデータのみ」を使用する方針。
- 外部 API 呼び出しは data 層に集約され、strategy 層や execution 層へ直接依存しない。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン自動リフレッシュ・レート制御）
  - pipeline: 日次 ETL（calendar / prices / financials）と差分取得ロジック
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・次/前営業日取得等
  - stats: zscore_normalize 等の統計ユーティリティ
- research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリー等の研究用ユーティリティ
- strategy
  - feature_engineering.build_features(conn, target_date): features テーブル構築
  - signal_generator.generate_signals(conn, target_date, ...): signals テーブル生成
- config
  - 環境変数読み込み・設定管理（.env 自動読み込み、必要変数取得）

---

## セットアップ手順

1. Python 環境作成（推奨: 仮想環境）
   - 例（venv）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 必要パッケージをインストール
   - 主要依存: duckdb, defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - プロジェクトを開発モードでインストール可能（セットアップファイルがある場合）:
     ```
     pip install -e .
     ```

3. 環境変数の準備
   - .env（または環境変数）に以下を設定してください（最低限必要なものを列挙）:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
     - KABUSYS_ENV: 環境 (development | paper_trading | live)（省略: development）
     - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   - 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

4. DuckDB スキーマ初期化
   - Python コンソールやスクリプトで:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - ":memory:" を指定すればインメモリ DB での初期化も可能:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（主要ワークフロー）

以下は典型的なシンプル実行例です。実運用ではログ設定やエラー処理、スケジューラ（cron / Airflow 等）を組み合わせてください。

1. 日次 ETL を実行して DuckDB にデータを保存する
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema(settings.duckdb_path)  # 初回のみ
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

2. 研究で作成した生ファクターを正規化して features を作る
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy import build_features
   from kabusys.config import settings
   from kabusys.data.schema import get_connection

   conn = get_connection(settings.duckdb_path)
   count = build_features(conn, date(2024, 1, 10))
   print(f"features upserted: {count}")
   ```

3. シグナルを生成して signals テーブルへ書き込む
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.config import settings
   from kabusys.data.schema import get_connection

   conn = get_connection(settings.duckdb_path)
   total_signals = generate_signals(conn, date(2024, 1, 10), threshold=0.6)
   print(f"signals written: {total_signals}")
   ```

4. RSS ニュース収集と銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import get_connection

   conn = get_connection(settings.duckdb_path)
   # known_codes は有効な銘柄コードセット（例: prices_daily の全 code を取得してセット化）
   known_codes = {"7203", "6758", ...}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

5. J-Quants の個別 API 呼び出し
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

   quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   financials = fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2024,1,1))
   ```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB のファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（既定: data/monitoring.db）
- KABUSYS_ENV — environment（development / paper_trading / live）: 不正な値は例外
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには "1" を設定

settings（kabusys.config.settings）経由でアクセスできます。

---

## 実装上の注意点 / 運用上の注意

- DuckDB のスキーマは init_schema() で作成します。既にテーブルがある場合はスキップ（冪等）。
- jquants_client はレート制限およびリトライロジックを内蔵しています。大量リクエスト時は注意。
- news_collector は SSRF 防御やレスポンスサイズ上限（10MB）など安全策を実装していますが、外部 RSS の扱いには注意。
- strategy 層は発注（execution）層に直接依存しない設計です。execution 層との接続は別実装が必要です。
- KABUSYS_ENV が "live" の場合は実際の発注・マネジメントには特別な安全措置が必要です（ここに含まれているのはロジックのみ）。

---

## ディレクトリ構成

プロジェクトの主要ファイルと役割（省略形）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py         — RSS ニュース取得・前処理・DB 保存
    - schema.py                 — DuckDB スキーマ定義・初期化 (init_schema)
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - stats.py                  — 統計ユーティリティ（zscore_normalize）
    - features.py               — data.stats の再エクスポート
    - calendar_management.py    — 市場カレンダー管理ユーティリティ
    - audit.py                  — 監査ログ（signal_events, order_requests, executions）
    - audit/ (※一部ファイルの途中切断あり)
  - research/
    - __init__.py
    - factor_research.py        — momentum / value / volatility の計算
    - feature_exploration.py    — 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py    — features テーブル構築（build_features）
    - signal_generator.py       — final_score 計算および signals 生成（generate_signals）
  - execution/ (現状空のパッケージプレースホルダ)
  - monitoring/ (監視 DB 用ロジック等、実装ファイルありうる)

（README に掲載したものはコードベースから抽出した主要モジュールの一覧です）

---

## 開発 / テスト

- テスト用には DuckDB のインメモリモード (":memory:") を使用すると便利です。
- config の自動 .env ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- 外部 API 呼び出しを伴うモジュール（jquants_client, news_collector）については HTTP クライアントや内部関数をモックして単体テストを行ってください。

---

## 参考・補足

- StrategyModel.md / DataPlatform.md といった設計ドキュメントに準拠した実装方針が各モジュールの docstring に記載されています（コード内コメントを参照してください）。
- ログや監査情報は運用上重要です。Slack 通知や監視フローは別途組み合わせてください。

---

この README はコードベースの現状（提供されたソース）に基づく概要ドキュメントです。追加したい運用手順（デプロイ、CI、監視アラート設計等）があれば追記できます。