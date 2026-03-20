# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームのライブラリ群です。  
データ収集（J-Quants）、DuckDBベースのデータレイク、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、ETLパイプライン、実行/監査用スキーマなどを含みます。

主な設計方針:
- ルックアヘッドバイアス回避（target_date 時点のデータのみ利用）
- 冪等性（DB への保存は ON CONFLICT / DO UPDATE 等で重複を防止）
- 外部 API 呼び出しは data 層に集中、strategy 層や execution 層は API へ依存しない
- DuckDB を用いた軽量なオンディスク DB

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - ニュース RSS 収集（URL 正規化・SSRF 対策・トラッキングパラメータ除去）
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar / raw_news 等）

- スキーマ / DB 管理
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - DB コネクションヘルパ

- ETL パイプライン
  - 差分取得（最終取得日からの差分）
  - バックフィル（APIの後出し修正を吸収）
  - 品質チェック（別モジュール quality を想定）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value等のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Spearman）やファクター統計サマリー

- 特徴量生成・シグナル生成
  - ファクターのクロスセクション正規化（Zスコア）
  - features テーブルへのアップサート（日付単位で置換）
  - ai_scores 統合、重み付けによる final_score 計算、BUY/SELL シグナル生成
  - Bear レジーム検知による BUY 抑制、エグジット（ストップロス等）判定

- マーケットカレンダー管理
  - JPX カレンダー更新ジョブ、営業日判定（next/prev/get_trading_days 等）

- ニュース処理
  - RSS フィード取得・テキスト前処理・記事ID生成（SHA256）・銘柄抽出・DB保存

- 監査・実行関連（スキーマ）
  - signal_events / order_requests / executions 等の監査用テーブル定義

---

## セットアップ手順

前提: Python 3.10+ を想定（型注釈等からの推測）。パッケージは pyproject.toml が存在する想定です。

1. リポジトリをクローンし、開発用インストール
   - pip を使って editable インストール（pyproject.toml があるなら）
     ```
     git clone <repo-url>
     cd <repo>
     python -m pip install -e .
     ```
   - 必要な追加依存（最低限の例）
     ```
     python -m pip install duckdb defusedxml
     ```

2. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（パッケージ読み込み時に自動ロード。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - オプション:
     - KABUSYS_ENV — one of "development", "paper_trading", "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   例 `.env`（最低限）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

3. データベース初期化
   - DuckDB スキーマを作成します（親フォルダを自動作成します）。
   - 例:
     ```py
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（主要 API の例）

以下はライブラリを Python スクリプトや REPL から利用する際の基本例です。

1. DuckDB を初期化して ETL を実行（日次 ETL）
   ```py
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を渡さなければ本日が対象
   print(result.to_dict())
   ```

2. 特徴量（features）を構築
   ```py
   from kabusys.data.schema import get_connection
   from kabusys.strategy import build_features
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 1, 31))
   print(f"features upserted: {n}")
   ```

3. シグナル生成
   ```py
   from kabusys.data.schema import get_connection
   from kabusys.strategy import generate_signals
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024, 1, 31))
   print(f"signals written: {total}")
   ```

4. ニュース収集ジョブ
   ```py
   from kabusys.data.schema import get_connection
   from kabusys.data.news_collector import run_news_collection

   conn = get_connection("data/kabusys.duckdb")
   # known_codes に有効な銘柄コードセットを渡すと自動で記事と銘柄を紐付けます
   res = run_news_collection(conn, known_codes={"7203","6758"})
   print(res)  # {source_name: inserted_count}
   ```

5. J-Quants データ取得（低レベル）
   ```py
   from kabusys.data import jquants_client as jq
   from datetime import date

   # トークンは settings.jquants_refresh_token を使って自動取得されます
   quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   print(len(quotes))
   ```

6. マーケットカレンダーの利用例
   ```py
   from kabusys.data.calendar_management import is_trading_day, next_trading_day
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   d = date(2024,1,1)
   print(is_trading_day(conn, d))
   print(next_trading_day(conn, d))
   ```

---

## 設定と注意点

- 環境変数は config.Settings クラスで取得されます。未設定の必須変数にアクセスすると ValueError が発生します。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストなどで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API クライアントは内部でレート制限（120 req/min）を守る実装があり、リトライ・トークン自動更新ロジックを持ちます。
- DuckDB の初期化は init_schema() を使ってください。既存テーブルはスキップされるため安全に実行できます。
- ニュースの RSS 取得には SSRF 防止や gzip BOM 等の対策済みですが、外部ソースの信頼性に依存するため運用時は監視を行ってください。

---

## ディレクトリ構成

（主要ファイルとモジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント
    - news_collector.py          — RSS ニュース収集
    - schema.py                  — DuckDB スキーマ定義と初期化
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — マーケットカレンダー管理
    - features.py                — data 層の features 再エクスポート
    - audit.py                   — 監査ログスキーマ（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/volatility/value）
    - feature_exploration.py     — リサーチ用の将来リターン/IC/summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py     — feature 作成（build_features）
    - signal_generator.py        — シグナル生成（generate_signals）
  - execution/                    — 実行層（空ファイル / パッケージ用）
  - monitoring/                   — 監視用（将来的に監視処理を配置）

ドキュメント参照ファイル（参照される想定）
- DataPlatform.md
- StrategyModel.md

---

## 開発 / テスト

- 自動環境読み込みをテストから切り離す場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト中に意図した環境変数だけを注入してください。
- モジュール内のネットワーク呼び出し（jquants_client._request や news_collector._urlopen）はテストでモック可能になるよう設計されています。

---

## ライセンス / 貢献

この README はコードベースの説明ドキュメントです。実際のライセンス・貢献ガイドはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

---

不明点や追加で README に入れたい利用例（cron の設定、運用手順、CI ワークフロー等）があれば教えてください。必要に応じて追記します。