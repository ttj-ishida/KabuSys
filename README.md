# KabuSys — 日本株自動売買システム

## プロジェクト概要
KabuSys は日本株向けの自動売買プラットフォーム用ライブラリです。  
データ取得（J-Quants API）、ETL（DuckDB へ永続化）、データ品質チェック、監査ログ（発注→約定のトレース）など、アルゴリズム取引基盤に必要な基本コンポーネントを提供します。

主な設計方針：
- データ取得はレート制限・リトライ・トークン自動更新に対応
- DuckDB を中心とした 3 層（Raw / Processed / Feature）スキーマによるデータ管理
- ETL は差分取得・バックフィル・品質チェックをサポート（冪等性を重視）
- 発注〜約定の監査ログを UUID ベースで追跡可能

---

## 機能一覧
- J-Quants API クライアント
  - 日足（OHLCV）・四半期財務データ・JPX マーケットカレンダーを取得
  - レート制御、リトライ、401 自動リフレッシュ、ページネーション対応
  - 取得時刻（fetched_at）を UTC で記録
- DuckDB スキーマ管理
  - Raw/Processed/Feature/Execution 層のテーブル定義と初期化
  - インデックス定義によるパフォーマンス最適化
- ETL パイプライン
  - 差分取得（最終取得日からの差分、バックフィル）
  - データ保存（ON CONFLICT DO UPDATE による冪等）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等を通じた完全トレーサビリティ
  - 発注冪等（order_request_id）、UTC タイムスタンプ管理
- モニタリング/通知（Slack トークン等を想定した設定あり）

---

## 要求環境・依存関係
- Python 3.10+（型ヒントに Union | を使用）
- duckdb
- 標準ライブラリ（urllib, json, logging, datetime 等）

（プロジェクトで使用する他のパッケージは必要に応じて追加してください）

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   pip install duckdb
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（デフォルトで OS 環境変数 > .env.local > .env の順で優先）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション/API のパスワード（必須）
   - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

   推奨・任意:
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. DuckDB スキーマ初期化
   - 初回はスキーマを作成します。Python REPL かスクリプトで：
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     # 監査ログを追加する場合
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```

---

## 基本的な使い方

- J-Quants からデータを取得する（簡単な例）
  ```python
  from kabusys.data import jquants_client as jq
  # id_token を省略すると内部キャッシュと自動リフレッシュを用いる
  quotes = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  ```

- ETL（日次パイプライン）を実行する
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  run_daily_etl は次の順で処理します：
  1. 市場カレンダーを先読み（デフォルト 90 日）
  2. 株価（日足）の差分取得（最終取得日から backfill_days、デフォルト 3 日）
  3. 財務データの差分取得（同上）
  4. 品質チェック（欠損・重複・スパイク・日付不整合）

- 監査ログの初期化（専用 DB）
  ```python
  from kabusys.data import audit
  conn = audit.init_audit_db("data/kabusys_audit.duckdb")
  # もしくは既存 conn に対して
  # audit.init_audit_schema(conn)
  ```

- 品質チェックを個別で実行する
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

---

## よく使う API（概要）
- kabusys.config.settings — 環境設定取得（プロパティ経由で取得）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline.run_daily_etl — 日次 ETL 実行
- kabusys.data.quality.run_all_checks — データ品質チェック
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査ログ初期化

---

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py           — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
      - schema.py         — DuckDB スキーマ定義・初期化
      - pipeline.py       — ETL パイプライン（差分取得・品質チェック）
      - quality.py        — データ品質チェック
      - audit.py          — 監査ログ（発注〜約定トレース）
      - pipeline.py
      - audit.py
    - strategy/
      - __init__.py       — 戦略層の雛形（実装は拡張）
    - execution/
      - __init__.py       — 発注実行層の雛形（実装は拡張）
    - monitoring/
      - __init__.py       — 監視／通知関連（拡張予定）

---

## 注意事項・運用メモ
- J-Quants の API レート制限（120 req/min）を遵守する実装になっています（内部でスロットリング）。
- get_id_token はリフレッシュトークンから ID トークンを取得します。401 受信時は自動でリフレッシュして 1 回リトライします。
- DuckDB の初期化は冪等設計です。既存テーブルがある場合は上書きせずスキップします。
- ETL は Fail-Fast ではなく、各ステップでエラーを収集して可能な処理は継続します。ETLResult で詳細を確認してください。
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env のロードを無効化できます。

---

## 開発
- コード規約・テスト・CI はプロジェクト方針に従って追加してください（本リポジトリはコアモジュールの提供を目的としています）。
- strategy / execution / monitoring は拡張ポイントです。実運用ではブローカー API（kabuステーション等）との接続実装やリスク管理を実装してください。

---

必要であれば、利用例スクリプト、.env.example ファイル、docker-compose によるローカルテスト手順なども追記できます。どの情報を優先して追加しますか？