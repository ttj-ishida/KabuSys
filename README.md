# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。データ収集（J-Quants）、ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、バックテスト（擬似約定・ポートフォリオシミュレータ）などの機能を含みます。

主に研究・バックテスト用途に設計されており、本番発注層（kabuステーション等）への依存を極力分離しています。

---

## 主な機能

- データ取得／保存
  - J-Quants API クライアント（株価・財務・マーケットカレンダー取得、レート制御・リトライ・トークン自動更新）
  - RSS によるニュース収集（SSRF対策・記事ID正規化・銘柄抽出）
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）

- データ処理（ETL）
  - 差分更新、バックフィル（後出し修正の吸収）
  - 品質チェック（欠損・スパイク・重複などを検出）

- 研究・特徴量
  - ファクター計算（モメンタム、ボラティリティ、バリュー、流動性等）
  - クロスセクションの Z スコア正規化、クリッピング
  - 特徴量（features）テーブルの構築（冪等処理）

- シグナル生成
  - features と ai_scores を統合して最終スコアを計算
  - Bear レジーム判定、BUY/SELL シグナル生成（冪等）

- バックテスト
  - インメモリ DuckDB に必要データをコピーして実行
  - 約定モデル（スリッページ・手数料）、ポートフォリオ管理（全量エグジット）、日次スナップショット記録
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）

---

## 要件（主要依存パッケージ）

- Python 3.10+
- duckdb
- defusedxml

（他は標準ライブラリ中心に実装されています。プロジェクト全体で追加の依存があれば pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／配置

   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）とインストール

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # またはパッケージ化されている場合:
   # pip install -e .

3. 環境変数 (.env) の用意

   プロジェクトルートに `.env`（と任意で `.env.local`）を置くことで自動的に読み込まれます。
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数例（必須箇所は README の「設定」参照）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live)
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

4. DuckDB スキーマ初期化

   Python REPL もしくはスクリプトから:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()

   ":memory:" を渡すとインメモリ DB を初期化します（テスト用）。

---

## 使い方

以下は代表的な操作例です。

- バックテスト（CLI）

  本プロジェクトにはバックテストのエントリポイントがあります。事前に DuckDB に必要テーブル（prices_daily / features / ai_scores / market_regime / market_calendar 等）が揃っている必要があります。

  実行例:

  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 \
    --slippage 0.001 \
    --commission 0.00055 \
    --max-position-pct 0.20 \
    --db data/kabusys.duckdb

  実行後、期間のバックテスト結果（CAGR, Sharpe, Max Drawdown 等）が出力されます。

- DuckDB スキーマ初期化（スクリプト内）

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- ETL（株価差分取得の例）

  from kabusys.data.pipeline import run_prices_etl, ETLResult
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  res = run_prices_etl(conn, target_date=date.today())
  if res.has_errors:
      print("ETL 中にエラーが発生しました:", res.errors)
  conn.close()

  （run_prices_etl は差分取得・保存を行い、取得数・保存数・品質問題・エラーを ETLResult として返します）

- 特徴量構築 / シグナル生成（Python API）

  from kabusys.strategy import build_features, generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  # features を構築
  build_features(conn, target_date=date(2024, 1, 4))
  # シグナル生成
  generate_signals(conn, target_date=date(2024, 1, 4))
  conn.close()

- ニュース収集ジョブ

  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # 有効な銘柄コードセット（任意）
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  conn.close()

- バックテストをプログラムから呼び出す

  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  # result.history / result.trades / result.metrics を利用
  conn.close()

---

## 環境変数（設定項目）

このライブラリは環境変数から設定を読み込みます。主なキー:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client が ID トークンを取得するために使用します。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（execution 層で使用）。

- KABU_API_BASE_URL  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須)  
  Slack 通知に使用（監視・アラート用）。

- DUCKDB_PATH  
  デフォルト DB パス（data/kabusys.duckdb）。

- SQLITE_PATH  
  監視用 SQLite DB（data/monitoring.db）。

- KABUSYS_ENV  
  実行環境: development / paper_trading / live（デフォルト: development）。

- LOG_LEVEL  
  例: INFO, DEBUG（デフォルト: INFO）。

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  
  パッケージインポート時の .env 自動読み込みを無効化します（テスト時に便利）。

.env ファイルはプロジェクトルート（.git または pyproject.toml を基準）に置くと自動で読み込まれます。フォーマットは一般的な KEY=VALUE 形式を想定します（コメント行や export キーワードもサポート）。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定の読み込み・検証
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・保存ユーティリティ）
    - news_collector.py
      - RSS 収集・前処理・銘柄抽出・DB 保存
    - pipeline.py
      - ETL ジョブ（差分更新・バックフィル・品質チェックのハイレベル処理）
    - schema.py
      - DuckDB スキーマ定義 / 初期化関数（init_schema）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - ファクター計算（mom/vol/value 等）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル構築（正規化・フィルタ）
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（インメモリ DB コピー + 日次ループ）
    - simulator.py
      - PortfolioSimulator（擬似約定・約定記録・時価評価）
    - metrics.py
      - バックテスト評価指標
    - run.py
      - CLI エントリポイント（バックテスト実行）
    - clock.py
      - 将来拡張用の模擬時計
  - execution/
    - __init__.py
    - （発注 API 接続 / 実運用の実装はここに追加）
  - monitoring/
    - （監視用コード・Slack 通知等を配置する想定）

---

## 開発・貢献メモ

- コードはテストしやすいように外部依存（HTTP, DB）を注入可能に設計されています。例えば jquants_client の id_token は引数で注入できますし、news_collector の URLopen は差し替え可能です。
- DuckDB のスキーマは冪等に作成されるため、何度でも init_schema() を実行して構いません。
- ランタイムの振る舞いは KABUSYS_ENV や LOG_LEVEL によって変わるため、開発時は development を使用してください。

---

README では主な使い方とアーキテクチャ概要を示しました。より詳細な仕様（StrategyModel.md, DataPlatform.md, BacktestFramework.md 等）がリポジトリにある場合はそちらを参照してください。質問や追加のドキュメントが必要であればお知らせください。