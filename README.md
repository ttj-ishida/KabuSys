# KabuSys

日本株自動売買システムのライブラリ（モジュール群）。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテストフレームワーク、ニュース収集などを提供します。本プロジェクトは研究環境 → 戦略設計 → バックテスト → 実運用（execution / monitoring）までのワークフローを想定しています。

---

## 主要な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF対策・トラッキング除去・前処理）
- ETL / データ基盤
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - 差分 ETL（差分取得・バックフィル考慮・品質チェックの設計）
- 研究 / ファクター計算
  - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financialsから）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略 / シグナル生成
  - ファクターの正規化と features テーブルへの保存（冪等）
  - features と AI スコアを統合した final_score の計算、BUY / SELL シグナル生成（冪等）
  - Bear レジーム抑制・売買ルール・エグジット判定実装
- バックテスト
  - インメモリ DuckDB に切り出して日次シミュレーションを実行
  - スリッページ・手数料モデル、ポートフォリオサイジング、評価指標（CAGR, Sharpe, MaxDD 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 実運用（骨組み）
  - execution / monitoring 名前空間を準備（発注・監視ロジックを接続可能）

---

## 動作環境・前提

- Python 3.10+
  - typing の `|` や型注釈（Python 3.10 以降）を使用しています。
- 必要な主要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリで多く実装されていますが、外部 API 呼び出しや環境に応じた追加パッケージが必要になる場合があります）

セットアップ時は仮想環境の利用を推奨します。

---

## セットアップ手順（例）

1. 仮想環境作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt がある場合はそちらを使ってください。無ければ最低限 duckdb と defusedxml を入れてください）
   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトルートで:
   # pip install -e .
   ```

3. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を利用します（パッケージ初期化時に自動でロードされます。不要な自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携用）
     - KABU_API_BASE_URL — kabuステーション API の base URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
     - DUCKDB_PATH — デフォルト DB パス（例: data/kabusys.duckdb）
     - SQLITE_PATH — 監視系 DB（例: data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live
     - LOG_LEVEL — DEBUG/INFO/...
   - 例: `.env`
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ
   conn.close()
   ```

---

## 使い方（主要な操作例）

以下は代表的な操作のサンプルです。詳細な引数や挙動は各モジュールのドキュメント（コード内 docstring）を参照してください。

- J-Quants から株価を取得して保存（jquants_client）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ニュース収集（RSS）と DB 保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット（任意）
  results = run_news_collection(conn, known_codes=known_codes)
  conn.close()
  ```

- 特徴量構築（feature_engineering）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- シグナル生成（signal_generator）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
  conn.close()
  ```

- バックテスト（CLI または API）
  - CLI:
    ```bash
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
    ```
  - API:
    ```python
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest

    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    # result.history, result.trades, result.metrics を参照
    conn.close()
    ```

- ETL パイプライン（差分更新の例）
  - pipeline モジュールには差分取得・保存・品質チェックの設計が含まれています（run_prices_etl など）。実行例（概要）:
    ```python
    from kabusys.data.pipeline import run_prices_etl
    from kabusys.data.schema import init_schema
    from datetime import date

    conn = init_schema("data/kabusys.duckdb")
    fetched, saved = run_prices_etl(conn, target_date=date.today())
    conn.close()
    ```

---

## ディレクトリ構成（抜粋）

以下はコードベースの主要ファイル・モジュール構成です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント・保存ユーティリティ
    - news_collector.py      — RSS ニュース収集・前処理・DB 保存
    - schema.py              — DuckDB スキーマ定義と init_schema()
    - stats.py               — z-score 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン（差分取得・バックフィル等）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル生成（正規化・フィルタ）
    - signal_generator.py    — final_score 計算・BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py              — バックテストエンジン（run_backtest）
    - simulator.py           — PortfolioSimulator（疑似約定・履歴管理）
    - metrics.py             — バックテスト評価指標計算
    - clock.py               — SimulatedClock（将来用途）
    - run.py                 — CLI エントリポイント
  - execution/               — 発注周り（プレースホルダ）
  - monitoring/              — 監視・アラート（プレースホルダ）
  - その他ドキュメントはコード内 docstring に詳細設計が含まれます。

---

## 注意点 / 運用上のヒント

- 環境変数は .env / .env.local を通じて自動ロードされます（プロジェクトルートは .git / pyproject.toml を探索して決定）。テスト時に自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API にはレート制限があり（120 req/min）、クライアントは固定間隔スロットリングとリトライ・トークン自動更新のロジックを実装しています。大量取得は抑制してください。
- ファイルや DB の初期化は冪等に設計されています（ON CONFLICT / トランザクション処理）。
- 戦略・バックテストでは Look-ahead バイアスに注意しており、各モジュールは target_date 時点のみの情報に基づく実装方針です。
- production（ライブ）運用時は KABUSYS_ENV を `live` に設定し、kabuステーション連携・Slack 通知等を適切に構成してください。実口座接続は慎重に行ってください。

---

## 参考（主な API 関数）

- kabusys.config.settings — 環境変数取得（JQUANTS_REFRESH_TOKEN など）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.run_news_collection / save_raw_news
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic
- kabusys.strategy.build_features / generate_signals
- kabusys.backtest.run_backtest / CLI: python -m kabusys.backtest.run

---

README はここまでです。コード中の docstring に設計方針・詳細な利用法・引数仕様が豊富に記載されていますので、実装や拡張を行う際は該当モジュールのコメントを参照してください。必要なら個別機能の使い方（例: ETL の細かいフローやパラメータ説明）をさらにドキュメント化します。