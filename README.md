KabuSys
=======

KabuSys は日本株向けの自動売買 / データプラットフォームの実装骨子です。  
主要コンポーネント（データ収集、特徴量計算、シグナル生成、バックテスト、ニュース収集、ETL スイート）を含み、DuckDB をデータ層に用いる設計になっています。

この README はリポジトリの主要機能・セットアップ・基本的な使い方・ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
--------------
- 目的: 日本株の戦略開発〜運用を支援するためのモジュール群（データ取得、ファクター計算、シグナル生成、バックテスト、ニュース収集、ETL）。
- データストア: DuckDB を想定（ファイル DB / in-memory 両対応）。
- 設計方針:
  - ルックアヘッドバイアス回避（target_date 時点のデータのみ参照する等）。
  - 冪等性（DB への INSERT は ON CONFLICT 等で上書き制御）。
  - テスト容易性（id_token 注入、in-memory DB、関数単位での呼び出し可能）。
  - ネットワーク安全・堅牢性（J-Quants API リトライ・レートリミット、RSS の SSRF 対策等）。

主な機能一覧
--------------
- データ取得 / 保存
  - J-Quants API クライアント（jquants_client）: 株価日足、財務データ、マーケットカレンダーの取得・保存（リトライ、レート制御、トークン自動更新対応）。
  - ニュース収集（news_collector）: RSS から記事収集、前処理、記事ID生成、銘柄抽出・保存（SSRF 対策、gzip 対応）。
  - ETL パイプライン（data.pipeline）: 差分取得・バックフィル、品質チェックフック。
  - DuckDB スキーマ定義・初期化（data.schema）。

- 研究 / ファクター
  - ファクター計算（research.factor_research）: Momentum / Volatility / Value 等の計算（prices_daily / raw_financials を参照）。
  - 特徴量探索（research.feature_exploration）: Forward returns, IC（Spearman）算出、factor summary。
  - 統計ユーティリティ（data.stats）: Z スコア正規化など。

- 戦略
  - 特徴量エンジニアリング（strategy.feature_engineering）: research で計算した生ファクターを正規化・フィルタして features テーブルへ UPSERT。
  - シグナル生成（strategy.signal_generator）: features と ai_scores を統合して final_score を算出し BUY / SELL シグナルを生成し signals テーブルへ保存。Bear レジーム抑制、エグジット判定（ストップロス等）。

- バックテスト
  - シミュレータ（backtest.simulator）: 擬似約定（スリッページ・手数料考慮）、ポートフォリオスナップショット、トレード履歴。
  - エンジン（backtest.engine）: データのインメモリ複製、日次ループでのシグナル適用、ポジション管理、結果集計。
  - メトリクス（backtest.metrics）: CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio 等。
  - CLI ランナー（backtest.run）: コマンドラインでバックテストを実行可能。

- その他
  - ニュース→銘柄紐付け、raw_* テーブルの管理、ログレベル制御、環境変数ベースの設定管理（config.py）。

セットアップ手順
----------------
前提
- Python 3.10 以上（コードは | 型注釈等を使用しているため）。
- DuckDB を利用するためネイティブ拡張が入らない環境では pip インストールが必要。

基本手順（例）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate      # Unix/macOS
   .venv\Scripts\activate.bat     # Windows
   ```

3. 必要パッケージのインストール
   - requirements.txt が無い場合は主要依存を個別に入れてください。例:
   ```
   pip install duckdb defusedxml
   ```
   - ロギングやテストで他パッケージが必要な場合は各自追加してください。

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を配置すると自動でロードされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（execution 層利用時）
     - SLACK_BOT_TOKEN: Slack 通知に利用する場合の Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1（自動ロード停止）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）など

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   Python REPL などで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - ":memory:" を渡すとインメモリ DB が作られます（バックテスト用など）。

使い方（代表的なフロー）
----------------------

1) データ ETL（J-Quants から株価・財務・カレンダー取得）
   - ETL 関数は kabusys.data.pipeline にまとまっています。例（Python）:
   ```python
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_prices_etl, run_news_collection

   conn = init_schema("data/kabusys.duckdb")

   # 株価差分 ETL の例
   from datetime import date
   target = date.today()
   fetched, saved = run_prices_etl(conn, target_date=target)
   print("prices fetched:", fetched, "saved:", saved)

   # ニュース収集（known_codes を渡すと銘柄抽出・紐付けも行う）
   known_codes = {"7203", "6758", "9984"}  # 例
   result = run_news_collection(conn, known_codes=known_codes)
   print(result)
   ```

2) 特徴量構築 → シグナル生成
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import build_features, generate_signals
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   tdate = date(2024, 1, 31)

   # features を作成（raw ファクターを正規化して features テーブルへ挿入）
   count = build_features(conn, target_date=tdate)
   print("features upserted:", count)

   # signals を生成（features, ai_scores, positions を参照して signals テーブルへ書き込む）
   signals_written = generate_signals(conn, target_date=tdate)
   print("signals written:", signals_written)
   ```

3) バックテスト（CLI または Python）
   - CLI:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 \
       --slippage 0.001 \
       --commission 0.00055 \
       --max-position-pct 0.20 \
       --db data/kabusys.duckdb
     ```
   - Python API:
     ```python
     from kabusys.backtest.engine import run_backtest
     from kabusys.data.schema import init_schema
     from datetime import date

     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
     print(result.metrics)
     conn.close()
     ```

主要モジュール / API の概要
-------------------------
- kabusys.config.settings
  - 環境変数から設定値を取得（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, DUCKDB_PATH 等）
  - 自動 .env ロード（プロジェクトルートを .git または pyproject.toml から検出）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema(db_path) — DuckDB のスキーマを作成して接続を返す
- kabusys.data.pipeline
  - run_prices_etl, run_news_collection など（差分取得・保存・品質検査）
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)
  - backtest.simulator.PortfolioSimulator / DailySnapshot / TradeRecord
  - backtest.metrics.calc_metrics

ディレクトリ構成
----------------
（src 配下を基準に簡易ツリー例）
- src/kabusys/
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
    - metrics.py
    - simulator.py
    - clock.py
    - run.py
  - execution/         # 発注関連（空 __init__ 等、実装箇所あり）
  - monitoring/        # 監視・通知（将来的な実装想定）

注意事項 / 運用メモ
-------------------
- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを指定してください（設定ミスは例外になります）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しはレート制限（120 req/min）に従う実装になっています。大量データ収集時は注意してください。
- RSS 収集には SSRF 対策・受信サイズ上限など保護機構が組み込まれていますが、未承認のフィードを追加する際は慎重に設定してください。
- DuckDB スキーマは初期化処理で複数のテーブル・インデックスを作成します。既存 DB を初期化する場合はバックアップを推奨します。

問題点 / 拡張案
----------------
- 現在のコードは基本ロジックを中心にした実装です。実運用では以下の点を検討してください:
  - 監視・アラート（Slack 通知やジョブ監視）
  - 実際の発注連携（kabu ステーション API との安全な接続）
  - AI スコア算出パイプライン（ai_scores テーブルへの投入）
  - 運用時のジョブスケジューリング（cron / Airflow 等）
  - テストカバレッジや型チェックの強化

貢献
----
- バグ修正・機能拡張は歓迎します。Pull Request の前に issue を立てて概要を共有してください。

お問い合わせ
------------
- 実装に関する質問・改善提案はリポジトリの Issue をご利用ください。

以上。README の補足や特定機能の詳しいドキュメント（例えば StrategyModel.md / DataPlatform.md）を作成希望であれば、その章ごとに詳細を生成します。