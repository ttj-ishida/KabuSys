# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。  
J-Quants / RSS 等からのデータ収集、DuckDB を使ったスキーマ管理、ETL パイプライン、品質チェック、監査ログ（発注→約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための内部ライブラリ群です。主に以下を目的としています。

- J-Quants API からの市場データ（株価日足、財務データ、マーケットカレンダー）の取得・保存
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダーの運用ロジック（営業時間判定、次営業日計算など）
- 発注・約定の監査ログを残すためのスキーマとユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴として、API レート制限遵守、リトライ・トークン自動リフレッシュ、冪等保存（ON CONFLICT）、SSRF/XML 攻撃対策などに配慮しています。

---

## 機能一覧

主な機能（モジュール／代表的な関数）

- kabusys.config
  - .env / .env.local と OS 環境変数の読み込み（自動ロード、無効化フラグあり）
  - settings: J-Quants / kabu API / Slack / DB パス / 環境判定 等のプロパティ
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles), save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)
  - セキュリティ対策（defusedxml、SSRF リダイレクト検査、応答サイズ制限、トラッキングパラメータ除去）
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
  - Raw / Processed / Feature / Execution / Audit 用テーブルとインデックスを定義（冪等）
- kabusys.data.pipeline
  - run_prices_etl(...), run_financials_etl(...), run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, ...) — 日次 ETL の統合エントリ
  - 差分更新、バックフィル、品質チェック連携
- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(...)
  - calendar_update_job(conn, lookahead_days=90)
- kabusys.data.quality
  - check_missing_data(conn, target_date=None)
  - check_spike(conn, target_date=None, threshold=...)
  - check_duplicates(conn, target_date=None)
  - check_date_consistency(conn, reference_date=None)
  - run_all_checks(conn, ...)
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)
  - 監査（signal → order_request → executions）用テーブル定義とインデックス

（strategy / execution / monitoring パッケージは存在しますが、本コードベースでは初期化のみです）

---

## 要件

- Python 3.10 以上（型注釈に | を使用）
- 必要な外部ライブラリ（例）
  - duckdb
  - defusedxml

実際のプロジェクトでは requirements.txt や pyproject.toml を用意して依存管理してください。

---

## セットアップ手順

1. リポジトリをクローン／取得する

2. 仮想環境を作成して有効化（推奨）

   Linux/macOS:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   # またはプロジェクトの依存ファイルがあればそれを使う:
   # pip install -r requirements.txt
   ```

4. パッケージを編集モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数 (.env) を準備する  
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（環境変数優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（コードで _require() されるもの）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意設定（デフォルトあり）
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

6. DuckDB スキーマ初期化
   Python REPL かスクリプト内で:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # フォルダがなければ自動作成
   ```

---

## 使い方（代表的な例）

以下はライブラリを使うための簡単なサンプルコード例です。

- DuckDB の初期化（必須）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

- J-Quants トークン取得（手動）
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 株価データを取得して保存（個別）
  ```python
  from kabusys.data import jquants_client as jq
  from datetime import date

  records = jq.fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 3, 31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- 日次 ETL 実行（カレンダー取得 → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
  print(result.to_dict())
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection

  # known_codes は銘柄抽出に使う有効コードセット（任意）
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存数, ...}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- 監査ログ用スキーマ初期化（既存 conn に追加）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn)
  ```

---

## 注意点 / 実装上の設計・セキュリティ考慮

- J-Quants クライアントは 120 req/min のレート制限を守る実装です。大規模並列呼び出しには注意してください。
- ネットワークエラーや 429/408/5xx を対象に指数バックオフでリトライします。401 はトークン自動リフレッシュを試みます。
- news_collector は XML パースに defusedxml を利用、SSRF 対策（リダイレクト先の検査、プライベートIP へのアクセスブロック）、レスポンスサイズ制限など複数の防御を実装しています。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）にしており、再実行しても安全になるよう配慮しています。
- all-timestamp は UTC の扱いを基本にしています（監査ログ等で明示的に UTC をセット）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ構成（簡略）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save）
    - news_collector.py         — RSS 収集・解析・保存
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py    — マーケットカレンダー管理
    - audit.py                  — 監査ログスキーマ（発注→約定トレース）
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py               — 戦略層（拡張点）
  - execution/
    - __init__.py               — 発注・ブローカー連携（拡張点）
  - monitoring/
    - __init__.py               — 監視・メトリクス（拡張点）

---

## 拡張 / 実運用のヒント

- strategy / execution / monitoring はプラグイン的に実装・追加することを想定しています。戦略は signal_events を生成し、order_requests→実発注→executions を通じて監査ログを残す設計です。
- 本番（live）運用時は KABUSYS_ENV=live を設定し、ログや安全制約を厳格にするなど運用ポリシーを組み込んでください。
- DuckDB ファイルは定期バックアップ（S3 等）を検討してください（監査ログは削除しない前提）。
- ETL のスケジューリングは cron / Airflow / Prefect など外部ジョブランナーを使うと管理しやすいです。

---

問題点や追加でREADMEに載せたい内容（例：CI、テスト、デプロイ手順、requirements.txt の内容、.env.example）などがあれば教えてください。必要に応じて README を追記・改善します。