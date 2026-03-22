# KabuSys

日本株向けの自動売買システム向けライブラリ群（ミニマム実装）。  
データ取得（J-Quants）、ETL / データベーススキーマ、研究用ファクター計算、特徴量生成、シグナル生成、バックテストフレームワーク、ニュース収集などを含みます。

---

## プロジェクト概要

KabuSys は以下のレイヤーを持つ設計です：

- Data Platform: J-Quants API / RSS からデータ取得し DuckDB に保存（raw → processed → feature）。
- Research: ファクター計算・特徴量探索（ルックアヘッドバイアスに配慮）。
- Strategy: 特徴量を正規化・統合してシグナル（BUY/SELL）を生成。
- Backtest: 日次シミュレータを用いたバックテストエンジン／メトリクス算出。
- Execution (雛形): 発注／約定／ポジションテーブル等のスキーマを提供（実際の接続は含まない）。
- News: RSS 収集・テキスト前処理・銘柄抽出・DB保存。

設計上のポイント：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）。
- DuckDB をデータ格納用に使用（init_schema によりスキーマ初期化）。
- 冪等性（ON CONFLICT/UPSERT）とトランザクション保護。
- ネットワーク呼び出しはレート制御・リトライ・トークン自動更新を実装。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - raw データの DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）
  - RSS ニュース収集（fetch_rss）と raw_news / news_symbols 保存
- スキーマ管理
  - init_schema(db_path) — DuckDB スキーマの作成（Raw / Processed / Feature / Execution レイヤー）
- 研究（Research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC・統計サマリ（calc_forward_returns, calc_ic, factor_summary）
- 特徴量とシグナル
  - build_features(conn, target_date) — features テーブルを作成／更新
  - generate_signals(conn, target_date, ...) — signals テーブルに BUY/SELL を出力
- バックテスト
  - run_backtest(conn, start_date, end_date, ...) — 日次ループのバックテスト実行
  - PortfolioSimulator / DailySnapshot / TradeRecord / BacktestMetrics
- ユーティリティ
  - zscore_normalize（クロスセクション Z スコア正規化）
  - ニュースの銘柄抽出（extract_stock_codes）

---

## セットアップ手順

前提
- Python 3.10+（typing の | 演算子、from __future__ annotations を利用）
- DuckDB を利用可能な環境

例（推奨）:

1. 仮想環境を作成して有効化（例: venv）
   - Unix / macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (cmd):
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージのインストール（最小）
   ```bash
   pip install duckdb defusedxml
   ```
   ※ 実プロジェクトでは追加パッケージ（HTTP クライアント等）を入れる場合があります。requirements.txt がある場合はそちらを使ってください。

3. パッケージをプロジェクトルートから利用する
   - 開発中はソースを直接参照するため、`PYTHONPATH` にプロジェクトルートを追加するか、pip の editable install を行うこともできます:
     ```bash
     pip install -e .
     ```
     （setup.py / pyproject.toml が整備されている場合）

4. DuckDB スキーマ初期化
   Python REPL やスクリプト内から:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 環境変数 / 設定

自動でプロジェクトルートの `.env` / `.env.local` を読み込む仕組みがあります（CWD に依存しない探索）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings クラスより）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知に利用する Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack のチャンネル ID（必須）

任意（デフォルトあり）:
- KABUS_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要ユースケース）

1. DB 初期化（1回）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

2. J-Quants からデータ取得と保存（ETL の一部）
   - J-Quants からレコードを取得して保存（例）
     ```python
     from kabusys.data import jquants_client as jq
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     # 例: 2024-01-01 〜 2024-01-31 の日足を取得して保存
     from datetime import date
     records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
     saved = jq.save_daily_quotes(conn, records)
     conn.close()
     ```

   - ETL 全体（パイプライン）は `kabusys.data.pipeline` にまとまっています（差分取得・バックフィル処理・品質チェック等）。

3. ニュース収集と銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   conn.close()
   ```

4. 特徴量生成（features テーブルの作成）
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024,1,31))
   ```

5. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   count = generate_signals(conn, target_date=date(2024,1,31))
   ```

6. バックテスト（コマンドライン）
   - CLI entry: `kabusys.backtest.run`
   - 実行例:
     ```bash
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --db data/kabusys.duckdb \
       --cash 10000000
     ```
   - 出力: CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / Total Trades

7. ライブラリ関数を直接使ったバックテスト呼び出し
   ```python
   from kabusys.backtest.engine import run_backtest
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   # result.history, result.trades, result.metrics を参照
   ```

---

## よく使う API（抜粋）

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources, known_codes)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(...)
  - calc_ic(...)

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)

---

## ディレクトリ構成

（ルート: src/kabusys 以下の主要ファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント／保存処理
    - news_collector.py            — RSS 収集・前処理・保存
    - schema.py                    — DuckDB スキーマ定義 / init_schema
    - stats.py                     — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                  — ETL パイプライン（差分取得・品質チェック）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — IC/将来リターン/統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py       — features テーブル生成（正規化 / フィルタ）
    - signal_generator.py          — final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                    — バックテストのメインループ
    - simulator.py                 — PortfolioSimulator / 約定ロジック
    - metrics.py                   — バックテスト評価指標算出
    - run.py                       — CLI エントリポイント
    - clock.py                     — SimulatedClock（将来拡張用）
  - execution/
    - __init__.py                  — 発注／実行関連（実装雛形）
  - monitoring/                    — 監視関連（ファイルは空/雛形として配置）
  - backtest/ (同上)
  - その他: README.md（本ファイル）

---

## 注意事項 / 実運用に向けた補足

- J-Quants の API レート制限やエラー処理は実装済みですが、実運用では追加の監視・メトリクス蓄積が必要です。
- 発注部分（kabuステーション等）への実接続／オーダー管理は別途セキュアに実装する必要があります（本リポジトリは発注 API を直接実行しない設計）。
- DuckDB のファイルパスやバックアップ戦略、アクセス制御は運用ポリシーに従ってください。
- テストと CI: ネットワーク依存部分（API/RSS）はモックしてユニットテストを書くことを推奨します（コード中でモックしやすい設計になっています）。

---

もし README に追加したい使用例（特定の ETL ワークフロー、バックテスト設定、サンプル .env.example など）があれば、必要に応じて追記します。