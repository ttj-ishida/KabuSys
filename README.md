# KabuSys

日本株自動売買システムのライブラリ（KabuSys）。  
データ取得、ETL（差分取得・保存・品質チェック）、ニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）、および戦略/実行/監視のための基盤モジュール群を提供します。

---

## 概要

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。主に以下の機能を備え、堅牢で再現性のあるデータ収集と保存、品質管理、監査トレースを重視しています。

- J-Quants API 経由での株価・財務・マーケットカレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、Gzip/サイズ制限）
- DuckDB を用いた 3 層（Raw / Processed / Feature）+ Execution / Audit のスキーマ定義と初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、翌/前営業日検索）
- 監査ログ（signal → order_request → executions を UUID で連鎖してトレース可能）
- 簡易の戦略・実行・監視用モジュールのプレースホルダ（拡張可能）

---

## 主な機能一覧

- data/jquants_client.py
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得
  - レート制御（120 req/min）、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等的保存（ON CONFLICT … DO UPDATE）
- data/news_collector.py
  - RSS 取得・パース、記事正規化、ID 生成（URL 正規化 + SHA-256）
  - SSRF 対策（スキーム検証、内部アドレスブロック、リダイレクト検査）
  - レスポンスサイズ・gzip 対策、DuckDB へのバルク保存（INSERT ... RETURNING）
  - 記事から銘柄コード抽出（4桁コード）
- data/schema.py
  - DuckDB 上のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) で DB 初期化
- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得の自動算出、backfill 対応、品質チェック（欠損・スパイク・重複・日付不整合）
- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間バッチ更新
- data/audit.py
  - 監査テーブル（signal_events / order_requests / executions）初期化
  - init_audit_db(db_path) で監査用 DB を初期化
- data/quality.py
  - 各種データ品質チェック（QualityIssue を返却）
- config.py
  - 環境変数管理。プロジェクトルートの `.env` / `.env.local` 自動ロード（無効化フラグあり）
  - 必須環境変数チェックと settings オブジェクト提供
- strategy/, execution/, monitoring/
  - 戦略・発注・監視関連の拡張用パッケージ（プレースホルダ）

---

## セットアップ

前提: Python 3.9+（コードは typing | union 等を使用）。推奨は仮想環境を使用。

1. リポジトリをクローン / コピー
   - このプロジェクトは src レイアウトを想定しています（例: `src/kabusys`）。

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要なライブラリ（抜粋）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 実プロジェクトでは pyproject.toml / requirements.txt を用意している想定です:
     - pip install -e . などでインストール

4. 環境変数 / .env
   - プロジェクトルートに `.env`（および `.env.local`）を置けば自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須環境変数（少なくともテストや API 呼び出しで必要）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
   - オプション:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  (デフォルト: INFO)
     - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
     - SQLITE_PATH=data/monitoring.db
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（主要 API と実行例）

以下は Python REPL やスクリプトから使う最小例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  ```

- 監査 DB 初期化（監査専用 DB を使いたい場合）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # オプションで target_date, id_token, run_quality_checks 等を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes を与えると記事 → 銘柄紐付けを行います（set of "7203", "6758" ...）
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(res)
  ```

- J-Quants の生データ取得（個別利用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from kabusys.config import settings

  token = get_id_token()  # settings.jquants_refresh_token を利用して id_token を取得
  quotes = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
  ```

- マーケットカレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェック（個別／一括）
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意:
- run_daily_etl 等は内部で J-Quants API を呼ぶため、有効なトークンとネットワークアクセスが必要です。
- テスト時は環境変数自動ロードを無効化したり、jquants_client の _urlopen をモックする等の工夫を推奨します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視・他用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動で .env を読み込ませたくない場合に 1 を設定

settings オブジェクト経由でこれらを取得できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## ディレクトリ構成

（重要ファイルのみ抜粋、プロジェクトルートは src/ を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
      - pipeline.py             — ETL パイプライン（run_daily_etl 等）
      - schema.py               — DuckDB スキーマ定義・初期化
      - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
      - audit.py                — 監査（audit）テーブル定義・初期化
      - quality.py              — データ品質チェック
    - strategy/
      - __init__.py             — 戦略モジュール群（拡張ポイント）
    - execution/
      - __init__.py             — 発注実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py             — 監視・メトリクス用（拡張ポイント）

---

## 設計・運用上の注意点

- J-Quants API
  - レートリミット 120 req/min を尊重するため固定間隔スロットリングを適用
  - リトライは指数バックオフで最大 3 回、HTTP 408/429/5xx を再試行対象
  - 401 が返った場合は refresh token から id_token を再取得して 1 回リトライ
  - 取得時刻（fetched_at）は UTC で記録し、Look-ahead bias を防止

- News Collector
  - URL 正規化・トラッキングパラメータ削除により記事の冪等性を確保（ID は SHA-256 ハッシュ）
  - SSRF 対策（スキーム検証・プライベートアドレスブロック）を実施
  - レスポンスの最大サイズ制限（デフォルト 10 MB）

- DB 保存
  - raw テーブルは ON CONFLICT 句で冪等保存（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）
  - init_schema は冪等的にテーブル・インデックスを作成

- 品質チェック
  - Fail-Fast ではなく問題を収集して呼び出し元が対応を判断する設計

---

## テスト / 開発時のヒント

- 自動 .env ロードを無効化:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- jquants_client のネットワーク呼び出しや news_collector._urlopen をモックしてユニットテストを行う
- DuckDB の in-memory モードを利用:
  - init_schema(":memory:")

---

README はプロジェクトの現状と主要な利用法をまとめたものです。戦略や実行ロジック、外部接続（証券会社 API）の実装は本リポジトリ内のプレースホルダを拡張して実装してください。必要であれば、導入手順の詳細（CI 設定、pyproject / requirements の整備、デプロイ手順、運用 runbook）も作成しますので、その要望を教えてください。