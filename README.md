# KabuSys

日本株向けの自動売買・研究プラットフォーム（Pythonライブラリ）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集などの機能を含むモジュール群で構成されています。

この README はプロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の目的をもつコンポーネント群を提供します。

- J-Quants API から日本株の日次株価・財務データ・カレンダーの取得（rate limit / retry / token refresh 対応）
- RSS 等からのニュース収集と銘柄紐付け（SSRF対策、トラッキングパラメータ除去）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の初期化と管理
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化・合成（features テーブルへの保存）
- シグナル生成（features と AI スコアの統合、BUY/SELL 生成）
- バックテストフレームワーク（擬似約定、手数料・スリッページ、メトリクス計算）
- ETL パイプラインの補助（差分取得・品質チェック・保存）

設計方針として「ルックアヘッドバイアス回避」「DB への冪等保存」「外部システム（発注）への直接依存を持たない」などが採用されています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（jquants_client）
  - raw_prices / raw_financials / market_calendar 等の保存（冪等）
- ニュース収集
  - RSS フィード取得、記事正規化、raw_news / news_symbols への保存
  - SSRF 対策、gzip サイズ制限、トラッキングパラメータ除去
- データスキーマ
  - DuckDB 用の包括的スキーマ初期化（init_schema）
  - テーブル群（prices_daily, features, ai_scores, signals, positions 等）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 戦略（strategy）
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）：重み付け、Bear フィルタ、BUY/SELL 生成
- バックテスト（backtest）
  - 日次シミュレータ（擬似約定、手数料/スリッページ適用）
  - run_backtest：DB からデータコピーして日次ループを回す CLI エントリポイントあり
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
- ETL パイプライン補助（data.pipeline）
  - 差分取得 / 保存 / 品質チェックのフレームワーク

---

## セットアップ手順（開発者向け・ローカル実行）

1. Python 環境準備（例: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリのインストール（最低限）
   - pip install duckdb defusedxml
   - その他プロジェクトで必要なライブラリがあれば requirements.txt / pyproject.toml に従ってインストールしてください。

   （このリポジトリにパッケージ化情報があれば `pip install -e .` で編集可能なインストールが可能です）

3. データベース初期化（DuckDB）
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 初回は parent ディレクトリが自動で作成されます。":memory:" を指定するとインメモリ DB。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を探す）にある `.env` / `.env.local` を読み込みます（自動で読み込まれるのがデフォルト）。
   - 自動ロードを無効にしたいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN  （J-Quants の refresh token）
     - KABU_API_PASSWORD       （kabuステーション API 用パスワード）
     - SLACK_BOT_TOKEN         （Slack 通知用ボットトークン）
     - SLACK_CHANNEL_ID       （Slack チャンネル ID）
   - 省略可能 / デフォルトあり:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG / INFO / ...、デフォルト: INFO）

   - サンプル .env の例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   ※ センシティブな情報は安全に管理してください（公開リポジトリに置かない）。

---

## 使い方（主要ユースケース）

以下は代表的なワークフロー例と簡単なコード/コマンド例です。

1. DuckDB スキーマを初期化
   - Python:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

2. J-Quants からデータ取得・保存（ETL）
   - data.pipeline の関数群を使って差分取得を行います（スクリプト化が想定）。
   - 例（概念）:
     from kabusys.data import jquants_client as jq
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     records = jq.fetch_daily_quotes(date_from=..., date_to=...)
     jq.save_daily_quotes(conn, records)

   - pipeline モジュールは差分ロジック・品質チェックを提供します（run_prices_etl など）。

3. 特徴量（features）作成
   - 研究モジュールで計算した生ファクターを正規化して features テーブルへ保存:
     from kabusys.strategy import build_features
     build_features(conn, target_date)  # target_date は datetime.date

4. シグナル生成
   - features と ai_scores を組み合わせて signals テーブルへ書き込み:
     from kabusys.strategy import generate_signals
     generate_signals(conn, target_date)

5. バックテスト
   - CLI 実行例:
     python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
   - または Python API:
     from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date, end_date)
     result.metrics などで評価指標にアクセス可能

6. ニュース収集（RSS）
   - data.news_collector.run_news_collection を呼び出して raw_news / news_symbols に保存:
     from kabusys.data.news_collector import run_news_collection
     run_news_collection(conn, sources=None, known_codes=set_of_codes)

7. システム設定の参照
   - 環境変数は kabusys.config.settings からアクセス可能:
     from kabusys.config import settings
     token = settings.jquants_refresh_token

注意:
- generate_signals / build_features は DuckDB の特定テーブル（prices_daily, raw_financials, features, ai_scores, positions 等）を参照します。事前に該当テーブルが適切に埋められている必要があります。
- run_backtest は本番 DB から必要なデータ範囲をコピーしてインメモリでバックテストを実行するため、本番 DB を汚染しません。

---

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: 各種環境変数ラッパー（JQUANTS_REFRESH_TOKEN 等）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)
  - 主要テーブル（features, ai_scores, prices_daily, positions, signals 等）を作成
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection / extract_stock_codes
- kabusys.research.factor_research
  - calc_momentum / calc_volatility / calc_value
- kabusys.research.feature_exploration
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)
  - backtest.run CLI で直接実行可能

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートに src/ がある構成を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - stats.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - backtest/
      - __init__.py
      - engine.py
      - simulator.py
      - metrics.py
      - clock.py
      - run.py  (CLI entry point)
      - run (additional runner)
    - execution/
      - __init__.py
      (発注関連モジュールのプレースホルダ)
    - monitoring/
      - (監視・アラート用モジュールのプレースホルダ)

- ドキュメント（想定）
  - DataPlatform.md, StrategyModel.md, BacktestFramework.md 等（実装コメントで参照）

---

## 運用上の注意・トラブルシューティング

- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部で固定間隔スロットリングとリトライを実装していますが、大量の並列リクエストは避けてください。
- DuckDB のスキーマ作成は冪等です。init_schema を複数回呼んでも問題ありません。
- news_collector は外部 RSS を取得するため SSRF 対策やレスポンスサイズ制限、gzip 解凍後サイズ確認などの防御ロジックを含みます。RSS 取得で失敗するソースがあっても他ソースの収集は継続されます。
- 本システムは発注（実際の注文発行）をデフォルトで行わない設計です。実注文を出す execution 層の実装や権限付与は別途注意して行ってください（API パスワード等の管理に注意）。

---

## 参考：よく使うコマンド例

- バックテスト CLI 実行
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- Python で DB 初期化と簡単な操作（REPL）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  from kabusys.strategy import build_features, generate_signals
  import datetime
  build_features(conn, datetime.date(2024,1,2))
  generate_signals(conn, datetime.date(2024,1,2))

---

README は随時更新してください。実際のデプロイや運用では、secret の管理（Vault 等）、ログ収集、監視・アラートの設定、CI/CD による依存管理を追加することを推奨します。