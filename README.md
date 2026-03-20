# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォームの Python ライブラリです。  
J-Quants からのデータ取得、DuckDB によるデータ格納・加工、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの機能を備えたモジュール群を提供します。

- 現状バージョン: 0.1.0

---

## 概要

KabuSys は次の目的で設計されています。

- J-Quants API から株価・財務・カレンダー等を安全に取得（レート制限・自動リトライ・トークンリフレッシュ対応）
- DuckDB を用いたローカルデータベース（Raw / Processed / Feature / Execution レイヤ）管理とスキーマ初期化
- 研究（research）で得た生ファクターを用いた特徴量生成・正規化
- 正規化済み特徴量＋AIスコアを用いた売買シグナル生成（BUY / SELL）
- RSS からのニュース収集と記事→銘柄紐付け（SSRF 対策・トラッキング除去）
- マーケットカレンダー管理・営業日判定
- ETL パイプライン（差分取得・品質チェック）
- 監査ログ（signal → order → execution のトレース保存）

設計上のポイント:
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全）
- ルックアヘッドバイアス対策（target_date 時点のデータのみ使用）
- 外部依存を限定（標準ライブラリ＋ minimal な依存で動作）
- セキュリティ考慮（SSRF 対策、XML の defusedxml 利用など）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、トークン自動リフレッシュ、レート制限、保存ユーティリティ）
  - pipeline: 差分 ETL（prices / financials / market calendar）と日次パイプライン
  - schema: DuckDB スキーマ作成・接続ユーティリティ
  - news_collector: RSS フィード取得・記事前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリー等の分析ツール
- strategy/
  - feature_engineering: raw ファクターを統合・正規化して features テーブルへ保存
  - signal_generator: features + ai_scores から final_score を計算し signals を生成
- audit / execution / monitoring: 監査ログ・発注/約定管理（スキーマ定義を含む）
- config: .env / 環境変数読み込み、アプリ設定（必須トークンなど）
- news_collector の SSRF 対策、J-Quants クライアントのレートリミット等、運用上の安全機構を多数実装

---

## 必要条件 (主な依存)

- Python 3.9+
- duckdb
- defusedxml

（上記以外に標準ライブラリを多用。将来的に追加依存がある場合は pyproject.toml 等に記載します）

---

## セットアップ手順

1. リポジトリをクローン

   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作る（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. インストール

   pip install -U pip
   pip install -e .            # 開発インストール（プロジェクトルートに pyproject.toml/setup がある前提）
   pip install duckdb defusedxml

4. 環境変数 / .env の準備

   プロジェクトルート（.git または pyproject.toml を基準）に `.env` または `.env.local` を配置すると自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（execution 層使用時）
   - SLACK_BOT_TOKEN       : Slack 通知（有効化している場合）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG/INFO/...)
   - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動読み込み無効化)
   - KABUSYS_API_BASE_URL 等（必要に応じて）

   DB パス（デフォルト値）:
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)

   .env の記法は shell 互換（export KEY=val / KEY="val" 等）に対応しています。

5. データベース初期化

   以下のサンプルで DuckDB のスキーマを作成します（デフォルトでは data/kabusys.duckdb に作成）。

   Python REPL またはスクリプト:

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)

   init_schema は既存テーブルがあればスキップするため安全に何度でも実行できます。

---

## 使い方（代表的な例）

- 日次 ETL を実行（J-Quants から差分取得して保存・品質チェック）

  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date 引数で任意日を指定可能
  print(result.to_dict())

- 特徴量の作成（research のファクターを統合して features テーブルへ保存）

  from datetime import date
  from kabusys.strategy import build_features
  build_count = build_features(conn, date.today())
  print(f"features upserted: {build_count}")

- シグナル生成

  from kabusys.strategy import generate_signals
  signals_count = generate_signals(conn, date.today(), threshold=0.6)
  print(f"signals written: {signals_count}")

- ニュース収集（RSS）と DB 保存

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", ...}  # 既知銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- マーケットカレンダーの夜間更新ジョブ

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar entries saved: {saved}")

- J-Quants から生データを直接取得して保存する例

  from kabusys.data import jquants_client as jq
  rows = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, rows)

注意:
- すべての ETL / 保存処理は冪等性を意識して実装されています（ON CONFLICT / トランザクション）。
- production では KABUSYS_ENV を適切に設定し、ログ・監視・Slack 通知等を組み合わせて運用してください。

---

## 設計・運用の注記（重要な実装ポイント）

- 認証と再試行:
  - J-Quants クライアントはトークンの自動リフレッシュ（401 発生時）を行い、HTTP エラー（408/429/5xx）に対して指数バックオフでリトライします。
  - API レートは 120 req/min を守るためスロットリングを導入しています。

- セキュリティ:
  - RSS 取得時は URL 正規化、トラッキングパラメータ除去、SSRF 対策（リダイレクト先検査・プライベートホスト拒否）、XML の defusedxml を利用しています。
  - .env の読み込みはプロジェクトルート検出（.git または pyproject.toml）を基準に行い、CWD に依存しません。

- データ品質:
  - pipeline.run_daily_etl は品質チェックを実行可能（quality モジュール）。品質問題が見つかっても ETL を止めずに問題を報告する方針です。

- ルックアヘッドバイアス対策:
  - feature_engineering / signal_generator / research の各処理は target_date 時点の利用可能データのみを参照するよう設計されています。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 取得・前処理・DB保存
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - stats.py               — zscore_normalize 等
    - features.py            — data.stats の再エクスポート
    - audit.py               — 監査ログ用スキーマ（signal / order / execution ログ）
    - (その他: execution, monitoring など)
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility 計算
    - feature_exploration.py — forward returns / IC / summary utilities
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成
    - signal_generator.py    — signals 作成
  - execution/                — 発注 / 約定関連（初期サブパッケージ）
  - monitoring/               — 監視・メトリクス関連（サブパッケージ）

上記のうち多くは DuckDB の `raw_*` / `prices_daily` / `features` / `signals` 等のテーブルに依存しています。schema.init_schema で必要テーブルはすべて作成されます。

---

## 開発・テスト

- 自動環境変数ロードを無効化したい場合:

  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- テストやローカル検証では DuckDB のインメモリモードが利用可能:

  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")

- テスト用に jquants_client._request や news_collector._urlopen などをモックして外部通信を切ることが想定されています。

---

## 最後に

この README はコードベース（src/kabusys/）の現行実装を元にまとめています。実運用前に必ず以下を確認してください:

- J-Quants / 証券会社 API の認証情報と権限
- 実際の注文フロー（execution 層）の安全性（最大発注量・レート制限・リスク管理）
- 運用監視とロギング設定

不明点や追加のサンプル（例: CI 用スクリプト、運用 runbook、.env.example の作成）が必要であれば教えてください。README を拡張して提供します。