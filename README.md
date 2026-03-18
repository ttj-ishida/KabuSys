# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株のデータ取得・ETL・品質チェック・ニュース収集・監査ログを備えた自動売買プラットフォームのコアライブラリです。本リポジトリはデータレイヤ（Raw / Processed / Feature / Execution）を DuckDB で構成し、J-Quants API や RSS フィードからのデータ取得、ETL パイプライン、監査ログの初期化・管理を行うためのモジュール群を提供します。

主な目的：
- J-Quants からの株価・財務・カレンダー取得（Rate limiting / リトライ / トークン自動リフレッシュ対応）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 防止・サイズ制限・トラッキング除去）
- DuckDB スキーマ定義と安全な初期化
- ETL（差分取得・バックフィル・品質チェック）の一括実行
- 監査ログ（signal → order_request → execution のトレース）用スキーマ

## 機能一覧

- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・財務（四半期）・市場カレンダーの取得
  - API レート制御（120 req/min）、指数バックオフリトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・XML パース（defusedxml）
  - URL 正規化／トラッキングパラメータ削除、記事ID は SHA-256 の先頭 32 文字
  - SSRF 対策、レスポンスサイズ上限、gzip 解凍の安全処理
  - DuckDB への冪等保存（INSERT ... RETURNING）と銘柄紐付け

- データスキーマ管理（kabusys.data.schema）
  - Raw/Processed/Feature/Execution 層のテーブル定義とインデックス
  - init_schema(db_path) による初期化（冪等）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日に基づく自動算出）とバックフィル
  - 市場カレンダー先読み
  - 品質チェック（kabusys.data.quality）との統合

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日の取得・夜間バッチ更新ジョブ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル、初期化ユーティリティ

- 品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合検出
  - QualityIssue による詳細レポート

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得のラッパー settings

## セットアップ手順

1. リポジトリをクローンし、開発環境を作成します（一般的な Python プロジェクト手順）：

   ```bash
   git clone <repository-url>
   cd <repository>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e ".[dev]"   # もしセットアップ用の extras があれば
   ```

   ※ requirements / pyproject.toml がある場合はそちらに従ってください。主な外部依存は duckdb, defusedxml などです。

2. 環境変数を設定します。プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。

   必須環境変数（少なくとも以下を設定してください）：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   省略可 / デフォルトあり：
   - KABUSYS_ENV           : development | paper_trading | live  (デフォルト: development)
   - LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト: INFO)
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視 DB 用の SQLite パス（デフォルト: data/monitoring.db）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマを初期化します（最初に一度だけ実行）：

   Python REPL やスクリプトで：

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

   監査ログ専用 DB を別ファイルで管理する場合：

   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   conn_audit.close()
   ```

## 使い方（代表的な例）

- 日次 ETL を実行する（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）：

  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  # DB 初期化済みであることを想定
  conn = schema.get_connection("data/kabusys.duckdb")

  # ETL 実行（今日を対象）
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- RSS ニュース収集ジョブを実行する：

  ```python
  import duckdb
  from kabusys.data import news_collector

  conn = duckdb.connect("data/kabusys.duckdb")
  # 既定の RSS ソースから収集し既知銘柄セットで紐付け（例）
  known_codes = {"7203", "6758", "9984"}
  stats = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(stats)
  conn.close()
  ```

- J-Quants の日足を個別取得して保存する：

  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  conn.close()
  ```

- 環境設定取得（アプリケーションから）：

  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

## 主要 API（要点）

- kabusys.config.settings — 環境変数からの設定取得（必須キーは _require() で検証）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar — J-Quants 取得
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar — DuckDB への保存（冪等）
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — RSS 収集と保存
- kabusys.data.pipeline.run_daily_etl — 日次 ETL（カレンダー・株価・財務・品質チェック）
- kabusys.data.calendar_management.* — 営業日判定・next/prev_trading_day・calendar_update_job
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化
- kabusys.data.quality.run_all_checks — 品質チェック一括実行

## ディレクトリ構成

以下は src 内の主要ファイル／モジュール一覧と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数と設定の管理（.env 自動読み込み、settings オブジェクト）

- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
  - news_collector.py — RSS フィードからニュースを取得、前処理、DuckDB 保存、銘柄抽出
  - schema.py — DuckDB の DDL（Raw/Processed/Feature/Execution 層）と初期化ユーティリティ
  - pipeline.py — ETL パイプライン（差分取得・バックフィル・品質チェック統合）
  - calendar_management.py — JPX カレンダー更新、営業日判定ユーティリティ
  - audit.py — 監査ログ（signal/order_request/execution）スキーマと初期化
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）

- src/kabusys/strategy/ — 戦略関連（汎用エントリ、実装はプロジェクト固有で追加）
- src/kabusys/execution/ — 発注・ブローカー連携ロジック（拡張対象）
- src/kabusys/monitoring/ — 監視・メトリクス関連（拡張対象）

（実装済みの詳細は各ファイルの docstring を参照してください）

## 運用上の注意事項 / 設計上のポイント

- J-Quants API のレート制限（120 req/min）を厳守するため内部でスロットリングと指数バックオフを実装しています。大量取得時は ETL のスケジューリングに注意してください。
- API 認証はリフレッシュトークン → ID トークンのフローを持ち、401 発生時は自動リフレッシュを試みます。ただしリフレッシュトークン自体は安全に保持してください。
- DuckDB への保存は基本的に冪等（ON CONFLICT）を利用していますが、外部から手動でデータを投入する場合は重複等に注意してください。品質チェックモジュールで監査できます。
- news_collector は SSRF 対策、レスポンスサイズ制限、XML の脆弱性対策（defusedxml）などを行っていますが、外部フィードの変化や巨大ファイルには注意してください。
- audit スキーマは監査・トレーサビリティ目的で設計されています。監査情報は削除しない前提です（FK は ON DELETE RESTRICT）。

## トラブルシュート／デバッグ

- .env の自動ロードが期待通りに動かない場合：
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していると自動ロードは行われません。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行います。パッケージ配布後や別の CWD から動かす場合は明示的に環境変数を設定してください。

- DuckDB に接続できない・テーブルが存在しない：
  - schema.init_schema() を実行して初期化してください。
  - デフォルトパスは data/kabusys.duckdb（親ディレクトリは自動作成されます）。

- J-Quants API エラー（HTTP 5xx / 429 / ネットワークエラー）：
  - 内部で最大 3 回のリトライと指数バックオフを行います。ログに警告が出ますので retry 後も失敗する場合はネットワークやトークンの有効性を確認してください。

## 今後の拡張案（参考）

- strategy / execution モジュールの具体実装（バックテスト API、リアルタイム発注アダプター）
- Slack 通知やモニタリングの統合（kabusys.monitoring）
- ETL の並列化（リソースと API レート制限を考慮）
- テストと CI（単体テスト、インテグレーションテスト用のモック）

---

詳細は各モジュール（src/kabusys/data/*.py, src/kabusys/config.py 等）の docstring を参照してください。実運用前に必ずローカル環境で ETL を試験実行し、品質チェック・ログを確認することを推奨します。