# KabuSys

日本株向け自動売買システムの Python パッケージ。バックテスト／運用補助・監視・発注・AI 支援などのコンポーネント群を提供します。

## 概要

KabuSys は次のような機能を備えた自動売買基盤のライブラリ兼実行環境です。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 発注後のリコンシリエーション（Reconciler）
- 監視基盤（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE Push）
- 監視ダッシュボード（Streamlit）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- ポートフォリオ構築・銘柄選定・ポジションサイズ計算（純粋関数）
- ファクター計算・特徴量解析（Research）
- ニュース NLP / 市場レジーム検出（OpenAI を利用した AI モジュール）
- ユーティリティ（プロセス優先度設定、設定読み込みなど）

このリポジトリはライブラリとしても、スクリプト（モジュール）を直接実行することでも利用できます。

## 主な機能一覧

- 監視（Monitoring）
  - システムリソース・プロセス監視（SystemMonitor）
  - 注文滞留 / 約定異常の検出（TradeMonitor）
  - ドローダウン / ポジション上限監視（RiskMonitor）
  - Kill Switch（flag ファイルで ExecutionEngine 停止指示）
  - LINE による一方向プッシュ通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード

- 実行（Execution）
  - 発注ワークフロー（OrderManager / ExecutionEngine）
  - ブローカ抽象化（BrokerClientFactory）
  - リコンシリエーション（Reconciler）

- Paper Trading
  - KABUSYS_ENV=paper_trading で MockBroker を使用し、本番 DB と分離された data/paper_trading.db を利用
  - 検証レポート生成スクリプト（tools.paper_verification_report）

- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算（等配分・スコア配分）
  - セクター制限、レジーム乗数、株数決定（単元株丸め・aggregate cap）

- リサーチ（research）
  - ファクター（momentum / volatility / value）計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ai）
  - ニュース記事を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書込み
  - マクロニュース + ETF MA200 乖離を合成した市場レジーム判定（score_regime）

## 前提条件

- Python 3.10+
- OS: Linux / macOS / Windows（ただし一部機能はプラットフォーム依存）
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（Python 標準ライブラリで利用可能）

※ requirements.txt は本リポジトリに含まれていない場合があるため、上記モジュールを手動でインストールしてください。

例:
pip install duckdb psutil requests openai streamlit

## セットアップ手順

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb psutil requests openai streamlit

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は保護）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（運用・一部機能で必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API を使う場合
- KABU_API_PASSWORD — kabuステーション API を使う場合

AI 機能を使う場合:
- OPENAI_API_KEY — OpenAI API キー（score_news, score_regime）

LINE 通知を使う場合（任意）:
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID

