# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ (kabusys)
バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集、データベーススキーマ管理、監査ログ、データ品質チェックなど、アルゴリズムトレーディング基盤に必要な共通機能を提供する Python モジュール群です。主に以下の機能を備え、J-Quants API や kabuステーション など外部サービスと連携するためのユーティリティを含みます。

- J-Quants API クライアント（データ取得・ページネーション対応・トークン自動リフレッシュ・レート制御・再試行）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 環境変数 / .env 管理（自動ロード機能）

設計方針として、データの冪等性、トレーサビリティ（UTC タイムスタンプ）、レート制限遵守、再試行による堅牢性を重視しています。

---

## 主な機能一覧

- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数を保護）
  - 必須変数は Settings クラスを通じて取得（未設定時はエラー）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足（OHLCV）・財務データ・JPX マーケットカレンダーの取得
  - ページネーション対応、ページ間で ID トークンを共有
  - レート制限（120 req/min）に基づくスロットリング
  - 408/429/5xx に対する指数バックオフ付きリトライ（最大 3 回）
  - 401 を検出した場合はリフレッシュトークンで自動再取得して再試行

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - インデックスや外部キーを含む初期化関数 `init_schema(db_path)`
  - 既存 DB への接続取得関数 `get_connection(db_path)`

- 監査ログ（Audit） (`kabusys.data.audit`)
  - signal_events / order_requests / executions テーブル
  - 発注の冪等性（order_request_id）とトレース可能性を保証
  - `init_audit_schema(conn)` / `init_audit_db(db_path)` を提供

- データ品質チェック (`kabusys.data.quality`)
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複（PK）検出、日付不整合検出
  - 各チェックは QualityIssue オブジェクトのリストを返す（Fail-Fast ではない）
  - `run_all_checks(conn, ...)` でまとめて実行可能

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（typing の Union 表記等に依存）
- DuckDB を使用（パッケージでインストール）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 最低依存: duckdb
   - 例:
     - pip install duckdb

   （プロジェクトで requirements.txt や pyproject.toml がある場合はそちらを使用してください。）

3. ソースをインストール（開発時）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成（自動で読み込まれます）
   - 必須環境変数の例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意 / デフォルト:
     - KABUSYS_ENV=development  (valid: development, paper_trading, live)
     - LOG_LEVEL=INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は基本的な利用フロー例です。

- DuckDB スキーマ初期化
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- J-Quants から日足を取得して保存
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  # トークンは設定済みであればモジュール内キャッシュを利用（自動リフレッシュあり）
  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, records)
  print(f"saved {saved} rows")
  ```

- 監査ログの初期化（既存 conn に追加）
  ```
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

  または監査専用 DB を作る:
  ```
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- データ品質チェックを実行
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
  ```

- 設定値参照
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

注意:
- J-Quants API へのリクエストはモジュール内でレート制御・リトライ・トークンリフレッシュを行いますが、並列化する場合はアプリ側で適切な設計（スロットリング共有など）を検討してください。
- DuckDB の path デフォルトは `data/kabusys.duckdb`。必要に応じて `settings.duckdb_path` を参照して下さい。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu API パスワード
- SLACK_BOT_TOKEN: Slack ボットトークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成

リポジトリ（src/kabusys）内の主なファイル構成:

- src/kabusys/
  - __init__.py            - パッケージ定義（__version__ = "0.1.0"）
  - config.py              - 環境変数・設定管理、.env 自動ロード、Settings クラス
  - data/
    - __init__.py
    - jquants_client.py    - J-Quants API クライアント（取得 / 保存関数）
    - schema.py            - DuckDB スキーマ定義と初期化 (init_schema, get_connection)
    - audit.py             - 監査ログテーブル定義と初期化
    - quality.py           - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - (その他): news / executions など向けの Raw テーブル定義を含む
  - strategy/
    - __init__.py          - 戦略モジュール（骨子）
  - execution/
    - __init__.py          - 発注実行モジュール（骨子）
  - monitoring/
    - __init__.py          - 監視用（骨子）

主要なスキーマ（DuckDB）:
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 監査: signal_events, order_requests, executions

---

## ログ / トラブルシューティング

- ログレベルや出力は `LOG_LEVEL` 環境変数で調整してください。
- .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から行われます。テスト等で自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API で 401 が返った場合は自動的にリフレッシュトークンで ID トークンを再取得して再試行します。リフレッシュに失敗すると例外となります。
- DuckDB 初期化時に親ディレクトリが存在しない場合は自動作成されます。

---

## 貢献・拡張

- strategy / execution / monitoring 以下は骨組みが用意されています。実際の戦略ロジック、注文フロー、監視ロジックはアプリケーション側で実装してください。
- 外部 API クライアントの追加（ニュース API 等）や、特徴量生成パイプラインの拡張は data 層に追加してください。
- テストを書く際は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して環境依存を切り離すことを推奨します。

---

この README はコードベースの現状（src/kabusys 内）に基づいて作成しました。実運用前に各種環境変数や DB スキーマの確認、外部サービスの認証情報の安全な管理を必ず行ってください。ご不明な点や README の拡張希望があれば教えてください。