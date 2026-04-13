KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買 / 研究 / 監視機能をまとめた軽量フレームワークです。  
本READMEはコードベース（src/kabusys 以下）を元に、、導入・実行に必要な情報を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は次のような機能を持つモジュール群で構成されています。

- 注文管理・発注（Execution Engine、OrderManager、Reconciler 等）
- ポートフォリオ構築（候補選定・重み付け、ポジションサイズ計算、セクター制約など）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、監視DB、アラート）
- 研究用コンポーネント（ファクター計算・特徴量解析）
- AI 活用モジュール（ニュースのセンチメント付与、レジーム判定 — OpenAI を利用）
- ユーティリティ（プロセス優先度 / CPU affinity、.env 自動読み込み等）
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

主要な設計方針：
- データベースは主に SQLite（監視ログ・paper trading 用）と DuckDB（時系列市場データ・研究用）。
- 環境変数 / .env で設定を管理（src/kabusys/config.py）。
- 本番と paper_trading は DB を分離（paper_trading は data/paper_trading.db を使う想定）。
- AI 系は OpenAI API（gpt-4o-mini）を利用。APIキーが必須。

機能一覧
--------
主な機能（モジュール名）と役割：

- execution/
  - OrderManager, Reconciler, ExecutionEngine（発注ロジック・リコン）
- portfolio/
  - 候補選定(select_candidates)、重み計算(calc_equal_weights/calc_score_weights)
  - position sizing（calc_position_sizes）、セクター制約適用(apply_sector_cap)
- monitoring/
  - SystemMonitor（CPU/メモリ/DISK、データ鮮度、PID チェック）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン / ポジション上限監視）
  - KillSwitch（フラグファイルで ExecutionEngine を停止）
  - AlertManager（LINE への通知）
  - MonitoringDB（監視ログの永続化）
  - MonitoringEngine（監視モジュールを束ねたポーリング）
  - Streamlit ダッシュボード（監視データの可視化）
- research/
  - ファクター計算(calc_momentum, calc_volatility, calc_value)
  - 特徴量解析（forward returns, IC 計算, summary）
- ai/
  - news_nlp（raw_news を LLM でスコアリングして ai_scores に保存）
  - regime_detector（MA200 とマクロニュースを用いた市場レジーム判定）
- tools/
  - paper_verification_report（paper_trading DB を解析して PASS/FAIL レポートを出力）

動作要件（想定）
----------------
- Python 3.10 以上（タイプヒントに「|」表記を使用しているため）
- 必要な外部パッケージ（最低限の一覧）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- 標準ライブラリ: sqlite3 等

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化する（例: venv / pyenv / poetry など）。
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストールする（requirements.txt があればそちら）。無ければ最低限：
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリを作成：
   - mkdir -p data

4. 環境変数の設定：
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時は必須）
     - KABUSYS_ENV: 起動環境（development | paper_trading | live） — デフォルト: development
     - PAPER_TRADING_SQLITE_PATH: paper_trading DB パス（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
   - .env/.env.local をプロジェクトルートに置くと自動的に読み込まれます（src/kabusys/config.py が .git または pyproject.toml を基準にプロジェクトルートを探索して読み込み）。
   - 自動読み込みを無効化する場合：
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. （任意）Paper Trading 用の初期 DB を用意する場合は、該当スクリプトや別途用意したデータ投入手順に従って下さい。

主要な環境変数（要点）
-------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading のとき、run_execution は paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使う。
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。デフォルト 60。1 未満や不正な値は無視されデフォルトを使う。
- PID_FILE_PATH: ExecutionEngine が書き込む PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト data/kill.flag）
- PAPER_FILL_MODE: paper_trading の MockBrokerClient の約定挙動（instant | partial | never | reject）
- OPENAI_API_KEY: AI モジュール利用時に必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）利用時

使い方（主要コマンド）
--------------------

- 監視ループ起動（SystemMonitor 単体版）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL= を上書きできます（例: export MONITOR_POLL_INTERVAL=30）
    - 起動時にプロセス優先度を "high" に設定します（psutil による設定。権限により失敗することがありますが警告扱いで続行します）。
    - 監視は .env にかかわらず monitoring 用 DB は sqlite_path（デフォルト data/monitoring.db）を使用します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）。
    - 実行前に必要な認証情報（KABU_API_PASSWORD 等）を設定してください。

- Streamlit ダッシュボード（監視データ閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 補足:
    - デフォルトで読み取り専用で DB を開きます。MonitoringEngine が記録を行っている必要があります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 補足:
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH を参照可能）。

- AI モジュール呼び出し（ライブラリ API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して前日15:00〜当日08:30 JST のニュースを集約し OpenAI で評価、ai_scores テーブルへ書き込みます。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続を渡して MA200 + マクロニュースを組み合わせたレジーム判定を market_regime テーブルへ書き込みます。
  - どちらも api_key を省略すると環境変数 OPENAI_API_KEY を参照します。

運用上の注意
------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。配布後も CWD に依存せず動作する設計です。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ExecutionEngine の停止には KillSwitch（data/kill.flag）を使用します。KillSwitch は RiskMonitor の評価結果によりフラグを書き込みます。
- PID ファイルの stale 検出機能があり、存在する PID が死んでいる場合は削除されアラートを記録します。
- OpenAI API の呼び出しはレートリミットや一時的な接続障害に対して指数バックオフでリトライする実装が含まれます。ただし API キー漏洩には注意してください。
- paper_trading モードは本番 DB と完全に分離されるため、検証・ローカルテストに利用可能です。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py — 環境変数 / .env の読み込み・Settings
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

- execution/
  - broker_factory, broker_api, execution_engine, order_manager, order_repository, reconciler, risk_manager, ...（発注・リコン関連）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, kill_switch.py, alert_manager.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- tools/
  - paper_verification_report.py

data/（実行時に生成・利用するデフォルトファイル）
- data/kabusys.duckdb (DuckDB)
- data/monitoring.db (監視用 SQLite)
- data/paper_trading.db (paper_trading 用 SQLite)
- data/execution.pid (PID ファイル)
- data/kill.flag (KillSwitch フラグ)

開発者向けメモ
---------------
- 型アノテーション、pure function 設計（portfolio 等）でユニットテストが書きやすい構成になっています。
- DuckDB は大規模時系列クエリの速度が速く、research モジュールは SQL と Python の組合せでファクターを算出します。
- OpenAI 呼び出し部分はテスト時に差し替え可能（各モジュールで _call_openai_api を patch する想定）。

最後に
------
この README はコードから主要ポイントを抜粋してまとめたものです。実際の運用前には .env.example（存在する場合）を確認し、環境変数を適切に設定のうえ、ローカルで動作確認（paper_trading モード）を行ってください。必要があれば README をプロジェクト固有の運用手順に合わせて追記してください。