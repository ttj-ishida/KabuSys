KabuSys — 日本株自動売買基盤
=======================

概要
----
KabuSys は日本株のデータ取得 / ETL / ファクター計算 / シグナル生成 / バックテストを行うためのライブラリ群です。  
主な設計方針は以下の通りです。

- DuckDB をデータ格納に用いる（ローカルファイルまたはインメモリ）。
- J-Quants API 等から取得した生データを Raw → Processed → Feature → Execution の層で管理。
- ルックアヘッドバイアスを避けるため、各処理は target_date 時点のデータのみ参照する。
- ETL・保存処理は冪等（ON CONFLICT / トランザクション）に実装。
- バックテストは本番 DB を汚さないためにインメモリ接続へデータをコピーして実行。

機能一覧
--------
主な機能群と代表モジュール：

- 環境設定
  - kabusys.config: .env の自動ロード、環境変数管理（必須変数の取得等）

- データ取得 / ETL / スキーマ
  - kabusys.data.jquants_client: J-Quants API クライアント（ページネーション、リトライ、レート制限、保存関数）
  - kabusys.data.news_collector: RSS 取得・前処理・raw_news 保存（SSRF対策、gzip制限、トラッキング除去）
  - kabusys.data.pipeline: 差分取得・ETL ロジック、品質チェックフック
  - kabusys.data.schema: DuckDB スキーマ定義と init_schema()

- データ処理 / 統計
  - kabusys.data.stats: z-score 正規化等の共通ユーティリティ

- 研究（Research）
  - kabusys.research.factor_research: momentum / volatility / value 等のファクター計算
  - kabusys.research.feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー

- 戦略（Strategy）
  - kabusys.strategy.feature_engineering: 生ファクターの正規化と features テーブルへの書き込み
  - kabusys.strategy.signal_generator: features + ai_scores を統合して BUY/SELL シグナルを生成

- バックテスト
  - kabusys.backtest.engine: 日次ループ・シミュレーションの実行（run_backtest）
  - kabusys.backtest.simulator: 擬似約定・ポートフォリオ状態管理（スリッページ・手数料モデル）
  - kabusys.backtest.metrics: バックテスト指標計算（CAGR, Sharpe, MaxDD, WinRate 等）
  - CLI: python -m kabusys.backtest.run による実行

- 実行（Execution）
  - フォルダは用意されています（発注等の実装を想定）

セットアップ
----------
前提
- Python 3.10 以上（X | Y 型ヒントを使用しています）
- DuckDB が必要（pip パッケージを使用）

推奨手順（ローカル開発）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数（.env）
- プロジェクトはルートにある .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 必須の環境変数（config.Settings 参照）：
  - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（jquants_client に使用）
  - KABU_API_PASSWORD      — kabu ステーション API パスワード（execution 層で使用想定）
  - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID       — Slack チャネル ID
- 任意 / デフォルト値を持つ：
  - KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL              — DEBUG/INFO/...（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（値は任意）

例 .env（最低限）
  JQUANTS_REFRESH_TOKEN=your_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C0123456789
  DUCKDB_PATH=data/kabusys.duckdb

初期 DB の準備
- DuckDB のスキーマを作成：
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

使い方（主要ユースケース）
-----------------------

1) スキーマ初期化
- Python REPL / スクリプトで：
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

2) ETL（株価・財務・カレンダー等の差分取得）
- pipeline モジュールの関数を利用：
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  # target_date に取得終了日を指定（通常は今日）
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()

- ニュース収集ジョブ:
  from kabusys.data.news_collector import run_news_collection
  result = run_news_collection(conn, sources=None, known_codes=set_of_codes)

3) ファクター整備（features テーブルの作成）
- build_features を呼び出して target_date の features を生成：
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()

4) シグナル生成
- generate_signals を呼んで signals テーブルを書き換え：
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)

5) バックテスト（CLI）
- 事前条件: 指定した DuckDB ファイルに prices_daily, features, ai_scores, market_regime, market_calendar が格納されていること。
- 実行例:
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
- オプションで初期資金やスリッページ、手数料、max position pct を調整可能。

6) バックテスト（プログラムから）
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  # result.history, result.trades, result.metrics を参照

開発・テストに役立つポイント
----------------------------
- 環境変数自動読み込みを無効にする（テストで明示的に環境を組みたい場合）:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB の ":memory:" を使えばインメモリ DB で高速にユニットテスト可能:
  conn = init_schema(":memory:")
- news_collector._urlopen など一部関数はテスト時にモックしやすい設計。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント + 保存関数
  - news_collector.py            — RSS 取得・前処理・保存
  - schema.py                    — DuckDB スキーマ定義 / init_schema
  - stats.py                     — zscore_normalize 等
  - pipeline.py                  — ETL 差分更新ロジック
- research/
  - __init__.py
  - factor_research.py           — momentum/volatility/value の計算
  - feature_exploration.py       — forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py       — features テーブル構築
  - signal_generator.py          — final_score 計算・signals 書き込み
- backtest/
  - __init__.py
  - engine.py                    — run_backtest（本体ループ）
  - simulator.py                 — PortfolioSimulator, mark_to_market, execute_orders
  - metrics.py                   — バックテスト評価指標
  - run.py                       — CLI エントリポイント
  - clock.py                     — SimulatedClock（将来拡張用）
- execution/                      — 発注関連（プレースホルダ）
- monitoring/                     — 監視 / メトリクス（実装想定）

注意事項 / 実運用に関するメモ
--------------------------
- J-Quants API のレート制限に注意（実装では 120 req/min を想定し RateLimiter で制御）。
- ETL は API の後出し修正（backfill）を吸収するため最終取得日から数日前を再取得する仕組みを組み込んでいます。
- production 環境では KABUSYS_ENV を live に設定し、ログレベルや Slack 通知などの振る舞いを適切に構成してください。
- Execution 層（実際の注文送信）は慎重に実装・テストしてください（テストネット / paper_trading 環境の活用を推奨）。

ライセンス
----------
（ここにライセンス情報を追加してください）

問い合わせ / 貢献
-----------------
バグ報告・機能提案・プルリクエストはリポジトリの Issue/PR を利用してください。コード内の docstring に処理仕様・参照ドキュメント（例: StrategyModel.md, DataPlatform.md）への言及があります。README を拡張して利用方法・運用手順を整備することを歓迎します。