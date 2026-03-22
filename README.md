# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、データ加工（DuckDB スキーマ・ETL）、リサーチ（ファクター計算・探索）、戦略（特徴量作成・シグナル生成）、バックテスト、ニュース収集などの機能をモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーを持つシステム設計を前提としています。

- Raw Layer: API から取得した生データ（株価、財務、ニュース等）
- Processed Layer: 整形済み市場データ（prices_daily / fundamentals 等）
- Feature Layer: 戦略 / AI 用の特徴量（features / ai_scores 等）
- Execution Layer: シグナル -> 注文 -> 約定 -> ポジション管理

設計の要点:
- DuckDB を DB エンジンとして採用（オンディスク / インメモリ両対応）
- J-Quants API からの取得はレートリミット・リトライ・トークン自動更新に対応
- リサーチ関係関数はルックアヘッドバイアス対策を実施（target_date 時点のデータのみを使用）
- 多くの操作は冪等（idempotent）に設計（ON CONFLICT、日付単位の置換等）

---

## 主な機能一覧

- data/
  - J-Quants API クライアント（取得・保存）: prices, financials, market calendar
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - schema: DuckDB スキーマの初期化（init_schema）
  - stats: 汎用統計ユーティリティ（Z スコア正規化等）
  - pipeline: 差分 ETL のラッパー（差分取得・保存・品質チェック）
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリー
- strategy/
  - feature_engineering: 生ファクターを正規化・合成して features テーブルに保存
  - signal_generator: features と ai_scores を統合して BUY / SELL シグナル生成
- backtest/
  - engine: run_backtest（DB をコピーして日次ループでシミュレーション）
  - simulator: 擬似約定・ポートフォリオ管理（スリッページ・手数料適用）
  - metrics: バックテスト評価指標の計算（CAGR, Sharpe, MaxDD 等）
  - CLI: python -m kabusys.backtest.run によるバッチ実行
- execution/, monitoring/（将来的に実装する発注・監視系）

---

## セットアップ手順

前提:
- Python 3.9+（typing の | 変形等が使われているため 3.10 を推奨）
- system-level に DuckDB を入れずとも Python パッケージとしてインストール可能

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   - 例:
     - git clone ...
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -U pip
     - pip install -e .

   必要パッケージ（代表例）:
   - duckdb
   - defusedxml
   - （標準ライブラリで実装されている部分が多いですが、上記を少なくとも導入してください）

2. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - オプション（デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()
   - インメモリでの初期化:
     - init_schema(":memory:")

---

## 使い方（主なユースケース）

以下は代表的な操作例です。実行時は適切に logging を設定してください。

- DuckDB 接続 / スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- J-Quants からデータ取得と保存
  - from kabusys.data import jquants_client as jq
  - id_token = jq.get_id_token()  # settings.jquants_refresh_token を使う
  - records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  - jq.save_daily_quotes(conn, records)

- ニュース収集
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes=known_code_set)

- 特徴量構築（features テーブルへ保存）
  - from datetime import date
  - from kabusys.strategy import build_features
  - upsert_count = build_features(conn, target_date=date(2024, 1, 31))

- シグナル生成
  - from kabusys.strategy import generate_signals
  - n_signals = generate_signals(conn, target_date=date(2024, 1, 31))

- バックテスト（Python API）
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  - result.history / result.trades / result.metrics を参照

- バックテスト（CLI）
  - 例:
    - python -m kabusys.backtest.run \
        --start 2023-01-01 --end 2024-12-31 \
        --cash 10000000 --db data/kabusys.duckdb

  run.py に CLI の詳細オプションが記載されています（--slippage, --commission, --max-position-pct 等）。

- ETL パイプライン（差分取得）
  - data.pipeline モジュールが差分取得・保存のヘルパーを提供します（run_prices_etl など）。
  - 実運用では ETL ジョブを cron / Airflow / Prefect 等で定期実行します。

注意点:
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取ります。
- run_backtest() は本番 DB から必要なテーブルをインメモリ DB にコピーして実行するため、本番テーブルを汚しません。
- feature / signal の計算は target_date 時点のデータのみを使うことでルックアヘッドバイアスを低減しています。

---

## 重要な設計上の挙動

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
  - OS 環境変数が優先され、.env.local は上書きとして読み込まれます。
  - テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- 冪等性:
  - jquants_client の save_* 関数や news_collector の保存処理は ON CONFLICT / DO NOTHING / DO UPDATE により冪等に設計されています。

- レートリミット / リトライ:
  - J-Quants クライアントは 120 req/min の固定スロットリングと、408/429/5xx に対する指数バックオフ・リトライを実装しています。401 はトークン自動リフレッシュを行います。

---

## ディレクトリ構成（主要ファイル）

（パッケージルートが `src/kabusys` の想定）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + 保存
    - news_collector.py            — RSS ニュース収集・DB 保存・銘柄抽出
    - pipeline.py                  — ETL 差分更新ラッパー
    - schema.py                    — DuckDB スキーマ定義・init_schema()
    - stats.py                     — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py           — momentum / volatility / value
    - feature_exploration.py       — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — build_features()
    - signal_generator.py          — generate_signals()
  - backtest/
    - __init__.py
    - engine.py                    — run_backtest()
    - simulator.py                 — PortfolioSimulator, 実約定ロジック（擬似）
    - metrics.py                   — バックテスト評価指標
    - clock.py
    - run.py                       — CLI エントリポイント
  - execution/                      — 発注関連（空ファイル/将来実装）
  - monitoring/                     — 監視系（将来実装）
  - research/                       — 研究用ユーティリティ群（上記参照）

---

## 例: 簡単なワークフロー

1. スキーマ初期化
   - from kabusys.data.schema import init_schema
   - conn = init_schema("data/kabusys.duckdb")

2. prices を J-Quants から取得して保存
   - from kabusys.data import jquants_client as jq
   - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
   - jq.save_daily_quotes(conn, records)

3. ファクター計算 -> features 生成
   - from kabusys.strategy import build_features
   - build_features(conn, target_date=...)

4. シグナル生成
   - from kabusys.strategy import generate_signals
   - generate_signals(conn, target_date=...)

5. バックテスト（CLI/API）で戦略評価

---

## 開発・貢献

- コード品質:
  - 多くの関数はロギングを行います。デバッグ時は LOG_LEVEL を DEBUG に設定してください。
- テスト:
  - 各モジュールは外部依存を最小化する設計です（API 呼び出しの注入や HTTP レスポンスのモックが可能）。
- 依存パッケージは requirements.txt / pyproject.toml に合わせて導入してください（本 README は主要な依存のみ列挙しています）。

---

もし README に追加したい具体的な例（実行コマンド、.env.example、docker-compose 例など）があれば教えてください。必要に応じてセクションを追記します。