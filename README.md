KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買・研究・監視用ライブラリ兼小規模フレームワークです。本コードベースは以下の責務を持ちます。

- 発注・注文管理・リコンシリエーション（ExecutionEngine 周り）
- 監視（System / Trade / Risk）およびアラート送信（LINE）
- Paper Trading（Mock ブローカー）サポートと検証レポート生成
- リサーチ（ファクター計算、特徴量探索）
- ニュースに基づく AI スコアリング（OpenAI を利用）
- 市場レジーム判定（AI + MA200 合成）
- Streamlit ベースの監視ダッシュボード

主な特徴
--------
- 環境変数 / .env による設定管理（自動読み込み：.env, .env.local）
- 本番 / paper_trading / development を区別する KABUSYS_ENV
- DuckDB（時系列データ分析） & SQLite（監視ログ・Orders） を併用
- AI 統合（OpenAI）によるニュースセンチメント評価とレジーム検出
- 監視エンジン（Kill Switch）で基準超過時に ExecutionEngine を停止可能
- Pure 関数群によるポートフォリオ構築、ポジションサイズ計算（テスト容易）
- Streamlit ダッシュボードで監視データの可視化
- Paper Trading 用 DB の分離（data/paper_trading.db がデフォルト）

必要な外部ライブラリ（代表）
--------------------------------
実行環境に合わせてインストールしてください。requirements.txt がある場合はそちらを優先してください。
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード用)

例（pip）
- pip install duckdb psutil requests openai streamlit

設定（環境変数）
----------------
主要な環境変数（省略時は README 内のデフォルトを利用）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出し用 API キー（AI 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt）
4. data ディレクトリを作成（必要なら）
   - mkdir -p data
5. .env（または .env.local）をプロジェクトルートに置く（.env.example を参照して作成）
   - 自動ロード機能はデフォルトで有効（.env, .env.local の優先順）
6. DuckDB / DB スキーマの準備
   - prices_daily / raw_financials / raw_news など、Research / AI が参照するテーブルは外部プロセスで作成してください（DuckDB を直接使う想定）。
   - 監視用 SQLite は起動時に init_monitoring_db によりテーブル作成・マイグレーションが実行されます。

使い方（実行例）
----------------

- 監視ループを起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL を秒で指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するとループが終了します（または Ctrl+C）。

- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、Paper DB（デフォルト data/paper_trading.db）に記録される
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID が書かれ、停止フラグ data/stop_requested.flag によって停止可能

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB に read-only で接続してダッシュボードを表示

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（デフォルト: data/paper_trading.db）

- AI 関連（プログラム的呼び出し）
  - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)
  - OPENAI_API_KEY が必要。関数は DuckDB 接続と target_date（date オブジェクト）を受け取る。

- Research / Factor 計算（例）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(duckdb_conn, target_date)

運用上の注意 / 実装ノート
-------------------------
- Settings（kabusys.config）:
  - .env 自動読み込み: プロジェクトルート判定は .git または pyproject.toml を探します。CWD に依存しない設計。
  - 必須変数は _require() で検出し、未設定時は ValueError を上げます。
- Paper Trading:
  - paper_trading 環境では本番 DB と分離して PAPER_TRADING_SQLITE_PATH を使う（デフォルト data/paper_trading.db）。
  - PAPER_FILL_MODE により MockBroker の挙動を変更できます（instant / partial / never / reject）。
- 監視/停止フラグ:
  - stop_requested.flag（data/stop_requested.flag）: run_monitoring / run_execution がループ停止を検出するためのフラグ
  - kill.flag（設定に応じたパス）: KillSwitch が書き込むことで Execution を停止させる安全シャットダウントリガ
  - PID ファイル: data/execution.pid（ExecutionEngine が書き込む）
- init_monitoring_db() は既存 DB に対して必要なテーブル作成と簡易マイグレーション（カラム追加）を行います（冪等）。
- process priority / CPU affinity:
  - set_process_priority() によりプラットフォーム差を吸収してプロセス優先度を調整します。POSIX で niceness を下げる操作は権限が必要です。
- OpenAI / API エラーハンドリング:
  - AI 呼び出しは 429・ネットワーク・5xx をリトライする実装が含まれています。APIキー未設定時は関数が ValueError を投げます。
- テスト性:
  - 多くのモジュールは副作用を最小化する純粋関数群（portfolio、position_sizing、risk_adjustment、research 等）と、DB に依存する薄い永続化レイヤ（monitoring_db）に分離されています。OpenAI 呼び出しは差し替え可能（テスト用に patch する想定）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 管理
- run_monitoring.py        — SystemMonitor ポーリングループ起動
- run_execution.py         — ExecutionEngine 起動
- data/                    — （外部のデータ格納場所想定）

サブパッケージ（代表）
- kabusys/monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- kabusys/execution/
  - execution_engine.py (実装あり)
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - broker_api.py
- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- kabusys/research/
  - factor_research.py
  - feature_exploration.py
- kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- kabusys/tools/
  - paper_verification_report.py
- kabusys/utils/
  - process_priority.py

（補足）
- 各モジュール内に詳細な docstring と設計方針が記載されています。実運用前に Settings の必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）と DB の初期データ（prices_daily など）を整備してください。
- 本 README はコードベースの主要な使い方と設計上の注意点をまとめたものです。リポジトリ内の各ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）があればそちらも参照してください。

必要であれば、README に記載する環境変数の具体的な .env.example（テンプレ）や、簡単な docker-compose / systemd ユニット定義のサンプルも作成します。どの形式を追加しますか？