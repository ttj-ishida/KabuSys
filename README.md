# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（研究・ETL・特徴量生成・シグナル生成・バックテストを含む）

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants などの外部データソースから株価・財務・カレンダー・ニュースを取得して DuckDB に保存する ETL
- 研究環境で計算した生ファクターを加工して特徴量（features）を作る特徴量エンジニアリング
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成する戦略ロジック
- 売買シグナルに対するメモリ内ポートフォリオシミュレーションとバックテスト（トレード履歴・メトリクス出力）
- ニュース収集（RSS）やニュース→銘柄紐付けのためのユーティリティ

設計方針として、ルックアヘッドバイアス対策や冪等性、外部 API のレート制御・リトライ、DuckDB 上での安全なトランザクション操作を重視しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足・財務・取引カレンダー）: レートリミット、リトライ、トークン自動リフレッシュ対応
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事IDのハッシュ化）
  - DuckDB スキーマ初期化（init_schema）と冪等保存（ON CONFLICT）
- データ処理 / 研究
  - ファクター計算: Momentum / Value / Volatility / Liquidity（prices_daily / raw_financials ベース）
  - 特徴量生成: 正規化（Z スコア）、ユニバースフィルタ、クリッピング、features テーブルへの UPSERT
  - 特徴量探索: 将来リターン計算、IC（Spearman）計算、統計サマリー
- 戦略 / シグナル
  - ファクター・AI スコア統合による final_score 計算
  - Bear レジーム抑制、BUY/SELL シグナルの生成と signals テーブルへの冪等書き込み
- バックテスト
  - インメモリで本番 DB の必要データをコピーして実行（run_backtest）
  - PortfolioSimulator（スリッページ・手数料モデル、約定処理、マーク・ツー・マーケット）
  - トレード履歴から評価指標（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio）を算出
- ETL パイプライン（差分更新・バックフィル・品質チェックの仕組み）

---

## 前提（Prerequisites）

- Python 3.10+
- 必要なライブラリ（少なくとも）:
  - duckdb
  - defusedxml

（その他、標準ライブラリのみで多くのロジックが実装されています。追加の依存はプロジェクトの packaging/requirements に従ってください）

---

## セットアップ手順

1. ソース取得（例）
   - git clone …（リポジトリをチェックアウト）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt があればそれを使用）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（auto-load を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効にする（値が有れば無効）
     - KABUSYS_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例（.env の一部）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python から:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - あるいはテスト用にインメモリ:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（代表的な操作例）

- バックテスト（CLI）
  - パッケージに付属する CLI エントリポイント:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
    ```
  - 引数の説明は CLI ヘルプ（--help）を参照してください（slippage, commission, max-position-pct 等）。

- プログラムからバックテストを実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()
  # result.metrics に評価指標が入っています
  ```

- 特徴量構築（feature engineering）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,1,31))
  conn.close()
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
  conn.close()
  print(f"signals generated: {count}")
  ```

- ニュース収集 & 保存（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes: 抽出する銘柄コードのセット（銘柄抽出に利用）
  res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  conn.close()
  print(res)
  ```

- J-Quants から株価・財務取得＆保存（例）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, recs)
  conn.close()
  print(saved)
  ```

- ETL（差分更新）や pipeline の利用
  - `kabusys.data.pipeline` に差分更新や品質チェックのためのユーティリティやジョブが含まれています。プロジェクトの運用スクリプトから呼び出して差分取得・保存・品質確認を行ってください。

---

## 主なモジュールとディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動読み込み機能、Settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS 収集・正規化・保存
    - pipeline.py — ETL 差分更新 / ジョブ管理
    - schema.py — DuckDB スキーマ定義と init_schema()
    - stats.py — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features を作成する処理
    - signal_generator.py — features + ai_scores → signals の生成ロジック
  - backtest/
    - __init__.py
    - engine.py — run_backtest（全体ループ）
    - simulator.py — PortfolioSimulator（約定ロジック・履歴）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI ラッパー
    - clock.py — SimulatedClock（将来拡張用）
  - execution/ — 発注／実行レイヤ（骨格）
  - monitoring/ — 監視用モジュール（SQLite 等を想定）

スキーマ（DuckDB）の主要テーブル（schema.py に定義）
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores, market_regime
- signals, signal_queue, orders, trades, positions, portfolio_performance

---

## 備考 / 運用上の注意

- 環境変数は .env / .env.local から自動読み込みされますが、テスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限があります（本実装では 120 req/min を意識）。大量取得時はバックオフとページネーションに注意してください。
- ニュース収集や外部 URL 取得部分には SSRF 対策や gzip/サイズ上限チェック等を実装していますが、運用環境で追加制約が必要な場合は設定してください。
- DuckDB スキーマは冪等で作成されます。既存の DB を破壊しないよう、初回は `init_schema()` を利用してください。
- 本リポジトリのロジックは研究・シミュレーション用途に重点を置いており、本番運用での直接 API 発注やマネー管理には追加の安全対策が必要です。

---

この README はコードベースの主要ポイントに基づいた要約です。各モジュールの詳細な使い方はソース内の docstring を参照してください。ご不明点があれば使いたい機能や実行シナリオを教えてください。適宜具体例を追加します。