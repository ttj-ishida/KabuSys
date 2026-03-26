# KabuSys

日本株向け自動売買システム（ライブラリ / バックテスト / データ ETL 群）

概要
- KabuSys は日本株のリサーチ、ファクター構築、シグナル生成、ポートフォリオ構築、バックテスト、およびデータ取得（J-Quants / RSS ニュース）を目的としたモジュール群です。
- モジュール設計は「ルックアヘッドバイアス回避」「DuckDB を用いた時系列データ管理」「冪等性／トランザクション制御」「ネットワーク安全性（SSRF対策等）」を重視しています。

主な機能
- データ取得
  - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - RSS ベースのニュース収集（SSRF対策、前処理、記事→銘柄紐付け）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar / raw_news 等）
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング
  - research 側の生ファクターを正規化・結合して features テーブルへ UPSERT
  - ユニバースフィルタ（最低株価・平均売買代金）
- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear 相場抑制 / BUY / SELL ロジック（ストップロス等）
  - signals テーブルへの冪等書き込み
- ポートフォリオ構築
  - 候補選択、等金額 / スコア加重配分、リスクベースサイジング
  - セクター集中制限（apply_sector_cap）、レジーム乗数
- バックテスト
  - インメモリ DuckDB にデータをコピーして安全に実行
  - ポートフォリオシミュレータ（約定・スリッページ・手数料モデル・部分約定）
  - バックテスト評価指標（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
  - CLI エントリポイント: python -m kabusys.backtest.run
- その他
  - 環境設定管理モジュール（.env 自動読み込み、必須キーの取得）
  - ニュース抽出 → 銘柄コード紐付けユーティリティ

動作要件（推奨）
- Python 3.10+
- 依存パッケージ（抜粋）
  - duckdb
  - defusedxml
- （ネットワーク連携を行う場合）J-Quants API のリフレッシュトークン等

セットアップ手順

1. リポジトリをクローン／インストール
   - 開発環境での例:
     - git clone ... && cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限 duckdb と defusedxml をインストール）
     - pip install duckdb defusedxml

2. Python バージョン
   - 本コードは Python 3.10 以上を想定（型注釈に | を使用）。

3. 環境変数 / .env
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（.git または pyproject.toml を基準にルート探索）。
   - 自動読み込みを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必須環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（実行環境に応じて）
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - デフォルトで参照する DB パス等（環境変数未指定時のデフォルト値）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
   - settings を使った取得例（Python）:
     - from kabusys.config import settings
     - token = settings.jquants_refresh_token

4. DuckDB スキーマ初期化
   - 多くの処理（バックテスト、ETL）は DuckDB のスキーマ初期化関数 init_schema(db_path) を利用します（data.schema.init_schema を参照）。
   - 既存の DB を使う場合は事前に必要テーブル（prices_daily / raw_financials / features / ai_scores / market_regime / market_calendar / stocks / raw_news / news_symbols 等）を準備してください。

使い方（代表的なコマンド／API）

- バックテスト（CLI）
  - 実行例:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - 主なオプション:
    - --cash, --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --lot-size など

- 特徴量構築（Python API）
  - 例:
    - from kabusys.strategy import build_features
    - import duckdb, datetime
    - conn = duckdb.connect("path/to/kabusys.duckdb")
    - n = build_features(conn, datetime.date(2024, 1, 31))
    - conn.close()

- シグナル生成（Python API）
  - 例:
    - from kabusys.strategy import generate_signals
    - conn = duckdb.connect("path/to/kabusys.duckdb")
    - count = generate_signals(conn, datetime.date(2024, 1, 31))
    - conn.close()

- ニュース収集ジョブ
  - run_news_collection(conn, sources=None, known_codes=None)
  - 例:
    - from kabusys.data.news_collector import run_news_collection
    - conn = duckdb.connect("path/to/kabusys.duckdb")
    - results = run_news_collection(conn, known_codes=set_of_valid_codes)
    - conn.close()

- J-Quants データ取得 / 保存
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
  - 例（概念）:
    - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    - conn = duckdb.connect("path/to/kabusys.duckdb")
    - records = fetch_daily_quotes(date_from=..., date_to=...)
    - inserted = save_daily_quotes(conn, records)
    - conn.close()

主なモジュール（API の要点）
- kabusys.config
  - settings: Settings インスタンス。環境変数取得 (jquants_refresh_token / kabu_api_password / slack_bot_token / duckdb_path / env / log_level など)
- kabusys.data.jquants_client
  - fetch_* / save_* 系、get_id_token()、内部の rate limiter / retry ロジック
- kabusys.data.news_collector
  - fetch_rss, preprocess_text, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)
  - backtest CLI: kabusys.backtest.run
  - simulator / metrics モジュール（PortfolioSimulator, DailySnapshot, TradeRecord, BacktestMetrics）

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数と .env 自動読み込みロジック
  - data/
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - news_collector.py — RSS 収集と raw_news 保存
    - (schema.py, calendar_management.py 等は別ファイルとして想定)
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — IC / forward returns / 統計
  - strategy/
    - feature_engineering.py — features 構築処理
    - signal_generator.py — final_score 計算と signals テーブル生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（risk_based / equal / score）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py — バックテスト全体ループ
    - simulator.py — 擬似約定とポートフォリオ管理
    - metrics.py — 評価指標
    - run.py — CLI エントリポイント
  - execution/  — 発注・実行レイヤ（パッケージ化済み、実装は環境依存）
  - monitoring/ — 監視/通知関連（Slack 通知等、別モジュール想定）
  - portfolio/, research/ 等の __init__.py による API エクスポート

注意事項 / 運用上のポイント
- Look-ahead Bias に関する配慮:
  - 特徴量・シグナル生成・バックテストは「target_date 時点で利用可能なデータのみ」を使う設計になっています。
- 冪等性:
  - DB への挿入は ON CONFLICT / トランザクションで冪等に設計されています。ETL は再実行可能です。
- セキュリティ:
  - news_collector は SSRF を防ぐためホスト検証・リダイレクト検査・受信サイズ制限等を実装しています。
  - jquants_client はレート制御とリトライ、401 時のトークン自動再取得を持ちます。
- テスト / CI:
  - 自動ロードの影響を避けるためテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

貢献
- バグ報告・機能追加提案は issue を立ててください。
- コード貢献は pull request を送ってください。スタイルは PEP8 準拠を推奨します。

ライセンス
- リポジトリに含まれる LICENSE を参照してください。

補足
- README の例にあるコマンドや API 呼び出しは、このリポジトリ内に schema 初期化や環境依存の部分（外部サービスの認証情報、DB の前処理）が必要です。実運用では ETL パイプラインと DB 構築を先に行ってください。