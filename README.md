# KabuSys

日本株自動売買システムのライブラリ群（データ取得・ETL・スキーマ・監査・ニュース収集など）

このリポジトリは J-Quants / kabuステーション 等の外部サービスからデータを収集し、DuckDB に保管・品質チェックを行い、戦略／発注レイヤへ繋ぐための基盤ライブラリ群を提供します。

---

## 概要

主な目的は以下です。

- J-Quants API から株価（日足）、財務（四半期 BS/PL）、JPX カレンダーを取得する
- RSS フィードからニュースを収集して正規化 & DuckDB に保存する
- DuckDB のデータスキーマを定義・初期化する（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）を提供する
- 監査ログ（signal → order_request → executions のトレーサビリティ）を提供する

設計上のポイント：
- API レート制限遵守（J-Quants は 120 req/min）
- 冪等性（DuckDB への INSERT は ON CONFLICT 句でハンドリング）
- リトライ・トークン自動リフレッシュ対応（401 を検知して再取得）
- ニュース収集は SSRF / XML Bomb / Gzip Bomb 等の対策済み
- 品質チェック（欠損・重複・スパイク・日付不整合）を実装

---

## 機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）
  - RateLimiter、リトライ／指数バックオフ、401 時のトークンリフレッシュ

- data/news_collector.py
  - RSS フィード取得（fetch_rss）、前処理（preprocess_text）
  - 記事ID生成（URL 正規化 → SHA-256）
  - DuckDB への保存（save_raw_news, save_news_symbols, run_news_collection）
  - SSRF / サイズ上限 / defusedxml による XML セーフガード

- data/schema.py
  - DuckDB のすべてのテーブル DDL 定義と init_schema(db_path) による初期化
  - インデックス定義と get_connection()

- data/pipeline.py
  - 差分更新ロジック、バックフィル、run_daily_etl による日次 ETL（カレンダー→価格→財務→品質チェック）

- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間カレンダー差分取得

- data/quality.py
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - QualityIssue 型により結果を返す

- data/audit.py
  - 監査ログテーブル（signal_events, order_requests, executions）と init_audit_db

- config.py
  - 環境変数読み込み（.env / .env.local をプロジェクトルートから自動ロード）
  - Settings オブジェクト経由で設定値を取得
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD

- execution/, strategy/, monitoring/
  - パッケージプレースホルダ（extension が想定される場所）

---

## 必要要件（依存関係）

最低限の依存パッケージ（例）：
- Python 3.9+
- duckdb
- defusedxml

実際のインストールはプロジェクトの pyproject.toml / requirements.txt に従ってください。最小例:

pip install duckdb defusedxml

（本 README は依存解決ファイルの存在を仮定しておらず、環境によって追加依存が必要です）

---

## セットアップ手順

1. リポジトリをクローン / ワークスペースを準備
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)
3. 必要なパッケージをインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb defusedxml
4. 環境変数を設定（.env をプロジェクトルートに作成）
   - プロジェクトは起点ファイルから親ディレクトリを上がって .git または pyproject.toml を探し、そこをルートとみなして .env/.env.local を自動読み込みします。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例 .env（必須項目はプロジェクトで利用する機能により異なります）:
KABUSYS_ENV=development
LOG_LEVEL=INFO

# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知などに使用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

5. データベースの初期化
   - DuckDB スキーマを初期化：python REPL 等で以下を実行
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
   - 監査ログ専用に初期化する場合:
     from kabusys.data import audit
     conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡単なコード例）

以下は典型的な利用フローのサンプルです。スクリプトから呼び出して ETL を実行したり、ニュース収集を回したりできます。

- DuckDB スキーマ初期化（1回だけ）

```python
from kabusys.data import schema

# ファイルパスは settings.duckdb_path を使っても良い
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants のトークンは環境変数から自動使用）

```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema を行っている前提
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集を実行（既知銘柄リストがある場合は紐付けも可能）

```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄コード文字列の集合（例: {"7203","6758"...}）
results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

- J-Quants から直接価格を取得（テスト等）

```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 監査スキーマを初期化（audit 用）

```python
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須で使用する機能あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知機能で必要）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

settings オブジェクトからは kabusys.config.settings.<プロパティ> でアクセスできます。

---

## セキュリティ・設計上の注意

- J-Quants リクエストはレート制限・リトライを組み込んでありますが、他の API を追加する際もレート管理を考慮してください。
- news_collector は SSRF 対策（スキーム検証・プライベートアドレスの拒否・リダイレクト検査）と XML 解釈の安全化（defusedxml）を行っています。外部の URL を扱う部分は十分注意してください。
- DuckDB に保存する際は ON CONFLICT を使った冪等処理を行っていますが、外部からの直接挿入などでスキーマ整合が崩れると想定外の動作になることがあります。
- すべての timestamp は UTC を使うことを想定している箇所があるため、アプリ全体でタイムゾーン運用方針を統一してください。

---

## ディレクトリ構成

（主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数・Settings
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント・保存処理
    - news_collector.py            -- RSS 収集・保存・銘柄抽出
    - schema.py                    -- DuckDB スキーマ定義・初期化
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       -- 市場カレンダー操作・ジョブ
    - audit.py                     -- 監査ログテーブル初期化
    - quality.py                   -- データ品質チェック
  - strategy/
    - __init__.py                  -- 戦略用パッケージ入口（拡張場所）
  - execution/
    - __init__.py                  -- 発注/実行レイヤ（拡張場所）
  - monitoring/
    - __init__.py                  -- 監視・通知関連（拡張場所）

---

## 開発・テスト時のヒント

- 自動 .env ロードは便利ですが、テストでは環境ごとに値を注入したい場合があります。その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境変数を設定してください。
- モジュール内部でネットワーク呼び出しを行う箇所（news_collector._urlopen 等）はテストでモックしやすいように設計されています。
- DuckDB は ":memory:" を渡すことでインメモリ DB を利用できます（テストで高速に使えます）。

---

## 連絡・貢献

この README はコードベースの現状を元にまとめたものです。strategy / execution / monitoring 等は拡張の余地があり、貢献歓迎です。バグ報告・機能要求は Issue を立ててください。

---

以上。必要であれば、README に含めるサンプル .env.example や詳細な実行スクリプト例（cron/airflow 等での日次スケジュール）も作成できます。どの追加情報が欲しいか教えてください。