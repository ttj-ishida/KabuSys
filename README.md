# KabuSys

日本株向けの自動売買＆データ基盤ライブラリ（KabuSys）。  
J-Quants や RSS を使った市場データ収集、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集・銘柄紐付け、監査ログ用スキーマなどを提供します。

---

## 概要

KabuSys は次の目的のために設計された Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得するクライアント
- DuckDB を用いたデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS を用いたニュース収集と銘柄コード抽出・紐付け
- 監査ログ（signal → order → execution）を記録するスキーマ

設計上のポイント：
- API レートリミットやリトライ、トークン自動リフレッシュに対応
- DuckDB への保存は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）設計
- RSS 収集時に SSRF や XML 攻撃、巨大レスポンス等へ対策あり
- 品質チェック（欠損・重複・スパイク・日付整合性）を提供

---

## 機能一覧

- 環境設定管理（.env の自動ロード / 必須キー検査）
- J-Quants API クライアント（取得・認証・ページング・リトライ・レート制御）
  - 株価日足（OHLCV）
  - 財務（四半期 BS/PL）
  - マーケットカレンダー（JPX）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution / audit）
- ETL パイプライン（run_daily_etl を中心とした日次処理）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- RSS ニュース収集モジュール（記事ID生成、テキスト前処理、銘柄抽出、DB保存）
- マーケットカレンダー管理（営業日判定・前後営業日取得・夜間更新ジョブ）
- 監査ログスキーマ（信号→発注→約定のトレース可能なテーブル構造）

---

## 必要条件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

実際に使用する機能に応じて追加パッケージが必要になる場合があります。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   # 開発時: pip install -e .
   ```

4. 環境変数を設定
   - KabuSys では .env または OS 環境変数から設定を読み込みます。
   - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env, .env.local を自動ロードします。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   サンプル `.env`（プロジェクトルートに配置）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化（例）
   Python REPL またはスクリプト内で:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```
   - init_schema は親ディレクトリ作成、DDL とインデックスを全て作成します（冪等）。

---

## 使い方（例）

以下は主要なモジュールの簡単な使い方例です。

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- J-Quants の ID トークン取得（手動）
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を利用
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集（RSS）→ raw_news 保存 → 銘柄紐付け
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes: 銘柄抽出に使う有効な4桁コードの集合を用意
  known_codes = {"7203", "6758", "9984", ...}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: new_count, ...}
  ```

- 個別データ取得（J-Quants）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

  quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
  fin = fetch_financial_statements(code="7203")
  ```

- 監査スキーマ初期化（audit）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)  # 既存接続に監査テーブルを追加
  ```

エラーハンドリングやログは各モジュールで行われます。設定不足（必須環境変数が見つからない等）の場合、Settings プロパティは ValueError を投げます。

---

## ディレクトリ構成

主要ファイル / モジュール（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - news_collector.py      -- RSS ニュース収集・前処理・DB 保存
    - schema.py              -- DuckDB スキーマ定義・初期化
    - pipeline.py            -- ETL パイプライン（差分更新・バックフィル・品質チェック）
    - calendar_management.py -- マーケットカレンダーの管理・営業日ロジック
    - audit.py               -- 監査ログ（signal / order_request / executions）スキーマ
    - quality.py             -- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（strategy / execution / monitoring は将来的な戦略や発注・監視ロジックを想定したパッケージ）

---

## 補足（設計上の注意点）

- .env の自動読み込みはプロジェクトルート（.git もしくは pyproject.toml）を基準に行われます。テストや一時的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- J-Quants API 呼び出しは内部でレート制御とリトライを行います（120 req/min, 最大 3 回）。
- DuckDB への保存は冪等に設計されています。外部からデータを挿入する場合でも ON CONFLICT などにより重複制御を行っています。
- RSS 収集はセキュリティ対策（SSRF、XML bomb、gzip サイズ制限）を実装しています。外部 URL を扱うため、例外処理により堅牢化されています。
- 品質チェックは Fail-Fast ではなく、可能な限りすべての問題を収集して呼び出し側に返します。呼び出し側が重大度に基づいて処理を決めてください。

---

## 連絡・貢献

バグ報告や機能提案は Issue を立ててください。Pull Request は歓迎します。ドキュメントやテストの追加は特に助かります。

---

README は以上です。具体的な実行例や CI 設定、追加依存関係（Slack 通知や証券会社 API のクライアント等）については利用ケースに応じて追記してください。