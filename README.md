# KabuSys

日本株向けの自動売買 / バックテスト基盤ライブラリです。  
ファクター計算・特徴量エンジニアリング・シグナル生成・ポートフォリオ構築・バックテスト・データ取得（J-Quants）・ニュース収集など、運用環境と研究環境の双方を想定したモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とします。

- DuckDB を中心にしたデータパイプライン（価格・財務・ニュースなど）の管理
- 研究（factor/research）で得られた生ファクターを正規化して features を作成
- features と AI スコアを統合して売買シグナルを生成
- ポートフォリオ構築（候補選定、重み算出、ポジションサイジング、セクター制限等）
- バックテストエンジン（擬似約定・スリッページ・手数料モデル）
- J-Quants API クライアントや RSS ベースのニュース収集器など ETL ツール

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「ネットワーク・セキュリティ対策（SSRF 等）」を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ、DuckDB 保存用ユーティリティ）
  - news_collector: RSS 取得・前処理・raw_news / news_symbols への保存（SSRF 対策・gzip/サイズ上限・トラッキングパラメータ除去）
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering.build_features: ファクターの正規化・フィルタ・features テーブルへの UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを作成し signals テーブルへ保存
- portfolio/
  - portfolio_builder: 候補選定（スコア順）と重み計算（等配分 / スコア重み）
  - position_sizing.calc_position_sizes: 単元丸め・リスクベース / 重みベースの株数計算・aggregate cap の調整
  - risk_adjustment: セクターキャップ適用・市場レジームに応じた資金乗数
- backtest/
  - engine.run_backtest: DuckDB データをコピーしてインメモリでバックテストを実行する高レベル関数
  - simulator.PortfolioSimulator: 擬似約定ロジック（BUY/SELL の処理、部分約定、スリッページ・手数料適用、時価評価）
  - metrics.calc_metrics: CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio 等の評価指標
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config:
  - 環境変数読み込み（.env / .env.local の自動ロード）、必須変数取得ユーティリティ

---

## セットアップ手順（開発環境）

以下は一般的なセットアップ手順の例です。実環境では pyproject.toml / requirements.txt を参照してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 最低限必要となる外部ライブラリ（コード中に明示されている例）:
     ```
     pip install --upgrade pip
     pip install duckdb defusedxml
     ```
   - （開発用）パッケージをローカルインストール（もし pyproject.toml がある場合）:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 代表的な環境変数（.env の例）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUS_API_BASE_URL=http://localhost:18080/kabusapi
     ```

5. DuckDB スキーマ初期化
   - コード内で参照されている `kabusys.data.schema.init_schema()` を使ってスキーマを作成・接続する（実装されていることを前提）。
   - J-Quants からデータを取得して tables を埋めるか、既存の DuckDB ファイルを用意してください。

---

## 使い方（主要ワークフロー例）

1. J-Quants からデータ取得（ETL）
   - jquants_client を使って日足・財務・上場銘柄情報・カレンダーを取得し、DuckDB に保存します。
   - 例（概念）:
     ```py
     from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     token = get_id_token()
     recs = fetch_daily_quotes(id_token=token, date_from=date(2022,1,1), date_to=date(2024,1,1))
     save_daily_quotes(conn, recs)
     conn.close()
     ```

2. 特徴量作成（features）
   - DuckDB 接続を用意し、target_date を指定して特徴量をビルド:
     ```py
     from kabusys.strategy import build_features
     from kabusys.data.schema import init_schema
     from datetime import date
     conn = init_schema("data/kabusys.duckdb")
     n = build_features(conn, date(2024, 1, 4))
     print(f"features written: {n}")
     conn.close()
     ```

3. シグナル生成
   - features と ai_scores（任意）を用いてシグナルを生成:
     ```py
     from kabusys.strategy import generate_signals
     conn = init_schema("data/kabusys.duckdb")
     count = generate_signals(conn, date(2024,1,4))
     print(f"signals written: {count}")
     conn.close()
     ```

4. バックテスト（CLI）
   - 予め DuckDB を用意した上で CLI から実行:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - 主要オプション:
     - --start / --end : バックテスト期間
     - --cash : 初期資金（JPY）
     - --slippage / --commission : スリッページ・手数料率
     - --allocation-method : equal | score | risk_based
     - --lot-size : 単元株（デフォルト 100）
     - --db : DuckDB ファイルパス（必須）

5. バックテスト API 呼び出し（プログラムから）
   ```py
   from kabusys.backtest.engine import run_backtest
   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
   # result.history, result.trades, result.metrics を参照
   ```

---

## 重要な設計上の注意点

- ルックアヘッドバイアス対策
  - features / signals などは target_date 時点までに取得可能なデータのみを使用する設計になっています。
- 冪等性
  - データ保存時は ON CONFLICT や日付単位の置換（DELETE→INSERT）で冪等性を確保しています。
- セキュリティ / 可用性
  - news_collector は SSRF 対策（リダイレクト時の検証、プライベート IP ブロック）、レスポンスサイズ制限、defusedxml を用いた XML パース等を実装しています。
- 自動環境変数読み込み
  - config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動で読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして無効化できます。

---

## ディレクトリ構成

（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/  (発注 / 実際の execution 層は拡張想定)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - backtest/
    - engine.py
    - simulator.py
    - metrics.py
    - clock.py
    - run.py
    - __init__.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py 等、DB スキーマ管理モジュールを想定)
  - portfolio/ (上記)
  - monitoring/ (監視・アラート関連モジュール（未詳細実装）)

---

## よく使う関数／エントリポイント（まとめ）

- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=..., weights=...)
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- python -m kabusys.backtest.run (CLI)
- kabusys.data.jquants_client.get_id_token / fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.run_news_collection

---

## 開発・拡張のヒント

- 単体テストでは config の自動 .env 読み込みを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと良いです。
- バックテストでは本番 DB を直接書き換えないよう、engine._build_backtest_conn() がインメモリの DuckDB を構築してコピーします。外部ファイルに対しては読み取り専用に使ってください。
- 単元サイズ（lot_size）や手数料・スリッページモデルは実運用と合わせて調整してください。

---

この README はコードベースの主要機能と使い方の概要を示したものです。各モジュールの詳細な仕様・数式・設計根拠はソース内の docstring や設計ドキュメント（StrategyModel.md, PortfolioConstruction.md 等、リポジトリ内にある想定の設計書）を参照してください。必要であれば README に追記・改善します。