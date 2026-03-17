# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（プロトタイプ）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログなどを備え、戦略層／実行層と連携する基盤機能を提供します。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- J-Quants API からの市場データ（株価日足、財務データ、マーケットカレンダー）取得
- RSS からのニュース収集と記事 -> 銘柄コード紐付け
- DuckDB を用いたスキーマ定義・初期化および冪等保存（ON CONFLICT）
- ETL（差分取得、バックフィル、品質チェック）のパイプライン
- マーケットカレンダーの夜間更新・営業日判定ロジック
- 監査ログ（シグナル → 発注 → 約定のトレース用スキーマ）
- 設定管理（.env / 環境変数）と実行モード（development / paper_trading / live）

設計上の特徴として、API レート制御・リトライ・トークン自動リフレッシュ、Look-ahead バイアス対策（fetched_at 記録）、SSRF 対策、XML パースの堅牢化などが組み込まれています。

---

## 主な機能一覧

- データ取得
  - J-Quants: 日足（OHLCV）、四半期財務データ、マーケットカレンダー
  - RSS: 複数ソースからニュース記事取得、テキスト前処理、記事ID生成（正規化URL→SHA256）
- 永続化
  - DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）
  - 冪等保存（ON CONFLICT / INSERT ... RETURNING を利用）
- ETL & 品質管理
  - 差分取得（最終取得日+backfill に基づく）
  - 日次 ETL（run_daily_etl）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- カレンダー管理
  - 営業日判定、next/prev_trading_day、期間の営業日取得
  - calendar_update_job による夜間更新
- 監査ログ
  - signal_events / order_requests / executions によるトレーサビリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）および環境変数経由での設定

---

## 動作要件（想定）

- Python 3.10 以上（型ヒントに | を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース等）

（実際の requirements はプロジェクトの packaging / requirements.txt を参照してください）

---

## 環境変数 / .env

プロジェクトルートにある `.env` または `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings で _require されるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development, paper_trading, live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

`.env.example` を参考に `.env` を作成してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -e .           （パッケージ化されている場合）
   - または最低限:
     - pip install duckdb defusedxml

4. 環境変数設定
   - プロジェクトルートに `.env` を作成して必須キーを設定
     例:
       JQUANTS_REFRESH_TOKEN=xxxxxxxx
       KABU_API_PASSWORD=your_password
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       DUCKDB_PATH=data/kabusys.duckdb
       KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

6. 監査ログ（audit）テーブルを追加する場合
   - from kabusys.data import audit
     audit.init_audit_schema(conn)
   - あるいは新規 DB として init_audit_db を使用:
     audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（例）

- 基本的な DB 初期化と日次 ETL 実行

  from kabusys.config import settings
  from kabusys.data import schema, pipeline

  # DB 初期化（既存ならスキップ）
  conn = schema.init_schema(settings.duckdb_path)

  # 日次 ETL を実行（target_date 省略で今日）
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブ実行

  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  results = news_collector.run_news_collection(conn)
  print(results)  # {source_name: saved_count, ...}

- J-Quants トークン取得（明示的に行う場合）

  from kabusys.data import jquants_client
  id_token = jquants_client.get_id_token()  # settings.jquants_refresh_token を使う

- カレンダー判定例

  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  from datetime import date
  d = date(2025, 1, 1)
  trading = calendar_management.is_trading_day(conn, d)

注意:
- run_daily_etl 等はネットワークと API トークンを必要とします。
- J-Quants クライアントは内部でレート制限（120 req/min）およびリトライを実装しています。
- NewsCollector は SSRF 対策、gzip サイズ上限、XML の安全なパースを実装しています。

---

## ディレクトリ構成

概要的なツリー（主要ファイル）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / .env 読み込みと Settings
    - data/
      - __init__.py
      - schema.py               — DuckDB スキーマ定義・初期化
      - jquants_client.py       — J-Quants API クライアント（取得・保存）
      - pipeline.py             — ETL パイプライン（run_daily_etl など）
      - calendar_management.py  — マーケットカレンダー管理・判定ロジック
      - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
      - audit.py                — 監査ログ（signal/order/execution）スキーマ初期化
      - quality.py              — データ品質チェック
    - strategy/
      - __init__.py             — 戦略層（拡張想定）
    - execution/
      - __init__.py             — 発注実行層（拡張想定）
    - monitoring/
      - __init__.py             — 監視・メトリクス（拡張想定）

各モジュールはドメイン別に整理されています（data/* がデータ基盤機能の中心）。

---

## 注意事項 / 実運用上のヒント

- トークン管理:
  - J-Quants のリフレッシュトークンは厳重に管理してください。
  - jquants_client は 401 を受け取ると自動でリフレッシュを試みます（1 回）。
- バックフィル:
  - ETL はデフォルトで直近数日分を再取得する設計（backfill_days）です。API の後出し修正を吸収するためです。
- タイムゾーン:
  - 監査ログ等は UTC を前提に保存するように設計されています。
- テスト:
  - 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると便利です。
- セキュリティ:
  - RSS の取得はホストのプライベートアドレスや非 http/https スキームをブロックする等、SSRF 対策が組み込まれています。

---

README に記載した例は本リポジトリにある API を使う最小限の手順です。実際のデプロイ／運用時は、監視・ロギング設定、アクセス制御、シークレット管理（Vault 等）、CI/CD による schema マイグレーション運用などを合わせて整備することを推奨します。