# KabuSys

日本株向け自動売買基盤（軽量プロトタイプ）

KabuSys は J‑Quants / kabuステーション 等のデータ・ブローカーを想定した
日本株向けデータプラットフォーム＋戦略モジュール群です。
データ取得（ETL）→特徴量生成→シグナル生成→発注・監査の各層を分離して設計しており、
DuckDB をバックエンドにしてオフライン解析（research）と本番実行を同一コードベースで扱えます。

主な設計方針：
- DuckDB を用いたローカル DB（ファイル）中心のデータ管理
- ETL / 保存は冪等（ON CONFLICT / トランザクション）で安全に実行
- ルックアヘッドバイアス対策（常に target_date 時点の情報のみ使用）
- 外部依存を最小限にし、テスト容易性を重視

---

## 機能一覧

- データ取得・保存
  - J‑Quants API クライアント（株価、財務、マーケットカレンダー）
  - RSS ベースのニュース収集（前処理・記事ID正規化・銘柄紐付け）
  - 差分 ETL / 日次 ETL ジョブ（run_daily_etl）
- データベーススキーマ管理
  - DuckDB 用スキーマ定義と初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル設計
- 特徴量・研究ツール
  - ファクター計算（momentum / volatility / value）
  - クロスセクション Z スコア正規化ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 戦略
  - 特徴量合成（build_features）
  - シグナル生成（generate_signals） — BUY / SELL の判定ロジック実装
- カレンダー管理
  - JPX カレンダーの更新・営業日判定・前後営業日の取得など
- 監査・トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル定義
- ユーティリティ
  - 環境変数・設定管理（settings）
  - ロギング・レートリミッタ・リトライロジック等

---

## 前提条件 / 必要な環境変数

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする場合に `1` を設定
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_* などの追加設定は config.Settings を参照

.env の自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索し、
  OS 環境変数 > .env.local > .env の順で読み込みます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順

- リポジトリをクローンして、editable インストール（開発時）：
  - pip を利用する場合:
    - pip install -e .
  - あるいは pyproject.toml / setup に従って通常インストールしてください。

- 必要パッケージ（例: duckdb, defusedxml など）をインストールしてください。
  - requirements / pyproject に記載されている依存関係を利用します。

- .env を作成して必要な環境変数を設定します（上記参照）。

- DuckDB スキーマ初期化:
  - デフォルトの DB パスを使うか、任意のパスで初期化します。

  例:
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（よく使う操作例）

以下はインタラクティブやバッチでの呼び出し例です（Python スクリプトや cron/airflow から利用可）。

1) DuckDB スキーマ作成 / 接続
- 初期化（存在しない場合は parent ディレクトリも作成）:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 既存 DB に接続（初回は init_schema を推奨）:
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

2) 日次 ETL（株価・財務・カレンダーの差分取得）
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると今日で実行
  print(result.to_dict())

3) 特徴量構築（build_features）
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, date(2025, 1, 10))
  print(f"upserted features: {n}")

4) シグナル生成（generate_signals）
  from kabusys.strategy import generate_signals
  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2025, 1, 10))
  print(f"signals generated: {total}")

5) ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  conn = get_connection("data/kabusys.duckdb")
  # known_codes: 抽出に使用する銘柄コードセット（省略可）
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)

6) カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

7) J‑Quants の直接呼び出し（必要に応じて id_token を注入）
  from kabusys.data import jquants_client as jq
  # fetch_daily_quotes, fetch_financial_statements, save_* の組み合わせで利用

注意:
- run_daily_etl 等は内部で try/except によりステップ単位で失敗を切り分けます。戻り値（ETLResult）を確認して問題（quality_issues / errors）を把握してください。
- generate_signals, build_features は DuckDB 接続を直接受け取るため、本番では ETL → features → signals の順でスケジューリングしてください。

---

## 設計上のポイント / 実装メモ

- 冪等性:
  - DB 保存は ON CONFLICT / INSERT ... DO UPDATE / トランザクションで実装されており、
    同じデータを複数回投入しても重複や不整合を起こさないよう設計されています。

- ルックアヘッドバイアス対策:
  - 戦略系（feature_engineering / signal_generator / research）は target_date 時点のデータのみを参照します。
  - データ取得時は fetched_at を記録し、「いつデータを得られたか」をトレースできます。

- リトライ・レート制御:
  - J‑Quants クライアントは固定間隔スロットリング（120 req/min）と指数バックオフを実装。
  - 401 でトークンリフレッシュ、408/429/5xx は再試行対象です。

- セキュリティ配慮（ニュース収集）:
  - RSS フィードはスキーム検証、プライベートIP へのアクセスブロック（SSRF 対策）、
    最大受信サイズの制限、defusedxml による安全な XML パースなどの対策を実装しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン）
  - config.py — 環境変数/設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（fetch/save）
    - news_collector.py — RSS 収集・前処理・DB 保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義・初期化（init_schema / get_connection）
    - pipeline.py — ETL パイプライン（run_prices_etl, run_financials_etl, run_daily_etl）
    - stats.py — Z スコア等の統計ユーティリティ
    - features.py — data.stats のエクスポート
    - calendar_management.py — market_calendar 管理・営業日判定・calendar_update_job
    - audit.py — 監査ログ用 DDL（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターの合成・正規化 → features テーブルへ
    - signal_generator.py — final_score 計算と BUY/SELL シグナル生成 → signals テーブルへ
  - execution/ — 発注関連のモジュール（プレースホルダ／別実装想定）
  - monitoring/ — 監視・メトリクス（プレースホルダ）

（上記は公開されている主要モジュールの抜粋です。実際のリポジトリに他のファイルやドキュメントが存在する場合があります。）

---

## 開発・拡張のヒント

- テスト:
  - settings 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できるため、ユニットテストでは環境を固定して実行できます。
  - jquants_client._urlopen / news_collector._urlopen などをモックしてネットワーク依存を切り離せます。

- 本番運用:
  - KABUSYS_ENV を `paper_trading` / `live` に切り替えて動作モードを分離してください。
  - ETL やカレンダージョブは定期ジョブ（cron / Airflow）で運用し、run_daily_etl の戻り値を監視してアラートを出すと良いです。

---

必要に応じて README に含めたい追加情報（例: .env.example の完全な雛形、CLI ラッパー、運用手順や監視ルールなど）があれば教えてください。README を拡張して具体的な運用例やデプロイ手順も追加できます。