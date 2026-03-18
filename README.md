# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）の README。  
本ドキュメントはリポジトリ内の主要モジュール群（データ取得 / ETL / 品質チェック / 監査ログ等）を使い始めるためのガイドです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主に以下を提供します。

- J-Quants API からの市場データ取得（株価日足、財務データ、JPXカレンダー）
- RSS からのニュース収集と銘柄紐付け
- DuckDB を用いたスキーマ定義・初期化
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日探索）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上のポイントとして、API レート制限遵守、リトライ・トークン自動リフレッシュ、冪等（idempotency）を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（無効化可）
  - 必須環境変数の取得ラッパー（例: JQUANTS_REFRESH_TOKEN）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - リトライ、レート制御、トークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_* 系）
- ニュース収集
  - RSS 取得（gzip 支持、XML 安全パース）
  - URL 正規化・記事 ID 生成（SHA-256 の先頭 32 文字）
  - raw_news への冪等保存、銘柄抽出・紐付け
  - SSRF 対策（スキーム・プライベート IP ブロック、リダイレクト検査）
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit のテーブル定義とインデックス
  - init_schema での初期化
- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新／バックフィル対応
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間差分更新）
- 監査ログ
  - signal_events / order_requests / executions を用いたフルトレーサビリティ
  - init_audit_schema / init_audit_db
- 品質チェック
  - 欠損・重複・スパイク（前日比）・日付不整合などを検出

---

## 必要条件 / 依存

- Python 3.10 以上（型ヒントに `X | Y` 記法を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮に requirements を作る場合）:
```
pip install duckdb defusedxml
```

プロジェクトをパッケージとして扱う場合は、src 配下からインストールする方法等を用いてください（例: pip install -e .）。

---

## 環境変数（.env）

自動でルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（例）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL (任意) — "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python と依存ライブラリをインストール
   - Python >= 3.10
   - pip install duckdb defusedxml

2. リポジトリをクローンし、必要ならプロジェクトをインストール
   - pip install -e . （セットアップ用の packaging がある場合）

3. .env をルートに配置（上記の必須キーを設定）
   - 環境ごとの上書きは .env.local を使う

4. DuckDB スキーマを初期化
   - 例: Python REPL / スクリプトで
     ```python
     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)  # ファイルに作成される
     ```
   - インメモリでテストしたい場合:
     ```python
     conn = schema.init_schema(":memory:")
     ```

5. 監査 DB（任意）初期化
   - 監査用に別 DB を用意する場合:
     ```python
     from kabusys.data import audit
     conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要な API 例）

以下はライブラリの代表的な利用例です。実行環境では `.env` の設定を済ませてください。

- J-Quants の ID トークン取得（内部で settings.jquants_refresh_token を使用）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って POST 実行
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data import schema, calendar_management
  from kabusys.config import settings
  conn = schema.get_connection(settings.duckdb_path)
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS からニュース収集して保存・銘柄紐付け
  ```python
  from kabusys.data import schema, news_collector
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
  results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # source_name -> 新規保存件数
  ```

- DuckDB スキーマの初期化（最初の一回）
  ```python
  from kabusys.data import schema
  schema.init_schema("data/kabusys.duckdb")
  ```

- 監査スキーマの初期化（既存接続に追加）
  ```python
  from kabusys.data import schema, audit
  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn, transactional=True)
  ```

---

## ディレクトリ構成

主要ファイル / モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レートリミット、再試行）
    - news_collector.py
      - RSS 取得、前処理、DuckDB 保存、銘柄抽出
    - schema.py
      - DuckDB 用 DDL 定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分更新、run_daily_etl）
    - calendar_management.py
      - マーケットカレンダーの判定・更新・検索ユーティリティ
    - audit.py
      - 監査ログ用テーブル定義と初期化ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py
    - （戦略モジュールはこのパッケージ下に実装）
  - execution/
    - __init__.py
    - （発注 / ブローカー連携ロジックを置く場所）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連のモジュール）

各モジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取り SQL を通してデータを処理します。ETL 系はエラーや品質問題を個別にログ出力し、呼び出し側が停止・アラート判断を行えるようにしています。

---

## 開発 / テスト時のヒント

- 自動 .env 読み込みを無効にしたいとき:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- テスト用にインメモリ DB を用いると処理が軽くなります:
  ```python
  conn = schema.init_schema(":memory:")
  ```
- news_collector などのネットワーク呼び出しはモックしてユニットテストする設計になっています（例: _urlopen を差し替え）。
- schema.init_schema は冪等（既存テーブルがあればスキップ）です。初回のみ実行してください。
- settings.env は "development", "paper_trading", "live" のいずれかでなければエラーになります。

---

## トラブルシューティング（よくある注意点）

- 環境変数が不足していると Settings のプロパティで ValueError が発生します。エラー文に従って .env を確認してください。
- J-Quants API で 401 が出る場合、jquants_client は自動的にトークンをリフレッシュして 1 回リトライします。トークンが無効な場合は設定を見直してください。
- RSS フィードが大きすぎると MAX_RESPONSE_BYTES（デフォルト 10MB）で拒否されます。
- DuckDB のバージョンや SQL 構文差異による問題が出ることがあります。依存バージョン合わせを確認してください。

---

必要があれば、README に以下を追加できます（要望に応じて）：
- 実行コマンド例（systemd / cron / container）
- CI / テストのセットアップ手順
- 詳細な .env.example ファイル
- 戦略 / 発注フローのサンプル実装

ご希望の追加情報があれば教えてください。