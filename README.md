KabuSys
=======

日本株向けの自動売買・リサーチ基盤ライブラリです。DuckDB を用いたデータ管理、J-Quants API 経由のデータ取得、特徴量計算・シグナル生成、バックテストシミュレータなどを含みます。ライブラリはモジュール単位で呼び出してパイプラインや CLI を組み立てられる設計です。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（日足 / 財務 / 上場銘柄情報 / 市場カレンダー）
  - RSS ニュース収集（SSRF 対策・トラッキング除去・銘柄抽出）
  - DuckDB への冪等保存関数（ON CONFLICT で更新）
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDBベース）
  - ファクターの正規化（Z スコア）と features テーブル生成（冪等）
  - 研究用途の IC 計算・統計サマリ
- シグナル生成
  - features と AI スコアを統合して final_score を算出
  - BUY/SELL シグナルの生成（Bear レジーム抑制、ストップロス判定等）
  - signals テーブルへ日付単位で置換保存（冪等）
- ポートフォリオ構築 / サイジング
  - 候補選定、等金額/スコア加重、リスクベース計算
  - セクター集中制限、レジームに応じた乗数適用
  - 単元株丸め・aggregate cap（現金上限）調整
- バックテスト
  - インメモリ DuckDB にコピーして安全にバックテスト実行
  - 約定・スリッページ・手数料モデルを考慮したポートフォリオシミュレータ
  - メトリクス計算（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio）
  - CLI エントリポイント: python -m kabusys.backtest.run

セットアップ
-----------
1. 必要な Python バージョン
   - Python 3.10 以上（PEP 604 型注釈などを使用）

2. インストール（仮想環境推奨）
   - 必要最低限の依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
     - pip install -e .  （プロジェクトをパッケージとして使う場合）

3. 環境変数 / .env
   - プロジェクトは起点ファイルから親ディレクトリに .git または pyproject.toml を探索してプロジェクトルートを特定し、以下の順で .env を自動ロードします:
     - OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数を設定:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な環境変数（アプリケーション起動時に必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意 / 既定値
     - KABUSYS_ENV — development | paper_trading | live（既定: development）
     - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（既定: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（既定: data/monitoring.db）
   - 値が未設定で必須な場合は Settings クラスが ValueError を投げます（kabusys.config.settings 経由で参照可能）。

使い方（概要）
--------------
- DuckDB スキーマ初期化
  - コード内では kabusys.data.schema.init_schema(db_path) を呼んで DuckDB 接続を取得します（プロジェクトのスキーマ初期化関数を実装している想定）。
- データ取得（例）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - data = fetch_daily_quotes(date_from=..., date_to=...)
  - save_daily_quotes(conn, data)
- 特徴量ビルド
  - from kabusys.strategy import build_features
  - build_features(conn, target_date)  # features テーブルに日付単位で冪等書き込み
- シグナル生成
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, target_date, threshold=0.6)
- バックテスト（CLI）
  - DB を事前に prices_daily、features、ai_scores、market_regime、market_calendar 等で整備しておく必要があります。
  - 実行例:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - 主なオプション:
    - --cash, --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --lot-size など
- バックテスト（ライブラリ呼び出し）
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, allocation_method="risk_based")
  - 戻り値: BacktestResult(history, trades, metrics)
- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources={...}, known_codes=set_of_codes)

重要な実装ポイント（運用時の注意）
--------------------------------
- 自動環境読み込み:
  - プロジェクトルート検出に .git または pyproject.toml を使用するため、配布環境では .env の配置に注意してください。
- J-Quants クライアント:
  - リトライ（指数バックオフ）、レートリミット（120 req/min）、401 時の自動トークンリフレッシュ、ページネーション対応を含みます。
- ニュース収集:
  - SSRF 対策や受信サイズ制限、XML パース安全対策（defusedxml）を実装しています。
- 冪等性:
  - 多くの保存関数は ON CONFLICT（または DO NOTHING）を使って冪等にしています。ETL のリトライに安全です。
- バックテスト:
  - 実行時は本番 DB の signals / positions を汚さないよう、データをインメモリ DuckDB にコピーして実行します。
  - レジーム（market_regime）やセクター制限（stocks.sector）に依存します。必要なテーブルが整備されていることを確認してください。

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下の主要モジュール）
- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - jquants_client.py        — J-Quants API クライアント + 保存関数
    - news_collector.py        — RSS 収集・前処理・保存
    - ...（schema, calendar_management 等を想定）
  - research/
    - factor_research.py       — momentum/volatility/value 計算
    - feature_exploration.py   — IC / forward returns / summary
  - strategy/
    - feature_engineering.py   — features テーブル作成
    - signal_generator.py      — final_score と signals の生成
  - portfolio/
    - portfolio_builder.py     — 候補選定・配分重み
    - position_sizing.py       — 株数決定・aggregate cap
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - backtest/
    - engine.py                — バックテストループ（run_backtest）
    - simulator.py             — 約定ロジック・ポートフォリオ管理
    - metrics.py               — バックテスト評価指標
    - run.py                   — CLI entry point
    - clock.py                 — 将来用の模擬時計
  - execution/                  — 実運用向け発注層（プレースホルダ）
  - monitoring/                 — 監視・アラート（プレースホルダ）
  - ...その他ユーティリティモジュール

サンプル .env（例）
------------------
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

貢献・拡張
---------
- 移植性や運用観点の改善（単元株マップ、銘柄別手数料モデル、分足バックテストなど）は設計上拡張しやすくなっています。
- unit test / CI を追加することで更に信頼性を高めてください。

ライセンス
---------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（ここでは明記されていません）。

補足
----
- 実運用では必ず paper_trading で十分に検証してください（KABUSYS_ENV を paper_trading に設定）。
- DB スキーマ初期化やテーブル定義は kabusys.data.schema に実装されている前提です。バックテストや ETL の前にスキーマを準備してください。

必要であれば、README にサンプルスクリプト（ETL / 日次ジョブ）や DB スキーマのサンプル定義、よくあるエラーと対処法を追記できます。どの情報を補足しますか？