KabuSys — 日本株自動売買フレームワーク
======================================

概要
----
KabuSys は日本株向けの自動売買／研究／バックテスト用ライブラリです。  
モジュールはデータ取得（J-Quants 等）、ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、ポジションサイジング、バックテストシミュレータ、ニュース収集などに分かれており、研究（Research）→シグナル生成（Strategy）→実運用/実行（Execution）へと繋がる一連のパイプラインを想定しています。

主な設計方針
- DuckDB をデータストアとして利用（インメモリ/ファイル両対応）
- ルックアヘッドバイアス防止のため「取得時刻/fetched_at」を記録して ETL を設計
- 冪等性（INSERT ... ON CONFLICT）やトランザクションを意識した実装
- ネットワーク処理でのリトライやレート制限、SSRF 対策など安全性を考慮

主な機能
---------
- データ取得・保存
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
- ニュース収集
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出・紐付け（run_news_collection 等）
  - SSRF 対策・受信サイズ制限・XML パース安全化（defusedxml）
- 研究用モジュール
  - ファクター計算（momentum / volatility / value）
  - ファクター探索（forward returns / IC / summary）
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング
  - research 結果の正規化・ユニバースフィルタ適用・features テーブルへの書き込み（build_features）
- シグナル生成
  - features / ai_scores を統合して final_score を計算、BUY/SELL の判定と signals テーブルへの書き込み（generate_signals）
  - Bear レジーム抑制、SELL 優先のポリシー、エグジット条件（ストップロス等）実装
- ポートフォリオ構築
  - 候補選定（select_candidates）、等分配・スコア加重配分（calc_equal_weights / calc_score_weights）
  - リスク調整（セクター上限適用 apply_sector_cap、レジーム乗数 calc_regime_multiplier）
  - ポジションサイジング（calc_position_sizes） — risk_based / equal / score に対応、単元丸め・aggregate cap 等を考慮
- バックテストフレームワーク
  - ポートフォリオシミュレータ（PortfolioSimulator）
  - バックテストエンジン（run_backtest）: DB をコピーしてインメモリで安全に実行、スリッページ・手数料モデルを考慮
  - メトリクス計算（CAGR / Sharpe / MaxDD / WinRate / PayoffRatio）
  - CLI エントリ（python -m kabusys.backtest.run）
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）、必須設定のラッピング（kabusys.config.settings）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード抑止可能

セットアップ手順
----------------
前提
- Python 3.10 以上（| 型ヒント等を使用）
- システムに DuckDB の動作環境があること

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - 最低限の依存（明示的な requirements.txt が無い場合の例）:
     - pip install duckdb defusedxml
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数（.env）を準備
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化可）。
   - 主要な環境変数例:
     - JQUANTS_REFRESH_TOKEN=...   # J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD=...      # kabu ステーション API パスワード（実運用時）
     - KABU_API_BASE_URL=...      # kabu API のベース URL（デフォルトは http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN=...        # Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID=...       # Slack チャンネル ID（必須）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

5. データベーススキーマの初期化
   - 本プロジェクトでは kabusys.data.schema.init_schema(...) を使って DuckDB スキーマ初期化を行う想定です（schema モジュール参照）。
   - バックテストや本番実行前に prices_daily / features / ai_scores / market_regime / market_calendar 等のテーブルを用意してください。

使い方（代表例）
----------------

1) バックテスト（CLI）
   - DB ファイルが事前に必要（prices_daily, features, ai_scores, market_regime, market_calendar を含む）。
   - 実行例:
     - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
   - オプション:
     - --cash, --slippage, --commission, --allocation-method 等を指定可。
   - 出力: 標準出力にバックテスト指標（CAGR, Sharpe 等）を表示。

2) 特徴量構築（プログラム的に）
   - 例:
     - from kabusys.strategy.feature_engineering import build_features
     - conn = init_schema("path/to/kabusys.duckdb")  # schema モジュール経由で接続を作成する想定
     - build_features(conn, target_date=date(2024, 1, 31))
   - build_features は features テーブルへ日付単位で置換（冪等）で書き込みます。

3) シグナル生成（プログラム的に）
   - from kabusys.strategy.signal_generator import generate_signals
   - generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)

4) データ取得 → 保存（J-Quants）
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   - records = fetch_daily_quotes(date_from=..., date_to=...)
   - save_daily_quotes(conn, records)

5) ニュース収集ジョブ
   - from kabusys.data.news_collector import run_news_collection
   - results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
   - run_news_collection は各 RSS ソースの取得 → raw_news への保存 → 銘柄紐付けを一括で行います。

注意点
- run_backtest を含む多くの処理は DuckDB の所定のテーブル（prices_daily / features / ai_scores / signals / positions / market_regime / stocks / market_calendar 等）を参照します。バックテストやシグナル生成に利用する DB は事前に必要なデータを投入しておく必要があります。
- 環境依存の設定は kabusys.config.settings でラップされています。必須項目が不足すると例外が発生します。

ディレクトリ構成（概要）
----------------------
（ソースは src/kabusys 配下）

- kabusys/
  - __init__.py                         : パッケージ定義（version 等）
  - config.py                           : 環境変数・.env 自動ロード、Settings クラス
  - data/
    - jquants_client.py                 : J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py                 : RSS 取得・前処理・raw_news 保存、銘柄抽出
    - ...（schema, calendar_management 等が別途存在する想定）
  - research/
    - factor_research.py                : momentum/volatility/value ファクター計算
    - feature_exploration.py            : IC・forward returns・統計サマリー
  - strategy/
    - feature_engineering.py            : features の構築（正規化・ユニバースフィルタ）
    - signal_generator.py               : final_score 計算・買い/売りシグナル生成
  - portfolio/
    - portfolio_builder.py              : 候補選定・重み計算
    - position_sizing.py                : 株数決定・aggregate cap・単元丸め
    - risk_adjustment.py                 : セクター上限・レジーム乗数
  - backtest/
    - engine.py                         : run_backtest（バックテスト全体ループ）
    - simulator.py                      : ポートフォリオシミュレータ（約定/時価評価）
    - metrics.py                        : バックテスト評価指標計算
    - run.py                            : CLI ランナー
    - ...clock.py
  - portfolio/, execution/, monitoring/などの他モジュール（execution は空の __init__ が存在）

補足
----
- 本 README はコードベースの実装に基づく概要ドキュメントです。実行に必要な詳細なスキーマ定義（tables/columns）、追加の外部依存、運用手順（ETL スケジューラ、Slack 通知設定、kabu ステーション連携等）は別途ドキュメント（schema 定義ファイル・運用マニュアル）を参照してください。
- .env 読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して行います。テスト等で自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ライセンス / 貢献
----------------
- このリポジトリのライセンスやコントリビュート方法については本プロジェクトの LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。

お問い合わせ
----------
- 実装に関する質問や修正提案は Issue / PR を送ってください。README の改善提案も歓迎します。