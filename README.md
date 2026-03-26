# KabuSys

日本株向けの自動売買／リサーチフレームワーク（モジュール群）。  
データ取得（J-Quants）、ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などを含む。

---

## プロジェクト概要

KabuSys は、以下を目的としたモジュール設計の Python パッケージです。

- J-Quants API 等から市場データ・財務データを取得して DuckDB に保存する ETL
- 研究（research）モジュールでファクターを計算・解析
- 特徴量（features）作成 -> シグナル（signals）生成（strategy モジュール）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、リスク調整）
- バックテストフレームワーク（擬似約定、スナップショット、メトリクス）
- ニュース収集・記事と銘柄の紐付け

設計方針として「ルックアヘッドバイアスの排除」「DB に対する冪等な書き込み」「外部発注層への依存分離」「テストしやすい純粋関数の分離」などが採用されています。

---

## 主な機能一覧

- data/
  - J-Quants API クライアント（認証・ページネーション・レート制御・再試行）
  - raw_prices / raw_financials / market_calendar への保存ユーティリティ
  - ニュース RSS 収集（SSRF対策・トラッキングパラメータ除去・正規化）
- research/
  - momentum, volatility, value 等のファクター計算
  - 将来リターン算出、IC（スピアマンρ）計算、統計サマリ
- strategy/
  - 特徴量作成（Zスコア正規化・ユニバースフィルタ・クリップ）
  - シグナル生成（final_score 計算、Bear レジーム抑制、SELL 条件）
- portfolio/
  - 候補選定・重み付け（等金額 / スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（risk_based / equal / score、単元株丸め、aggregate cap）
- backtest/
  - インメモリ DuckDB にデータをコピーして安全にバックテスト
  - PortfolioSimulator（擬似約定、スリッページ・手数料モデル）
  - run_backtest API と CLI エントリポイント
  - バックテストメトリクス（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
- config.py
  - .env 自動読み込み（.env / .env.local）と必須環境変数取得、KABUSYS_ENV / LOG_LEVEL 管理

---

## セットアップ手順

前提: Python 3.9+（型ヒントに union 型表記などを使用）。プロジェクトルートに pyproject.toml または .git があることを想定。

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\Activate)

2. 必要パッケージをインストール  
   （ここでは最低限必要なパッケージを例示します。プロジェクトの pyproject.toml / requirements.txt を参照してください）
   - pip install duckdb defusedxml

   開発インストール（プロジェクトがパッケージ化されている前提）
   - pip install -e .

3. 環境変数の設定  
   プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動で読み込まれます。  
   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot Token（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - DUCKDB_PATH: デフォルト DuckDB DB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite DB（例: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（省略時: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（省略時: INFO）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化  
   コード中に `kabusys.data.schema.init_schema` が参照されます（このスクリプトで tables を作成する想定）。まずは DB を準備してください:
   - Python から init_schema を呼ぶか、付属のスクリプトで DB を初期化してください。
   （※ schema 定義ファイルはここに含まれていませんが、実運用ではスキーマ初期化が必要です）

---

## 使い方

ここでは主要な利用パターンを示します。

1. バックテスト（CLI）

   DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が用意されていることが前提です。

   例:
   ```
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2024-12-31 \
     --cash 10000000 --db path/to/kabusys.duckdb
   ```

   オプション（一部）:
   - --slippage, --commission, --max-position-pct, --allocation-method, --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size

   プログラム API から呼ぶ場合:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.backtest.engine import run_backtest

   conn = init_schema("path/to/kabusys.duckdb")
   result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
   conn.close()

   # result.history, result.trades, result.metrics を利用
   ```

2. 特徴量作成（strategy.feature_engineering）

   features テーブルに対して日次で特徴量を構築します（DuckDB 接続が必要）。

   例:
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy.feature_engineering import build_features

   conn = duckdb.connect("path/to/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 1, 31))
   print(f"upserted {n} features")
   conn.close()
   ```

3. シグナル生成（strategy.signal_generator）

   features / ai_scores / positions テーブルを参照して signals テーブルを生成します。

   例:
   ```python
   from kabusys.strategy.signal_generator import generate_signals
   generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
   ```

4. データ取得（J-Quants）

   J-Quants API からデータを取得して保存する関数群が提供されています。認証は `settings.jquants_refresh_token` を使用します。

   例（概念）:
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   records = fetch_daily_quotes(date_from=..., date_to=...)
   save_daily_quotes(conn, records)
   ```

5. ニュース収集

   RSS フィードを取得して raw_news / news_symbols に保存します（SSRF 対策・トラッキング除去済み）。

   例:
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)
   ```

6. バックテストの詳細操作（プログラム）

   run_backtest は内部で:
   - データのインメモリコピー（本番 DB を汚さない）
   - PortfolioSimulator（擬似約定）
   - ポートフォリオ構築（select_candidates, apply_sector_cap, calc_position_sizes 等）
   - metrics 計算（calc_metrics）

   を実行し、BacktestResult を返します。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュール群のツリーと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — .env 自動読み込み、環境設定（Settings）
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 収集・前処理・DB 保存
    - (その他: schema.py, calendar_management.py 等が想定される)
  - research/
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / 統計要約
  - strategy/
    - feature_engineering.py — features 作成（正規化・フィルタ）
    - signal_generator.py — final_score 計算、BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — ポジションサイズ計算（単元丸め、aggregate cap）
    - risk_adjustment.py — セクター上限、レジーム乗数
  - backtest/
    - engine.py — バックテストのメインロジック（run_backtest）
    - simulator.py — PortfolioSimulator（擬似約定、mark_to_market、トレード記録）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py — 将来拡張用の模擬時計
  - execution/ — 発注・実行層（インターフェース想定、実装は別途）
  - monitoring/ — 監視・アラート機能（Slack 統合等、実装想定）
  - portfolio/ — 上記ポートフォリオ関連
  - research/ — 研究モジュール
  - backtest/ — バックテストモジュール

---

## 注意点・運用上のヒント

- look-ahead バイアス回避:
  - 取得日時（fetched_at）やデータの date を厳密に扱い、features / signals は target_date 以前のデータのみを使う設計です。
- 環境変数の自動読み込み:
  - `config.py` はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テスト時に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB スキーマ:
  - 本リポジトリ内に schema 定義ファイル（init_schema）がある想定です。バックテストや ETL を動かす前にスキーマを初期化してください。
- エラーハンドリング:
  - J-Quants クライアントは 401 時にトークンリフレッシュを自動実行、ネットワークエラーや 429 等に対する指数バックオフを実装しています。
- ニュース収集:
  - RSS の取得は SSRF 対策済みですが、外部ソースの扱いは十分に注意してください。既知の銘柄コード集合を渡すと記事⇄銘柄紐付けを行います。

---

## 追加情報・貢献

- 実装仕様（StrategyModel.md、PortfolioConstruction.md、BacktestFramework.md、DataPlatform.md 等）を参照すると各アルゴリズム仕様の背景がわかります（本リポジトリではコード内コメントで参照されている想定）。
- バグ修正・機能追加の際はユニットテスト（特に純粋関数群: position_sizing, risk_adjustment, factor 計算など）を追加してください。

---

必要であれば README に次の項目を追加します:
- requirements.txt / pyproject.toml の具体的パッケージリスト
- schema の初期化スクリプト使用例（init_schema 実装内容）
- 実運用時の運用手順（ETL スケジュール、Slack 通知設定例）
- よくあるトラブルシューティング（トークンエラー、DB スキーマ不整合 等）

どの追加を希望しますか？