主な設定項目（デフォルト値は Settings クラスで定義）:
- KABUSYS_ENV: development | paper_trading | live  (default: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- PAPER_FILL_MODE: instant | partial | never | reject  (default: instant)
- LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, etc.

## 使い方

ここでは代表的な実行例を示します。モジュールはパッケージモードで実行できます。

- 監視ループを起動（Monitoring）
  - 環境変数でポーリング間隔を制御できます: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
  - 注意:
    - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番用 monitoring DB）を使用します。
    - プロセス優先度を high に設定します（psutil の権限で無視される場合あり）。

- 実行エンジンを起動（Execution）
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution
  - 起動時に pid ファイル（デフォルト data/execution.pid）を書きます。kill.flag（data/kill.flag）による停止機構を持っています。

- 監視ダッシュボード（Streamlit）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB を開きます。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプション --db PATH で DB を直接指定できます。

- AI スコアリング（ニュース）
  - ライブラリ API を直接呼ぶ:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - 実行時の注意:
    - OpenAI API のレート制限 / タイムアウト / 5xx はリトライ（指数バックオフ）しますが、最終的に失敗した場合はスキップして継続するフェイルセーフ設計です。
    - 処理後は ai_scores テーブルに書き込みます（部分成功時の破壊最小化を考慮）。

- 市場レジーム判定（AI + MA200）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

- 直接ライブラリを使った開発・テスト
  - 各モジュールは純粋関数（portfolio、research など）として呼べます。DuckDB 接続や SQLite 接続を渡して利用します。
  - 例:
    - import duckdb
    - from kabusys.research import calc_momentum
    - conn = duckdb.connect("data/kabusys.duckdb")
    - calc_momentum(conn, date(2026, 4, 10))

## 重要な挙動（設計上のポイント）

- .env 自動読み込み
  - Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。OS 環境変数は保護されます。
  - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- KABUSYS_ENV の動作差
  - development: 通常モード（デフォルト）
  - paper_trading: MockBroker を使用・発注記録は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に保存し本番 DB から分離
  - live: 本番モード

- Monitoring DB
  - monitoring 用の SQLite は monitoring_db.init_monitoring_db() により冪等にテーブルを初期化・マイグレーションします。
  - run_monitoring は常に Settings.sqlite_path を使う点に注意（環境に依らず監視データは本番パスへ）。

- Kill Switch
  - risk 条件（ドローダウン・ポジション上限）を満たすと kill.flag を書き込み、ExecutionEngine はこのファイルの存在で停止します。flag の既存チェックは冪等です。

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py（パッケージ定義、バージョン）
  - config.py（環境変数 / Settings）
  - run_monitoring.py（監視ポーリングループの起動スクリプト）
  - run_execution.py（ExecutionEngine 起動スクリプト）
  - tools/
    - paper_verification_report.py（Paper Trading 検証レポート CLI）
  - monitoring/
    - monitoring_db.py（SQLite ベースの永続化層）
    - system_monitor.py（システム状態・データ鮮度監視）
    - trade_monitor.py（注文滞留・約定異常監視）
    - risk_monitor.py（ドローダウン・ポジション数監視）
    - kill_switch.py（kill.flag 管理）
    - alert_manager.py（LINE 通知ラッパー）
    - monitoring_engine.py（Monitors を束ねるエンジン）
    - streamlit_dashboard.py（監視ダッシュボード）
  - execution/
    - order_manager.py（OrderManager）
    - reconciler.py（リコンシリエーション）
    - ...（ブローカー関連、OrderRepository 等）
  - portfolio/
    - portfolio_builder.py（候補選定、重み計算）
    - position_sizing.py（株数算出・aggregate cap）
    - risk_adjustment.py（セクター上限・レジーム乗数）
  - research/
    - factor_research.py（momentum/volatility/value）
    - feature_exploration.py（将来リターン・IC・統計）
  - ai/
    - news_nlp.py（ニュース NLP スコアリング）
    - regime_detector.py（市場レジーム判定）
  - data/ (想定データフォルダ)
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)
    - execution.pid, kill.flag など

（注）実際のリポジトリ内のファイル群に基づいた要約です。詳細は各モジュールの docstring を参照してください。

## 開発・デバッグのヒント

- 単体での監視実行（テスト目的）
  - MonitoringEngine を直接組み立てて run_once() を呼ぶことで 1 回だけのチェックを実行できます（テスト用途に便利）。
- DuckDB はファイル接続でもメモリ接続でも使えます。research モジュールは DuckDB 接続を受け取る設計なのでテスト用に小さな DB を作って試せます。
- OpenAI 呼び出しは外部依存（ネットワーク）なので、unittest.mock.patch で _call_openai_api を差し替えてユニットテストしやすく設計されています。

## ライセンス / 貢献

本 README はプロジェクト内のコードからの情報に基づいて作成されています。実際に運用する際は各所の TODO やログ記述、エラー処理の意図を理解した上で利用・改良してください。

貢献やバグ報告は Issue / PR を通じて受け付けてください。

---

必要があれば README の英語版や各機能（Monitoring、Execution、AI）の詳細な使い方ドキュメントを追加します。どのセクションを詳しくしたいか教えてください。