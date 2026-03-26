KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の実装群です。  
主に以下の機能を持つモジュール群で構成され、データ収集 → 特徴量作成 → シグナル生成 → ポートフォリオ構築 → バックテスト のワークフローをサポートします。

主な特徴
--------
- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動更新対応）
- RSS からのニュース収集（正規化・SSRF対策・記事→銘柄紐付け）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量正規化・features テーブルへの保存（冪等）
- シグナル生成（ファクター + AI スコア統合、Buy/Sell 判定、Bear フィルタ等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクターキャップ）
- バックテストフレームワーク（擬似約定モデル、スリッページ／手数料、メトリクス算出）
- DuckDB を利用したローカルデータレイヤ

セットアップ手順
----------------
1. 推奨 Python バージョン
   - Python 3.10 以上を推奨（型ヒントで | 記法を使用しています）。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   - 必要最低限の依存例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに setup/pyproject があれば pip install -e . でインストールしてください。）

4. 環境変数 / .env
   - プロジェクトルートの .env/.env.local を自動で（優先度: OS env > .env.local > .env）読み込みます。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等向け）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（execution 層で使用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
   - 任意 / デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL — DEBUG / INFO / ...
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

使い方（代表的なワークフロー）
----------------------------

1. データ取得（J-Quants）
   - jquants_client モジュールを使ってデータを取得し、DuckDB に保存する流れです。
   - 例:
     - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     - records = fetch_daily_quotes(date_from=..., date_to=...)
     - save_daily_quotes(conn, records)

2. ニュース収集
   - kabusys.data.news_collector.run_news_collection(conn, sources=..., known_codes=...)
   - RSS フィード取得 → raw_news に保存 → 必要に応じて銘柄コード抽出・news_symbols へ紐付け

3. 特徴量作成
   - build_features(conn, target_date)
   - DuckDB の prices_daily / raw_financials を参照して特徴量を計算し、features テーブルへ UPSERT します。

4. シグナル生成
   - generate_signals(conn, target_date, threshold=0.60, weights=None)
   - features / ai_scores / positions を参照して BUY/SELL シグナルを signals テーブルへ書き込みます。

5. バックテスト実行（CLI）
   - DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）が用意されていることを前提に実行します。
   - 使い方（例）:
     - python -m kabusys.backtest.run \
         --start 2023-01-01 --end 2023-12-31 \
         --cash 10000000 --db path/to/kabusys.duckdb
   - 主なオプション:
     - --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --risk-pct, --stop-loss-pct, --lot-size など
   - 実行結果としてバックテストの履歴・トレード・メトリクスが表示されます。

主要 API（抜粋）
----------------
- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.log_level など

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes

- kabusys.research
  - calc_momentum(conn, date), calc_volatility(conn, date), calc_value(conn, date)
  - calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - build_features(conn, date)
  - generate_signals(conn, date, threshold, weights)

- kabusys.portfolio
  - select_candidates(buy_signals, max_positions)
  - calc_equal_weights(candidates), calc_score_weights(candidates)
  - calc_position_sizes(...), apply_sector_cap(...), calc_regime_multiplier(regime)

- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)

注意事項 / 前提
---------------
- DuckDB のスキーマ初期化（init_schema）や、必要なテーブルへのデータ投入は別途行う必要があります（コード内で init_schema が参照されています）。
- Look-ahead bias を避けるため、データ取得・保存はバックテストの対象期間に合わせて慎重に行ってください（fetched_at 等のメタ情報を活用）。
- production (live) 環境での発注連携は execution 層（kabuステーション等）との統合が必要です（execution パッケージが依存先になります）。

ディレクトリ構成
----------------
（src/kabusys 以下の主なファイル／モジュール）
- kabusys/
  - __init__.py
  - config.py                         — 環境変数/設定管理
  - data/
    - jquants_client.py                — J-Quants API クライアント（取得/保存）
    - news_collector.py                — RSS ニュース収集・保存・銘柄抽出
    - (その他 data 関連モジュール: schema, stats, calendar_management 等を想定)
  - research/
    - factor_research.py               — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py           — IC / 将来リターン / 統計サマリー
  - strategy/
    - feature_engineering.py           — features 作成（正規化・UPSERT）
    - signal_generator.py              — final_score 計算・BUY/SELL 生成
  - portfolio/
    - portfolio_builder.py             — 候補選定・重み付け
    - position_sizing.py               — 発注株数計算（丸め・集計キャップ）
    - risk_adjustment.py               — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py                        — バックテスト全体ループ
    - simulator.py                     — 擬似約定・ポートフォリオ状態管理
    - metrics.py                       — バックテスト指標計算
    - run.py                           — CLI エントリポイント
    - clock.py                         — 将来用の模擬時計
  - execution/ (発注・kabuステーション等の実装用フォルダ)
  - monitoring/ (監視・Slack 通知等)

例: 環境変数（.env）テンプレート
--------------------------------
以下は最低限想定されるキーの例です（プロジェクトに .env.example があればそれを参照してください）。

JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

貢献 / ライセンス
------------------
この README はコードベースの概要と使い方をまとめたものです。プロジェクトへの貢献手順やライセンスはリポジトリのルート（CONTRIBUTING.md、LICENSE 等）を参照してください。

補足
----
- 各モジュールの詳細な仕様（StrategyModel.md、PortfolioConstruction.md、BacktestFramework.md、DataPlatform.md 等）はコード内コメントに参照があります。実装の根拠やパラメータ解説はそちらを参照してください。
- 質問や追加で README に載せたい内容（セットアップの自動化手順、CI の説明、実運用時の注意点など）があれば教えてください。README を拡張します。