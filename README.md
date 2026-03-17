# KabuSys

日本株自動売買システムのコアライブラリ（データ収集・ETL・品質管理・監査ログなど）

このリポジトリは、J-Quants や RSS 等からのデータ収集、DuckDB を用いたスキーマ定義と ETL、データ品質チェックや監査ログ機能を提供するライブラリ群です。主に日本株を対象としたデータパイプラインと監査機能を提供します。

## 主な特徴（機能一覧）

- 環境変数 / .env 自動読み込み（`kabusys.config`）
  - プロジェクトルートの `.env` / `.env.local` を自動で読み込み（無効化可能）
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 株価（日足 OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応の RateLimiter
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- RSS ニュース収集（`kabusys.data.news_collector`）
  - RSS から記事を収集し正規化・前処理して raw_news に保存
  - URL 正規化、トラッキングパラメータ除去、SSRF / XML 攻撃対策（defusedxml）
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で冪等性を確保
  - 銘柄コード抽出・news_symbols への紐付け
- DuckDB スキーマ定義・初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - インデックス定義、冪等なテーブル作成
- ETL パイプライン（`kabusys.data.pipeline`）
  - 市場カレンダー・株価・財務データの差分取得（バックフィル対応）
  - 品質チェック（`kabusys.data.quality`）との連携
  - 日次 ETL 統合エントリ（run_daily_etl）
- マーケットカレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定 / prev/next 営業日取得 / 期間の営業日取得
  - 夜間バッチで JPX カレンダーを差分更新するジョブ
- 監査ログ（`kabusys.data.audit`）
  - signal → order_request → execution までのトレーサビリティ用テーブル
  - UUID による冪等キー、UTC タイムスタンプ、インデックス
- データ品質チェック（`kabusys.data.quality`）
  - 欠損データ、スパイク（前日比）、重複、日付整合性チェック
  - QualityIssue オブジェクトで問題を集約（error / warning）

## 必要な環境変数

以下の環境変数はアプリケーション設定で参照されます（必須は README 内で明示）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）、デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値が設定されていれば無効化）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順

1. Python 仮想環境の作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   - 本コードベースで使われている主な依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - その他、運用で必要なパッケージ（Slack クライアント等）は用途に応じて追加してください。

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

4. DuckDB スキーマの初期化
   - 例（Python REPL またはスクリプトで）:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # settings.duckdb_path はデフォルト data/kabusys.duckdb
     ```

5. 監査ログスキーマ（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings

   # 監査専用 DB を別ファイルに分ける場合:
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

## 使い方（代表的な例）

- 日次 ETL を実行する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブを実行する
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集ジョブを実行する
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  # known_codes に有効な銘柄コードセットを渡すと自動で紐付け
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants から生データを直接取得して保存する（テストやユーティリティ）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  token = get_id_token()  # settings から自動参照
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)
  ```

- 品質チェックを手動実行する
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点:
- J-Quants API のレート制限（120 req/min）に従うよう内部で制御していますが、大量リクエストを行う際には実行頻度に注意してください。
- get_id_token は内部で settings.jquants_refresh_token を参照します。環境変数が未設定だと例外になります。

## ディレクトリ構成

リポジトリ（src/kabusys）内の主要ファイル・モジュール構成は以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch / save）
    - news_collector.py              — RSS ニュース収集・保存ロジック
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン（差分取得 / 統合）
    - calendar_management.py         — 市場カレンダー操作・更新ジョブ
    - audit.py                       — 監査ログ（signal/order/execution）の DDL と初期化
    - quality.py                     — データ品質チェック群
  - strategy/
    - __init__.py                    — 戦略関連のプレースホルダ
  - execution/
    - __init__.py                    — 発注/執行関連のプレースホルダ
  - monitoring/
    - __init__.py                    — 監視機能のプレースホルダ

（各モジュールの詳細はソースコメントや docstring を参照してください）

## 開発メモ / 設計上の注意

- 時刻／タイムゾーンは明確に UTC を使用する方針（fetched_at や監査ログの TIMESTAMP）。
- DuckDB を採用しているため、軽量で高速にローカル分析が可能です。運用時はファイルパス（DUCKDB_PATH）を適切に設定してください。
- ニュース収集でのセキュリティ対策（SSRF / XML Bomb / レスポンスサイズ制限）を実装済みです。
- ETL は差分更新を行い、バックフィル日数によって後出し修正を吸収します。
- 監査ログ（audit）はトレーサビリティ確保のため削除しない前提で設計しています。

## 参考（よく使う関数のまとめ）

- data.schema.init_schema(db_path) — DuckDB を初期化して接続を返す
- data.jquants_client.get_id_token() — J-Quants ID トークン取得
- data.jquants_client.fetch_daily_quotes(...) — 株価日足取得
- data.jquants_client.save_daily_quotes(conn, records) — raw_prices へ保存
- data.pipeline.run_daily_etl(conn, ...) — 日次 ETL 実行
- data.news_collector.run_news_collection(conn, ...) — RSS 一括収集
- data.calendar_management.calendar_update_job(conn, ...) — カレンダー夜間更新
- data.audit.init_audit_db(path) — 監査ログ DB 初期化
- data.quality.run_all_checks(conn, ...) — 品質チェック一括実行

---

この README はリポジトリ内の docstring とソースコードから作成しています。導入や運用の際は、環境変数の管理、J-Quants 利用規約、証券会社 API（kabuステーション等）の運用ルールに従ってください。必要であれば README を拡張して実運用手順（systemd / cron の設定、監視・アラート設計、運用プレイブック）を追加できます。