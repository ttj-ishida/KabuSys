# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。J-Quants などの外部データソースからデータを収集・保存し、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログなど ETL と運用に必要な機能群を提供します。

---

## 概要

このプロジェクトは以下を目的としたモジュール群を含みます。

- J-Quants API からの株価・財務・カレンダー等の取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いた 3 層データレイヤ（Raw / Processed / Feature）と実行（Execution）・監査（Audit）スキーマの管理
- RSS ベースのニュース収集と記事 — 銘柄紐付け処理（SSRF 対策、サイズ制限、トラッキングパラメータ除去等）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日検索）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（シグナル → 発注 → 約定 のトレース可能なスキーマ）

設計上の特徴として、API レート制御、指数バックオフを伴う再試行、取得日時（fetched_at）による Look‑ahead Bias の防止、DuckDB での冪等保存（ON CONFLICT）などが組み込まれています。

---

## 主な機能一覧

- data.jquants_client
  - 株価日足（OHLCV）、財務（四半期）、JPX カレンダーの取得
  - レート制限（120 req/min）制御、リトライ（408/429/5xx）、401 時のトークン自動更新
  - DuckDB への冪等保存（save_*** 系関数）
- data.news_collector
  - RSS から記事を収集し raw_news に保存
  - URL 正規化・トラッキング除去・記事 ID（SHA-256）による冪等性
  - SSRF 対策、レスポンスサイズ制限（既定 10MB）、gzip 解凍対応
  - 銘柄コード抽出と news_symbols への紐付け
- data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution）
  - init_schema による初期化（冪等）
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェックの順で処理
  - 差分更新、backfill、品質チェックの統合
- data.calendar_management
  - カレンダーの夜間更新ジョブ、営業日/前後営業日判定、期間の営業日取得
- data.quality
  - 欠損 / スパイク / 重複 / 日付不整合 のチェック（QualityIssue を返す）
- data.audit
  - 監査用スキーマ（signal_events / order_requests / executions）の初期化とインデックス
- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数アクセスラッパー
  - 環境（development / paper_trading / live）判定、ログレベル検証

---

## 必要な環境変数

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境（"development" / "paper_trading" / "live"、デフォルト "development"）
- LOG_LEVEL — ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL", デフォルト "INFO"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには "1" を設定
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

備考:
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に `.env` → `.env.local` の順で行い、OS 環境変数は保護されます。
- .env.example を参考に .env を用意してください（config._require が未設定時は ValueError を投げます）。

---

## セットアップ手順

以下は一般的な Python 環境での手順例です。

1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 基本的に必要なのは duckdb と defusedxml（その他標準ライブラリを使用）
   - 例:
     pip install duckdb defusedxml

   （本リポジトリに requirements.txt がある場合はそれを使用してください:
     pip install -r requirements.txt）

3. 環境変数を設定
   - プロジェクトルートに `.env` を置くか、OS 環境変数で設定します。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789

4. データベース初期化
   - Python REPL またはスクリプトから DuckDB スキーマを初期化します。例:

     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

   - 監査ログスキーマを追加する場合:

     from kabusys.data import audit
     audit.init_audit_schema(conn)

---

## 使い方（簡単な例）

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックをまとめて実施）:

  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブ:

  from kabusys.data import schema, news_collector
  conn = schema.init_schema("data/kabusys.duckdb")

  # 既知の銘柄コードセットを渡して紐付けを行う
  known_codes = {"7203", "6758", "9984"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)

- J-Quants の ID トークン取得（手動例）:

  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用して自動取得

- DuckDB 接続の取得（既存 DB に接続）:

  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")

注意点:
- jquants_client は内部でレートリミッタ／リトライを実装しています。大量リクエスト時でも API 制限を守る設計です。
- save_* 関数は冪等性（ON CONFLICT）を考慮しており、同一データを複数回保存しても重複されません。

---

## ディレクトリ構成

（主要なファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境設定・.env 自動読み込み
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント、保存処理
      - news_collector.py      — RSS ニュース収集と保存／銘柄抽出
      - schema.py              — DuckDB スキーマ定義 / init_schema
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py — カレンダー更新／営業日ユーティリティ
      - audit.py               — 監査スキーマ初期化
      - quality.py             — データ品質チェック
    - strategy/
      - __init__.py            — 戦略層（拡張ポイント）
    - execution/
      - __init__.py            — 発注/執行処理（拡張ポイント）
    - monitoring/
      - __init__.py            — 監視・メトリクス（拡張ポイント）

---

## 開発・運用上の注意

- 環境変数の自動ロード
  - config.py はプロジェクトルートを探して `.env` → `.env.local` を自動で読み込みます。
  - テストや CI で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- データの整合性／品質
  - pipeline.run_daily_etl は品質チェックをオプションで実行します。品質チェックで重大な問題が見つかった場合の対処（ETL 停止／通知）は利用者側で行ってください（Fail‑Fast にはしていません）。

- セキュリティ
  - news_collector は SSRF 対策、XML パースに defusedxml を利用、レスポンスサイズ制限や gzip 解凍後サイズ検査など複数の防御を実装しています。

- ログとモード
  - KABUSYS_ENV により is_live / is_paper / is_dev 切替が可能です。ログレベルは LOG_LEVEL で制御します。

---

## 今後の拡張ポイント（例）

- strategy パッケージに具体的戦略（シグナル生成）を実装
- execution パッケージにブローカー連携（kabu ステーション API）実装
- monitoring に Prometheus 等のメトリクス公開実装
- CI 環境向けのテストスイート・モック（API/HTTP/DB）整備

---

必要であれば README の英語版や、各モジュールの API リファレンス（関数一覧・引数詳細・例）も作成します。どの追加項目が必要か教えてください。