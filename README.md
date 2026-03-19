# KabuSys

日本株向け自動売買基盤（KabuSys）の簡易リポジトリ説明書です。  
この README はコードベース（src/kabusys 以下）を元に、導入・基本的な使い方・ディレクトリ構成などを日本語でまとめたものです。

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ管理（DuckDB）、研究（ファクター計算／特徴量探索）、戦略（特徴量→シグナル生成）、ニュース収集（RSS）および発注/監査に向けた土台を提供するライブラリ群です。  
設計上のポイント：

- DuckDB をデータストアとして使用し、Raw / Processed / Feature / Execution の層でデータを管理
- J-Quants API からの差分取得（レート制御・リトライ・トークン自動更新を実装）
- 研究モジュールはルックアヘッドバイアスを防止する設計（target_date 時点のデータのみ使用）
- 冪等（idempotent）な DB 保存、トランザクション利用による日付単位の置換
- ニュース収集は SSRF 対策、XML の安全パース、トラッキングパラメータ除去等を実装

## 機能一覧

主要な機能（モジュール別）

- konfig / 環境変数管理
  - 環境変数の自動ロード (.env / .env.local)、必須設定の検査（settings オブジェクト）
- data/jquants_client
  - J-Quants API クライアント（トークン管理、ページネーション、リトライ、レート制御）
  - fetch/save: 日足、財務諸表、マーケットカレンダーなど
- data/schema
  - DuckDB のスキーマ定義（Raw, Processed, Feature, Execution 層）と初期化関数
- data/pipeline
  - 日次 ETL（run_daily_etl）: カレンダー→株価→財務→品質チェックの一括実行
  - 差分取得（バックフィル）、品質チェック連携
- data/news_collector
  - RSS 取得（fetch_rss）、前処理、raw_news テーブルへの冪等保存、銘柄抽出
- data/calendar_management
  - market_calendar の管理、営業日判定、next/prev_trading_day、calendar_update_job
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（forward returns, IC, summary）
- strategy
  - build_features(conn, target_date): raw ファクターを統合・正規化して features テーブルへ保存
  - generate_signals(conn, target_date, ...): features + ai_scores を用いて BUY/SELL シグナルを生成して signals テーブルへ保存
- data/stats
  - zscore_normalize: クロスセクション Z スコア正規化ユーティリティ
- audit（監査用 DDL など）
  - signal_events / order_requests / executions 等の監査テーブル定義

## セットアップ手順

前提

- Python 3.10 以上（型注釈で | 演算子を使用）
- DuckDB（Python パッケージとして duckdb）
- defusedxml（RSS パースの安全化）
- ネットワークアクセス（J-Quants API 等）および適切な API トークン

推奨手順（ローカル開発用）

1. リポジトリをクローンし、仮想環境を作成・有効化

   bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール（最小限の例）

   bash
   pip install duckdb defusedxml

   補足: 実運用ではログ・HTTP ライブラリなど追加依存がある場合は requirements.txt を用意してください。

3. 環境変数の準備

   プロジェクトルートに `.env`（または `.env.local`）を作成します。自動ロードは `kabusys.config` により、プロジェクトルートが .git または pyproject.toml を基準に探索されます。

   必須環境変数（コード内で _require() されるもの）：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意・デフォルト値あり：
   - KABUSYS_ENV (development|paper_trading|live) — デフォルト `development`
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化

   DB パス：
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）

4. DuckDB スキーマ初期化

   Python REPL やスクリプトで:

   python
   >>> from kabusys.data.schema import init_schema
   >>> conn = init_schema("data/kabusys.duckdb")

   上記で必要なテーブルとインデックスが作成されます。

## 使い方（主要な操作例）

以下はライブラリの主要エントリポイントを使った最小実例です。実環境では適切なログ設定・例外処理・監視を追加してください。

