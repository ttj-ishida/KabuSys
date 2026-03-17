# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注→約定トレース）などを提供するモジュール群を含みます。

本リポジトリは src パッケージ配下に実装されており、ライブラリとしてインポートして利用します。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたスキーマ定義と冪等なデータ保存
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 等の防御措置、GZip/サイズ制限）
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ（シグナル → 発注要求 → 約定 を UUID 連鎖でトレース）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント:
- API レート制限やリトライ、トークン自動刷新を組み込み
- DuckDB の ON CONFLICT / RETURNING を活用して冪等性・正確な挿入把握
- セキュリティ対策（XML デコードの defusedxml、SSRF 対策、レスポンスサイズ制限 等）
- ETL は各ステップのエラーハンドリングを行い、可能な限り処理を継続

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ID トークン取得、日足/財務/カレンダー取得、DuckDB への保存関数）
  - レートリミッタ、指数バックオフ、401 時のトークン自動更新を実装
- data/news_collector.py
  - RSS フィード取得、XML 安全パース、URL 正規化、記事ID生成（SHA-256 先頭 32 文字）、DuckDB への冪等保存、銘柄抽出・紐付け
- data/schema.py
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution 層）を定義し初期化する関数
- data/pipeline.py
  - 日次 ETL（差分取得・バックフィル・品質チェック）を実行する run_daily_etl 等
- data/calendar_management.py
  - market_calendar テーブルを用いた営業日判定、next/prev_trading_day、夜間の calendar_update_job
- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）定義・初期化
- data/quality.py
  - 欠損、スパイク、重複、日付不整合のチェックと QualityIssue 集計
- strategy/, execution/, monitoring/
  - パッケージスケルトン（将来的な戦略・発注・監視ロジック配置場所）

---

## 必要条件（Dependencies）

- Python 3.9+（ソースに型ヒントで Union 表現や typing 機能を使用）
- 必要なライブラリ（最低限）:
  - duckdb
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください）

インストール例:
```
pip install duckdb defusedxml
```

またはパッケージのセットアップが用意されている場合:
```
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンし、開発環境を作成する:
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

2. 環境変数（.env）を用意する  
   プロジェクトは .env / .env.local を自動読み込みします（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack Bot トークン（通知用）
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   オプション（デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL （デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: monitoring 用 sqlite パス（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読込を無効化

   .env（例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマの初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   audit（監査ログ）を別 DB に初期化する場合:
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（クイックスタート）

- 日次 ETL を実行する（ETL は J-Quants から差分取得し DuckDB に保存、品質チェックも実行）:
  ```python
  from datetime import date
  import kabusys
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集（RSS）を実行して raw_news に保存・銘柄紐付け:
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  # sources を省略するとデフォルトソース（Yahoo Finance ビジネス等）を使用
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count}
  ```

- J-Quants の ID トークンを取得（直接呼び出す場合）:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照
  ```

- カレンダー更新バッチ（夜間ジョブ）:
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェックを個別に実行:
  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 実装上の注意点

- 環境読み込み: `kabusys.config` はパッケージの位置を基準にプロジェクトルート（.git または pyproject.toml）を探し、.env / .env.local を自動的にロードします。OS 環境変数が優先されます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の初期化は冪等です。既存テーブルがあればスキップされます。
- jquants_client はモジュールレベルでトークンキャッシュを行い、ページネーション間で同一トークンを共有します。401 発生時は自動で refresh（1回）を試みます。
- news_collector は SSRF 対策、XML 安全パース、応答サイズ制限、Gzip 解凍後のサイズ検査等を実装しています。RSS の不正なリンクや大きなレスポンスはスキップされます。

---

## ディレクトリ構成

（src 配下の主なファイル・モジュール）
- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント & DuckDB 保存
      - news_collector.py            -- RSS ニュース収集・保存・銘柄抽出
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       -- マーケットカレンダー管理（営業日判定 等）
      - audit.py                     -- 監査ログ（signal/order/execution）
      - quality.py                   -- データ品質チェック
    - strategy/
      - __init__.py                  -- 戦略用パッケージ（拡張ポイント）
    - execution/
      - __init__.py                  -- 発注/実行関連（拡張ポイント）
    - monitoring/
      - __init__.py                  -- 監視関連（拡張ポイント）

---

## 開発・貢献

- 新しい機能は各サブパッケージ（data, strategy, execution, monitoring）にモジュールを追加してください。
- DuckDB に対するスキーマ変更は schema.py の DDL を修正後、マイグレーション方針をチームで合意してください（現在は CREATE TABLE IF NOT EXISTS ベース）。
- テスト時は自動 .env ロードを無効化するか（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）、テスト専用の .env.test を利用してください。
- ネットワーク呼び出しは可能な限りモックしてユニットテストを作成してください（例: news_collector._urlopen の差し替え等）。

---

以上。必要であれば README に実行例のシェルスクリプトや pyproject/Makefile を追加するテンプレートも作成します。どの形式（簡易実行スクリプト、systemd / cron ジョブ例、Dockerfile 等）を追加したいか教えてください。