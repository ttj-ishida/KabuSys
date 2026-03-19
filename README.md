# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API からマーケットデータ・財務データを取得して加工し、特徴量生成・シグナル生成・発注層へ繋ぐためのユーティリティを提供します。

---

## 主要な特徴（概要）

- データ収集（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーの取得・保存（ページネーション・リトライ・トークン自動更新対応）
- DuckDB スキーマの定義と初期化（冪等な DDL）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 特徴量エンジニアリング（research で算出された生ファクターの正規化・フィルタ・保存）
- シグナル生成（特徴量＋AIスコア統合による BUY/SELL シグナル生成、エグジット判定）
- ニュース収集（RSS 取得、記事の正規化・DB 保存・銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev／範囲取得）
- 発注・監査向けの DB スキーマ（signal / order / execution / positions 等）

---

## 機能一覧（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルートを探索）および環境変数管理
- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン管理）
  - schema: DuckDB のスキーマ定義と init_schema / get_connection
  - pipeline: run_daily_etl / 個別 ETL ジョブ（run_prices_etl 等）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄紐付け
  - calendar_management: market_calendar の更新、営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary 等
- kabusys.strategy
  - feature_engineering.build_features: features テーブル生成（正規化・ユニバースフィルタ）
  - signal_generator.generate_signals: features/ai_scores を元に BUY/SELL シグナル生成
- kabusys.execution / kabusys.monitoring
  - 発注・監視関連のインターフェース（スケルトン）

---

## 必要条件

- Python 3.10+
  - （コード中の型ヒントや union 型 `X | Y` を利用しているため）
- 主な依存ライブラリ
  - duckdb
  - defusedxml
  - （標準ライブラリの urllib などを使用）
- J-Quants API の利用にはリフレッシュトークンが必要

※ 要件を管理した requirements ファイルがプロジェクトにある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 開発中なら editable install:
     - python -m pip install -e .
   - もしくは通常インストール／依存のインストール:
     - python -m pip install duckdb defusedxml
     - （プロジェクトの requirements.txt があれば pip install -r requirements.txt）

2. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 読み込み優先度: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

3. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabu ステーション API パスワード（必須、発注関連を使う場合）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須、通知連携を使う場合）
   - SLACK_CHANNEL_ID — Slack チャネル ID（必須、通知連携を使う場合）
   - 任意 / 既定:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト `INFO`
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`

4. データベース初期化
   - Python REPL / スクリプト内で DuckDB ファイルを初期化します:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - メモリDB を使う場合は `":memory:"` を指定できます。

---

## 使い方（主要ユースケース）

以下は代表的な使い方です。実行はアプリケーションやバッチジョブから呼び出します。

1) DuckDB スキーマ初期化
- 例:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
- 例:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定可能
  - print(result.to_dict())

3) 特徴量の構築（features テーブル生成）
- 例:
  - from datetime import date
  - from kabusys.strategy import build_features
  - n = build_features(conn, date(2025, 1, 31))
  - print(f"{n} 銘柄の特徴量を upsert しました")

4) シグナル生成（features と ai_scores を統合して signals テーブルへ）
- 例:
  - from kabusys.strategy import generate_signals
  - count = generate_signals(conn, date(2025, 1, 31), threshold=0.6)
  - print(f"{count} 件のシグナルを書き込みました")

5) ニュース収集（RSS 取得→raw_news 保存→銘柄紐付け）
- 例:
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  - print(results)

6) カレンダー更新（夜間バッチ）
- 例:
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print(f"market_calendar に保存: {saved}")

7) 直接 J-Quants データを取得する
- fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - raws = fetch_daily_quotes(date_from=..., date_to=...)
  - save_daily_quotes(conn, raws)

---

## 環境変数の詳細

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` と `.env.local` を読み込みます。
  - 上書きルール: OS 環境 > .env.local > .env
  - テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 必須キー（使用箇所に応じて必要）
  - JQUANTS_REFRESH_TOKEN: jquants_client.get_id_token() に使用されます
  - KABU_API_PASSWORD: kabu ステーション連携に必要
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用

- 設定値の取得例（コード内）
  - from kabusys.config import settings
  - settings.jquants_refresh_token
  - settings.duckdb_path  (Path オブジェクト)
  - settings.env / settings.log_level

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save 関数）
  - news_collector.py — RSS 収集・保存・銘柄抽出
  - schema.py — DuckDB スキーマ / init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — market_calendar 管理（営業日判定等）
  - features.py — zscore_normalize の再エクスポート
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログ用スキーマ定義
- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py — build_features
  - signal_generator.py — generate_signals
- execution/
  - __init__.py  （発注層の実装用プレースホルダ）
- monitoring/
  - （監視／メトリクス用のプレースホルダ）

プロジェクトルート
- .env / .env.local（任意、設定）
- pyproject.toml / setup.cfg（パッケージ設定がある場合）
- data/（デフォルトのデータファイル保存先、duckdb ファイル等を置く）

---

## 開発・テストのヒント

- テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして環境依存を切ると良いです。
- DuckDB のインメモリモード (`":memory:"`) を使えば副作用のない単体テストが書きやすいです。
- jquants_client の HTTP 呼び出し部分はモック可能に設計されているため、ネットワーク依存テストを避けられます。
- news_collector._urlopen などはテストで差し替え可能（外部アクセスのモックに活用できます）。

---

## 参考・補足

- 戦略・データ設計（StrategyModel.md / DataPlatform.md / DataSchema.md 等）がコードにコメントで示されています。実運用や拡張の際はこれらの設計方針に従って実装を行ってください。
- 本リポジトリは発注 API や実口座での運用を想定するため、KABUSYS_ENV によるモード切替（development / paper_trading / live）やログレベル管理が用意されています。実運用前に十分なテストとリスク管理・監査ログの確認を行ってください。

---

必要であれば README にサンプル .env.example、実行例スクリプト、CI 用の簡易構成、さらに詳細な API ドキュメント（各関数の引数・戻り値例）を追加できます。どの情報を優先して追記しますか？