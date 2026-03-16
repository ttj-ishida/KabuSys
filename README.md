# KabuSys

日本株向けの自動売買基盤コンポーネント群（ライブラリ）。

このリポジトリはデータ収集・ETL・品質チェック・監査ログなど、自動売買システムのデータ基盤と監査周りの機能を提供します。戦略・発注実行・監視周りのパッケージは骨組みが用意されています。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API から株価（日足）・財務データ・JPX マーケットカレンダーを取得して DuckDB に保存する。
- 差分更新（バックフィル含む）、レート制御、リトライ、トークン自動リフレッシュなど堅牢な API クライアントを提供する。
- データの冪等保存（ON CONFLICT DO UPDATE）により重複や再取得に耐える ETL を実現する。
- データ品質チェック（欠損、スパイク、重複、日付不整合）を行い、問題の監査情報を返す。
- シグナルから約定までのトレーサビリティを確保する監査スキーマを提供する。

---

## 機能一覧

- 環境設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数チェック
  - KABUSYS_ENV（development / paper_trading / live）とログレベル管理

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足（OHLCV）、四半期財務、マーケットカレンダー取得
  - レートリミット（120 req/min）順守（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - fetched_at による取得時刻の記録（UTC）
  - DuckDB への冪等保存用 save_* 関数

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化関数 `init_schema()` / `get_connection()` を提供
  - 監査ログ用のスキーマ初期化も別モジュールで提供

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL（カレンダー先読み、差分取得、バックフィル、品質チェック）
  - 個別ジョブ（株価 / 財務 / カレンダー）を実行するヘルパー
  - 品質チェックと結果集約（ETLResult）

- データ品質チェック (`kabusys.data.quality`)
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日付・非営業日）検出
  - 各種チェックは QualityIssue オブジェクトで結果を返す

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - シグナル/発注要求/約定の監査テーブルを定義・初期化
  - order_request_id を冪等キーとして二重発注防止をサポート

---

## 前提条件 / 要件

- Python 3.10+
  - 型注釈に Python 3.10 の union 演算子（|）を使用しています。
- duckdb パッケージ（DB 用）
- ネットワーク接続（J-Quants API へアクセスする場合）
- 必要に応じて Slack 連携用トークンなど

（本 README はライブラリのみの説明です。実際の注文送信やブローカ連携は別実装が必要です。）

---

## 環境変数

必須（ライブラリを使う際に設定が必要）:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:

- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動で .env を読み込まない
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: デフォルト `data/monitoring.db`
- KABU_API_BASE_URL: デフォルト `http://localhost:18080/kabusapi`

.env 読み込みの挙動:

- プロジェクトルート（.git または pyproject.toml を基準）を探索して自動的に読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- .env.local は .env を上書きする（ただし OS 環境変数は保護される）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## セットアップ手順（開発向けクイックスタート）

1. リポジトリをクローンする

   git clone <repo-url>
   cd <repo-dir>

2. Python 仮想環境を作成・有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール

   pip install duckdb

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

4. 環境変数を用意する

   プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、必須変数を設定します。例:

   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（基本例）

以下はライブラリを利用した主要な操作例です。Python スクリプト内で呼び出します。

- DuckDB スキーマ初期化

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

  - 引数に ":memory:" を渡すとインメモリ DB を使用します。
  - 初回は親ディレクトリを自動作成します。

- 監査ログテーブルの初期化（既存接続へ追加）

  from kabusys.data import audit
  audit.init_audit_schema(conn)

- 日次 ETL を実行する（市場カレンダー先読み・差分取得・品質チェック）

  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())

  # ETL結果を確認
  print(result.to_dict())

- 個別ジョブの実行（例: 株価差分ETL）

  from datetime import date, timedelta
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # 例: 過去3日分をバックフィルして当日まで取得
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

- 品質チェックのみ実行

  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

注意点:

- J-Quants API 呼び出し時は内部でレート制御・リトライ・トークン更新が行われます。大量のリクエストを短時間に投げないようにしてください。
- save_* 関数は ON CONFLICT DO UPDATE による冪等保存を行います。

---

## ディレクトリ構成（主なファイル）

（パッケージは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境設定・自動 .env 読み込み
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（差分取得・品質チェック）
    - quality.py                — データ品質チェック
    - audit.py                  — 監査ログ用スキーマ（signal / order_request / executions）
  - strategy/
    - __init__.py               — 戦略層（拡張ポイント）
  - execution/
    - __init__.py               — 発注実行層（拡張ポイント）
  - monitoring/
    - __init__.py               — 監視・アラート（拡張ポイント）

---

## 重要な設計・運用上の注意

- レート制限とリトライ
  - J-Quants API のレート制限を守るため、内部で 120 req/min を想定した固定インターバルのスロットリングを実装しています。
  - 408/429/5xx に対するリトライ（最大 3 回、指数バックオフ）を実装しています。
  - 401 はトークン期限切れとみなしトークンを自動リフレッシュして 1 回リトライします。

- トレーサビリティ
  - 監査ログは UUID ベースの階層（strategy_id → signal_id → order_request_id → broker_order_id）で紐づきます。
  - order_request_id は冪等キーとして機能するので、再送時の二重発注防止に利用してください。

- データ整合性
  - save_* 関数は ON CONFLICT DO UPDATE を用いて重複を回避し、fetched_at を記録して「いつデータを取得したか」をトレースできます。
  - ETL はバックフィルを行い API の後出し修正を吸収する設計です（デフォルト backfill_days=3）。

---

## 拡張・開発

- strategy / execution / monitoring パッケージは拡張ポイントです。実際の戦略ロジックやブローカ接続（kabuステーション等）はここに実装してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑制できます。

---

もし README に追記したい使用例（cron ジョブ、Dockerfile、CI 設定）や、外部サービス（Slack 通知、kabu API 連携）に関する記載が必要であれば教えてください。README をその要件に合わせて拡張します。