- 日次 ETL 実行（市場カレンダー、株価、財務を差分取得）

  python
  >>> from kabusys.data.schema import init_schema
  >>> from kabusys.data.pipeline import run_daily_etl
  >>> conn = init_schema("data/kabusys.duckdb")
  >>> result = run_daily_etl(conn)  # target_date を指定可能
  >>> print(result.to_dict())

- 特徴量の作成（research のファクターを統合して features テーブルに保存）

  python
  >>> from datetime import date
  >>> from kabusys.strategy import build_features
  >>> conn = init_schema("data/kabusys.duckdb")
  >>> n = build_features(conn, date(2025, 1, 15))
  >>> print(f"upserted features: {n}")

- シグナル生成

  python
  >>> from datetime import date
  >>> from kabusys.strategy import generate_signals
  >>> conn = init_schema("data/kabusys.duckdb")
  >>> total = generate_signals(conn, date(2025, 1, 15))
  >>> print(f"signals generated: {total}")

  generate_signals は weights、threshold を引数で上書き可能です。

- RSS ニュース収集と保存

  python
  >>> from kabusys.data.news_collector import run_news_collection
  >>> conn = init_schema("data/kabusys.duckdb")
  >>> known_codes = {"7203", "6758"}  # 有効銘柄コードセット（オプション）
  >>> results = run_news_collection(conn, known_codes=known_codes)
  >>> print(results)

- カレンダー更新バッチ

  python
  >>> from kabusys.data.calendar_management import calendar_update_job
  >>> conn = init_schema("data/kabusys.duckdb")
  >>> saved = calendar_update_job(conn)
  >>> print(f"saved calendar records: {saved}")

- スキーマのみ取得済みの既存 DB へ接続したい場合

  python
  >>> from kabusys.data.schema import get_connection
  >>> conn = get_connection("data/kabusys.duckdb")

## 設定（環境変数のキー）

主な環境変数

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用途）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development|paper_trading|live）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（任意）

注意: config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。テスト時等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ディレクトリ構成

リポジトリの主要なファイル/ディレクトリ（src/kabusys 配下）

- kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save 等）
    - schema.py                  — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                — ETL パイプライン / run_daily_etl 等
    - news_collector.py          — RSS 取得・正規化・保存
    - calendar_management.py     — market_calendar 管理・営業日ロジック
    - features.py                — zscore_normalize の公開再エクスポート
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査用テーブル定義（signal_events など）
    - (その他: quality.py 等、品質チェック関連が想定される)
  - research/
    - __init__.py
    - factor_research.py         — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py     — forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py     — build_features: 正規化・UPSERT
    - signal_generator.py        — generate_signals: final_score 計算・BUY/SELL 生成
  - execution/                   — 発注ロジック用のエントリ（空 / 拡張ポイント）
  - monitoring/                  — 監視・メトリクス（存在が宣言されているが詳細実装は別途）

注: 上記は現コードベースのファイルに基づく概略です。実装の詳細や追加のツール・ユーティリティは別途存在する可能性があります。

## 運用上の注意点

- secrets（API トークン等）は .env で管理し、リポジトリへ含めないこと。`.env.example` を用意して必要なキーをドキュメント化してください。
- J-Quants API のレート制限を守る（jquants_client 内で制御済みだが、大量取得の際は注意）。
- DuckDB へは冪等的な保存ロジック（ON CONFLICT / DO UPDATE）を多用しているため、部分的再実行が比較的安全です。ただしトランザクション失敗時はロールバックが行われるためログを必ず確認してください。
- research/strategy モジュールは「target_date 時点のデータのみ」を使う設計です。将来値へのアクセスに注意して実装してください（ルックアヘッドバイアス回避）。
- ニュース収集は外部 URL を扱うため SSRF や XML 攻撃対策（実装済み）を理解しておいてください。

---

この README はコード内容を要約したものであり、詳細仕様（StrategyModel.md、DataPlatform.md、Researchドキュメント等）が別途存在すると想定されます。実運用・開発の際はそれらの設計資料も参照してください。質問や追加でサンプルスクリプトが欲しい場合は教えてください。