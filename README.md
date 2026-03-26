KabuSys
=======

日本株向けの自動売買 / 研究プラットフォームのコードベース（抜粋）。  
バックテスト、特徴量作成、シグナル生成、データ収集（J-Quants / RSS）などの機能を含むモジュール群です。

プロジェクト概要
--------------
KabuSys は以下の機能を持つ Python 製ライブラリ／ツール群です。

- J-Quants API および RSS からのデータ収集（株価、財務、マーケットカレンダー、ニュース）
- DuckDB を用いたデータ管理（ETL → 正規化 → features / signals テーブル）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（ファクター + AI スコアの統合、BUY/SELL 判定）
- ポートフォリオ構築（候補選定、配分、リスク調整、ポジションサイジング）
- バックテストフレームワーク（擬似約定・スリッページ・手数料モデル・評価指標）
- ニュース収集・銘柄紐付け（RSS → raw_news / news_symbols）

主要ターゲットは日本株（単元株 100 株を想定）で、運用フェーズ（development / paper_trading / live）に対応する設定を備えています。

主な機能一覧
-------------
- データ取得・保存
  - J-Quants API クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - DuckDB への冪等保存: save_daily_quotes, save_financial_statements, save_market_calendar
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 上限、トラッキング除去）
  - raw_news / news_symbols への保存（重複排除、チャンク挿入）
- 研究用ファクター計算
  - Momentum / Volatility / Value を DuckDB 上で計算（prices_daily / raw_financials を参照）
  - 研究ユーティリティ: calc_forward_returns, calc_ic, factor_summary
- 特徴量エンジニアリング
  - build_features(conn, target_date): ファクター統合 → Z スコア正規化 → features テーブルへ UPSERT
- シグナル生成
  - generate_signals(conn, target_date, ...): features・ai_scores を統合して BUY/SELL シグナルを signals テーブルへ書込
  - Bear レジーム時の BUY 抑制、エグジット判定（ストップロス等）
- ポートフォリオ構築
  - select_candidates / calc_equal_weights / calc_score_weights
  - apply_sector_cap（セクター集中の上限チェック）
  - calc_position_sizes（risk_based / equal / score のサイジング、単元丸め、aggregate cap）
- バックテスト
  - PortfolioSimulator（擬似約定・履歴記録）
  - run_backtest(conn, start_date, end_date, ...): エンジンループ、シグナル生成→約定→マークトゥーマーケット→サイジングを実行
  - 評価指標計算（CAGR, Sharpe, MaxDD, WinRate, Payoff, TotalTrades）
- 設定管理
  - settings オブジェクト: 環境変数経由の設定取得（必須キーは未設定時に例外）

セットアップ手順
----------------

1. Python 環境（推奨: 3.10+）を用意します。

2. 必要パッケージをインストールします（プロジェクトの requirements.txt があればそれを使用してください）。本コードから想定される代表的な依存は以下です:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```

3. パッケージを開発モードでインストール（任意）:
   ```
   pip install -e .
   ```

4. DuckDB 用 DB ファイルやデータディレクトリを作成します。設定は環境変数で行います（下節参照）。

環境変数（設定）
----------------
Settings は環境変数または .env/.env.local から読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

主な環境変数（必須マークあり）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")、デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO", ...)、デフォルト "INFO"

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

使い方（代表的な例）
-------------------

- バックテストを CLI で実行
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --db path/to/kabusys.duckdb \
    --cash 10000000
  ```
  オプションで slippage, commission, allocation-method, lot-size 等を調整可能。

- プログラムから特徴量を作成
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  ```

- シグナル生成（features + ai_scores を元に signals テーブルへ書込）
  ```python
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date(2024,1,31))
  ```

- J-Quants からデータ取得 & 保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  articles = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  save_daily_quotes(conn, articles)
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  ```

主要モジュールとファイル説明（抜粋）
----------------------------------
- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス（自動 .env ロード、必須チェック）
- src/kabusys/data/jquants_client.py
  - J-Quants API クライアント、レートリミット・リトライ・トークンリフレッシュ、DuckDB 保存ユーティリティ
- src/kabusys/data/news_collector.py
  - RSS 取得、前処理、raw_news / news_symbols への保存、SSRF/サイズ制限対策
- src/kabusys/research/factor_research.py
  - Momentum / Volatility / Value の計算ロジック（prices_daily / raw_financials ベース）
- src/kabusys/strategy/feature_engineering.py
  - build_features: ファクター正規化 → features テーブルへの UPSERT
- src/kabusys/strategy/signal_generator.py
  - generate_signals: final_score 計算、BUY/SELL 判定、signals テーブル更新
- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定、重み計算（equal/score）
  - position_sizing.py: 株数決定（risk_based / equal / score）、aggregate cap、単元丸め
  - risk_adjustment.py: セクター制限、レジーム乗数
- src/kabusys/backtest/
  - engine.py: run_backtest エンジン、バックテストループ
  - simulator.py: PortfolioSimulator（擬似約定、履歴・トレード記録）
  - metrics.py: バックテスト評価指標計算
  - run.py: CLI エントリポイント
- src/kabusys/data/schema.py (参照実装がある想定)
  - init_schema(db_path) で必要テーブルを初期化するユーティリティ（この README のコード内では参照されます）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- data/
  - jquants_client.py
  - news_collector.py
  - schema.py (想定)
  - stats.py (想定: zscore_normalize 等)
  - calendar_management.py (想定: get_trading_days)
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
  - clock.py
- execution/ (空のパッケージ、実運用 API ラッパー等を想定)
- monitoring/ (監視・アラート用モジュールを想定)

開発・運用上の注意
-----------------
- Look-ahead bias（未来情報を学習／使用してしまうバイアス）を防ぐため、各処理は target_date 時点で「システムが知り得る」情報だけを使う設計になっています。バックテストではデータコピーと日付フィルタによる厳密な制御が行われます。
- ニュース収集や外部 API 呼び出しは外部ネットワークに依存するため、タイムアウトやエラー処理を適切に設定してください。
- 設定や機密情報は .env に保存し、git 管理下に置かないでください（.env.local は .env を上書きするローカル専用設定）。
- 実運用（live）で注文実行を組み込む場合は execution 層と kabu API 周りの安全確認（認証・リトライ・エラーハンドリング）を行ってください。

ライセンス・貢献
----------------
この README はコード抜粋に基づく概要ドキュメントです。実際のライセンス情報・コントリビューションガイドはリポジトリルートの LICENSE / CONTRIBUTING を参照してください。

その他
-----
詳細な設計仕様やモデル（StrategyModel.md、PortfolioConstruction.md、BacktestFramework.md、DataPlatform.md 等）はリポジトリ内のドキュメントを参照してください。README に含めていない補助モジュール（data.stats、data.schema など）は本 README の記述と合わせて利用してください。

--- 

必要に応じて README の補足（例: 実行例の詳細、schema 初期化手順、テスト方法）を追加できます。どの情報をさらに充実させたいか教えてください。