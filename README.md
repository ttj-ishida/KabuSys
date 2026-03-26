# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリ。  
ファクタ計算・特徴量生成・シグナル生成・ポートフォリオ構築・バックテスト・データ取得（J-Quants）・ニュース収集など、研究〜運用に必要な主要コンポーネントをモジュール単位で提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- DuckDB を分析用 DB として利用
- 発注/実行層と分離された純粋関数群（テスト容易性）
- 冪等性・トランザクション制御を重視した DB 操作

バージョン: 0.1.0

--------------------------------------------------------------------------------
目次
- プロジェクト概要
- 機能一覧
- 動作環境 / 必要パッケージ
- セットアップ手順
- 環境変数（.env）
- 使い方（主要ユースケースと例）
- ディレクトリ構成
- 補足 / 注意点

--------------------------------------------------------------------------------
プロジェクト概要
- ファクタ算出（Momentum, Volatility, Value, Liquidity）
- 特徴量の正規化・クリッピング・features テーブルへの保存
- AI スコアやファクターを統合して売買シグナルを生成（BUY/SELL）
- セクター集中制限・レジーム乗数などのリスク調整
- ポジションサイジング（等金額・スコア加重・リスクベース）
- ポートフォリオシミュレータとバックテストエンジン（スリッページ・手数料モデル含む）
- J-Quants API クライアント（取得／保存）、RSS ニュース収集モジュール

--------------------------------------------------------------------------------
機能一覧（主要モジュール）
- kabusys.config
  - .env 自動読み込み（プロジェクトルート判定）
  - Settings クラス（必要な環境変数をプロパティで提供）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し、ページネーション、リトライ、保存関数（raw_prices / raw_financials / market_calendar / stocks など）
  - news_collector: RSS 取得（SSRF 対策、gzip 対応）、raw_news 保存、銘柄抽出
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB を用いたファクター計算）
  - feature_exploration: IC 計算、将来リターン、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: ファクター正規化・features テーブルへの UPSERT
  - signal_generator.generate_signals: final_score 計算、BUY/SELL 判定、signals テーブルへの置換
- kabusys.portfolio
  - portfolio_builder: 候補選択・重み算出（等金額・スコア加重）
  - position_sizing: 発注株数算出（risk_based / equal / score）
  - risk_adjustment: apply_sector_cap、calc_regime_multiplier
- kabusys.backtest
  - engine.run_backtest: バックテストループ（データコピー、発注・約定・マーク・シグナル生成）
  - simulator.PortfolioSimulator / DailySnapshot / TradeRecord
  - metrics.calc_metrics: CAGR, Sharpe, MaxDD, WinRate, Payoff 等
  - CLI エントリポイント: python -m kabusys.backtest.run
- その他
  - data.stats 等のユーティリティ（zscore 正規化など）

--------------------------------------------------------------------------------
動作環境 / 必要パッケージ（一例）
- Python 3.10+（型注釈で Union | を使用しているため 3.10 以上を推奨）
- 主要依存パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリで実装されている箇所が多いですが、実行に応じて追加パッケージが必要になる場合があります。
- 実運用では HTTP や DB 関連の追加パッケージ・監視ライブラリ等を導入する想定です。

--------------------------------------------------------------------------------
セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install --upgrade pip
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
   開発時は pip install -e . で編集可能インストールを行うことができます（パッケージ化済みの場合）。

4. 環境変数 (.env) の作成
   プロジェクトルートに .env を配置することで自動読み込みされます（詳細は下記参照）。
   例:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB スキーマ初期化 / DB 準備
   コード中では kabusys.data.schema.init_schema(db_path) を用いてスキーマを初期化・接続することを想定しています。
   （init_schema 実装が別ファイルにあると仮定しているため、事前にスキーマを準備してください）

--------------------------------------------------------------------------------
環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（jquants_client 用）
  - KABU_API_PASSWORD      — kabu ステーション API パスワード（発注実装がある場合）
  - SLACK_BOT_TOKEN        — Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID       — Slack チャンネル ID

- 任意 / デフォルトあり:
  - KABUSYS_ENV            — 実行環境: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL              — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
  - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH            — 監視用 SQLite パス（デフォルト data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

自動 .env 読み込みについて
- プロジェクトルートは __file__ を基点に .git または pyproject.toml を上位ディレクトリで探索して特定します。
- 認識される順序:
  OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。

--------------------------------------------------------------------------------
使い方（主要な例）

1) バックテスト（CLI）
- DB が事前に prices_daily / features / ai_scores / market_regime / market_calendar を含んでいる必要があります。
- 実行例:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb \
    --allocation-method risk_based --lot-size 100

- 出力: コンソールにメトリクス（CAGR, Sharpe, MaxDD, Win Rate 等）を表示

2) Python API で特徴量生成 / シグナル生成
- 簡単な呼び出し例（DuckDB 接続は init_schema を使用）:

  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals
  from datetime import date
  conn = init_schema("path/to/kabusys.duckdb")
  target = date(2024, 01, 31)
  # features を計算して保存
  build_features(conn, target)
  # シグナルを生成して保存
  generate_signals(conn, target)

3) J-Quants からデータ取得・保存（例）
- 日足取得 → DB 保存の例:

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import init_schema
  conn = init_schema("path/to/kabusys.duckdb")
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  save_daily_quotes(conn, records)

4) ニュース収集（RSS）
- 自動トラッキング除去・SSRF 対策済み。例:

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  conn = init_schema("path/to/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 銘柄コードセット（抽出に利用）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

--------------------------------------------------------------------------------
ディレクトリ構成（主要ファイル抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - jquants_client.py
      - news_collector.py
      - (schema.py, calendar_management.py, stats.py などが参照される)
    - research/
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - feature_engineering.py
      - signal_generator.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - backtest/
      - engine.py
      - simulator.py
      - metrics.py
      - run.py
    - execution/ (実行・発注層のプレースホルダ)
    - monitoring/ (監視用コードのプレースホルダ)

（実際のリポジトリでは上記以外にもユーティリティやスキーマ定義が含まれる想定です）

--------------------------------------------------------------------------------
補足 / 注意点
- DuckDB スキーマ初期化関数（kabusys.data.schema.init_schema）は本コード内で参照されています。バックテストや ETL を動かすにはスキーマが正しく存在していることが前提です。
- jquants_client は API レート制限・リトライ・トークン自動更新などを備えています。J-Quants トークンの管理は settings を通じて行います。
- RSS ニュース収集では SSRF や Gzip Bomb、トラッキングパラメータ除去などの対策を実装していますが、運用環境ではさらに堅牢なネットワーク制御を推奨します。
- 実口座での自動売買を行う場合は法令・証券会社の規約・リスク管理を十分に確認してください（本リポジトリは学術/研究目的の実装例です）。

--------------------------------------------------------------------------------
貢献 / ライセンス
- 本 README にライセンスや貢献ルールは含めていません。リポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください。

--------------------------------------------------------------------------------
お問い合わせ
- 実行時の問題やコード理解についての質問があれば、必要なファイル・実行ログ・環境情報（Python バージョン、DuckDB バージョン、実行コマンド）を添えて問い合わせてください。

以上。README の補足・追加項目や例の拡充（実行スクリプト・CI 設定・テスト手順など）が必要であればお知らせください。