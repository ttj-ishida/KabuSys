KabuSys
======

日本株向けの自動売買 / 研究プラットフォームの一部実装です。  
本リポジトリはデータ取得・特徴量計算・シグナル生成・ポートフォリオ構築・バックテスト・ニュース収集などの主要コンポーネントを含み、研究環境とバックテスト環境での再現性ある実験や運用前チェックを想定しています。

特徴
---
- データ取得
  - J-Quants API クライアント（レート制限、リトライ、トークン自動更新、ページネーション対応）
  - RSS ニュース収集（SSRF対策、トラッキングパラメータ除去、記事IDの冪等生成）
- 研究用ファクター計算
  - momentum / volatility / value 等の定量ファクターを DuckDB 上で計算
  - Z スコア正規化・ユニバースフィルタ
- シグナル生成
  - 正規化済みファクター + AIスコアを統合して final_score を計算、BUY/SELL シグナルを作成
  - Bear レジームでは BUY を抑制するロジック
- ポートフォリオ構築
  - 候補選定、等配分 / スコア加重、リスクベースのサイジング、セクター集中制限
- バックテストフレームワーク
  - 擬似約定モデル（スリッページ・手数料・単元丸め）
  - 日次スナップショット・トレード記録・メトリクス計算（CAGR, Sharpe, MaxDD 等）
  - 単一関数 run_backtest で全ループを実行
- データベース
  - DuckDB を想定（データスキーマはコード内から初期化して使用）

必須環境・依存
---
- Python 3.10+（型ヒントで | 演算子等を使用）
- 主要パッケージ（例）
  - duckdb
  - defusedxml
- その他、実際に運用する際は J-Quants API の認証情報や kabuステーション の API 情報を別途準備してください。

セットアップ手順
---
1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . または pip install -r requirements.txt を使ってください）

4. 環境変数 (.env) の用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（OS環境変数が優先）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

  推奨される環境変数（最低限）
  - JQUANTS_REFRESH_TOKEN=...        # J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD=...            # kabuステーション API パスワード（必須）
  - SLACK_BOT_TOKEN=...              # Slack 通知用 Bot Token（必須）
  - SLACK_CHANNEL_ID=...             # Slack チャンネル ID（必須）
  - DUCKDB_PATH=data/kabusys.duckdb  # DuckDB ファイルパス（任意、デフォルト）
  - SQLITE_PATH=data/monitoring.db   # SQLite（モニタリング用、任意）
  - KABUSYS_ENV=development|paper_trading|live  # 動作モード（default: development）
  - LOG_LEVEL=INFO|DEBUG|...         # ログレベル（default: INFO）

使い方（例）
---

1) バックテスト（CLI）
- 事前準備: DuckDB ファイルに必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks など）を用意してください。バックテストは既存DBを読み取り専用で利用します。
- 実行例:
  - python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db path/to/kabusys.duckdb

- 主なオプション:
  - --slippage, --commission, --max-position-pct, --allocation-method (equal|score|risk_based), --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size

- 出力: 標準出力にバックテスト指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）が表示されます。戻り値として run_backtest は BacktestResult（history, trades, metrics）を返します（ライブラリとして利用する場合）。

2) 特徴量作成（Python API）
- 例スニペット:
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features

    conn = init_schema("path/to/kabusys.duckdb")
    try:
        n = build_features(conn, target_date=date(2023, 12, 31))
        print(f"upserted {n} features")
    finally:
        conn.close()

  - build_features は DuckDB 接続（prices_daily, raw_financials テーブルが必要）と target_date を受け、features テーブルへ日付単位で置換挿入します。

3) シグナル生成（Python API）
- 例スニペット:
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import generate_signals

    conn = init_schema("path/to/kabusys.duckdb")
    try:
        total = generate_signals(conn, target_date=date(2023, 12, 31), threshold=0.6)
        print(f"generated {total} signals")
    finally:
        conn.close()

  - generate_signals は features / ai_scores / positions を参照し、signals テーブルへ日付単位で置換挿入します。

4) ニュース収集（プログラム呼び出し）
- 例スニペット:
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    from kabusys.data.schema import init_schema

    conn = init_schema("path/to/kabusys.duckdb")
    try:
        known_codes = {"7203", "6758", "9432"}  # など
        results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
        print(results)
    finally:
        conn.close()

  - fetch_rss / save_raw_news / save_news_symbols の一連処理をまとめて実行します。SSRF 対策や圧縮レスポンス検査などの安全機構が組み込まれています。

ライブラリとしての使い方（短い一覧）
- データ取得: kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- ETL保存: save_daily_quotes / save_financial_statements / save_market_calendar
- 研究: kabusys.research.calc_momentum, calc_volatility, calc_value, calc_ic, calc_forward_returns
- 特徴量: kabusys.strategy.build_features
- シグナル: kabusys.strategy.generate_signals
- ポートフォリオ: kabusys.portfolio.select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- バックテスト: kabusys.backtest.run_backtest
- ニュース: kabusys.data.news_collector.run_news_collection

注意点 / 運用上のヒント
---
- 環境変数の自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込みします。
  - 読み込み順序: OS環境 > .env.local > .env
  - 自動読み込みを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかである必要があります。
- 本番・ライブ運用前に必ず paper_trading モードで入念な検証を行ってください。live モードでは実際の約定や外部APIが関与するためリスクが高くなります。
- バックテストのデータは Look-ahead bias を避けるため、各データ取得時点（fetched_at）や報告日を正しく管理してから使用してください。本実装でもその考え方を踏襲していますが、データ整備はユーザ側の責任です。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理（.env 自動読み込み、必須変数チェック）
- data/
  - jquants_client.py       — J-Quants API クライアント
  - news_collector.py       — RSS ニュース収集・保存ロジック
  - (その他: schema, calendar_management など参照されるモジュール)
- research/
  - factor_research.py      — momentum / volatility / value 等のファクター計算
  - feature_exploration.py  — IC / forward returns / 統計サマリ
- strategy/
  - feature_engineering.py  — features の作成（正規化・UPSERT）
  - signal_generator.py     — final_score 計算・BUY/SELL シグナル生成
- portfolio/
  - portfolio_builder.py    — 候補選定・重み算出
  - position_sizing.py      — 株数決定・リスク制限・単元丸め
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
- backtest/
  - engine.py               — バックテストループ（run_backtest）
  - simulator.py            — 擬似約定・ポートフォリオ管理
  - metrics.py              — バックテスト評価指標計算
  - run.py                  — CLI Entrypoint for backtest
  - clock.py                — SimulatedClock（将来用）
- execution/                 — 発注 / 実行層（プレースホルダ）
- monitoring/                — モニタリング層（プレースホルダ）
- portfolio/ __init__.py     — 公開 API エクスポート
- strategy/ __init__.py      — 公開 API エクスポート
- research/ __init__.py      — 公開 API エクスポート
（実際のリポジトリでは上記以外に data/schema.py やデータ初期化用スクリプト等が含まれる想定です。）

ライセンス・貢献
---
- 本 README ではライセンスファイルの記載を省略しています。実リポジトリの LICENSE を参照してください。
- バグ報告や機能追加の提案は Issue を通じてお願いします。

最後に
---
この README はコードベース内の docstring と実装を元に作成しています。実運用・本番導入の前に必ずローカル検証（paper_trading 等）を行い、外部APIキーや取引パラメータの管理に注意してください。必要であれば README をプロジェクトの実状に合わせて補足・修正してください。