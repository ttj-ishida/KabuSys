KabuSys
=======

日本株自動売買システム（KabuSys）のリポジトリ内ドキュメントです。  
この README はコードベース（src/kabusys/ 以下）を前提として、概要・機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめています。

概要
----
KabuSys は日本株向けの自動売買基盤です。  
主な役割は以下のとおりです：

- シグナル生成・ポートフォリオ構築（選定、重み付け、リスク調整、株数算出）
- 発注実行エンジン（本番 / ペーパートレード切替）
- 監視（システム稼働・データ鮮度・取引ログ監視・Kill Switch）
- リサーチ（ファクター算出、特徴量探索）
- ニュース NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定
- ペーパートレードの検証レポート生成ツール

特徴
----
- 明確に分離された Paper Trading と Live（実発注）モード
- DuckDB（分析用） と SQLite（監視／発注ログ）を併用
- OpenAI を使ったニュースセンチメント（オプション）
- Kill Switch / stop フラグによる安全停止
- 簡易な .env ウィザードと設定検証ツール
- 日次ローテートのログ出力（logs/ ディレクトリ）

前提（推奨）
-------------
- Python 3.10 以上（ソースに PEP 604 型注釈などを使用）
- 必要なライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証でオプション）
- 任意で virtualenv / venv を使った仮想環境

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   - 例:
     - git clone <repo>
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストールします。

   - requirements.txt があれば:
     - pip install -r requirements.txt
   - 無ければ最低限:
     - pip install duckdb psutil openai pyyaml

3. .env を作成します（対話ウィザード推奨）。

   - ウィザード:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
   - 主要なオプション / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）

   自動ロード:
   - プロジェクトルートに .env / .env.local がある場合、起動時に自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定を検証します。

   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます。

使い方（起動／ツール）
----------------------

主要なエントリポイントと実行方法:

- ExecutionEngine（売買実行）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、データは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録されます（本番 DB と分離）。
    - 実行中の停止: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して安全停止します。
    - 実行中は pid ファイル（デフォルト: data/execution.pid）を出力します。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60秒）。
    - 監視は常に本番用の sqlite_path を使用（環境にかかわらず）。
    - 停止フラグ: data/stop_requested.flag によりループ終了。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定できます（優先度: --db > env > デフォルト）。

- AI 関連
  - ニュース NLP / レジーム判定機能は OpenAI API キー（OPENAI_API_KEY）を環境変数または関数引数で指定して実行します。
  - OpenAI 呼び出し失敗時はフェイルセーフ（スコアを 0 にするなど）で動作を続けます。

運用上のフラグ / ファイル
------------------------
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py のループ停止用フラグ。ファイルが存在すると安全終了します。
- data/kill.flag
  - KillSwitch（モニタリング側）で書き込まれると ExecutionEngine に停止シグナルを与える目的で使用。場所は Settings.kill_flag_path で変更可能。
- PID ファイル
  - 実行エンジンは execution.pid（デフォルト）に PID を書く仕組みがあります。

デフォルトパス
--------------
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- SQLite (paper_trading): data/paper_trading.db
- ログ: logs/（日次ローテーション、30日保持）
これらは .env で上書き可能です。

注意事項・開発者向けメモ
------------------------
- Paper Trading モードは本番データベースと完全分離する設計です。必ず KABUSYS_ENV を切り替えて動作を確認してください。
- 設定検証ツールは PyYAML がない場合、YAML の検査をスキップします（警告が出ます）。
- logging は kabusys.utils.logging_setup.setup_logging で統一されます。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- プロセス優先度設定は psutil を用いて OS に応じて行います（失敗時は警告を出して継続）。
- DB スキーマの初期化・簡易マイグレーションは kabusys.monitoring.monitoring_db.init_monitoring_db で行います。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py              — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- config_setup.py        — .env 対話式ウィザード
- validate_config.py     — 起動前設定検証 CLI
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — SystemMonitor 起動スクリプト

src/kabusys/ai/
- news_nlp.py            — ニュースの NLP スコアリング（OpenAI 利用）
- regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）

src/kabusys/monitoring/
- monitoring_db.py       — 監視用 SQLite 操作用 API（テーブル作成・CRUD）
- system_monitor.py      — システム・データ鮮度監視
- trade_monitor.py       — （取引監視、ファイル内に実装あり）
- risk_monitor.py        — ドローダウン・ポジション上限チェック
- kill_switch.py         — Kill Switch 制御
- monitoring_engine.py   — 各 Monitor を束ねたポーリングエンジン
- alert_manager.py       — （アラート送信管理: LINE 等）

src/kabusys/execution/
- execution_engine.py    — 発注実行エンジン（セッション管理）
- order_manager.py
- order_repository.py
- reconciler.py
- broker_factory.py
- risk_manager.py

src/kabusys/portfolio/
- portfolio_builder.py   — 候補選定・重み計算
- position_sizing.py     — 株数決定・投下資金スケーリング
- risk_adjustment.py     — セクターキャップ、レジーム乗数

src/kabusys/research/
- factor_research.py     — Momentum / Volatility / Value ファクター計算（DuckDB）
- feature_exploration.py — 将来リターン、IC、統計サマリー等

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成

src/kabusys/utils/
- logging_setup.py       — 共通ログ設定
- process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

ユーティリティ / DB
- data/                  — 実行に必要なファイル（.flag / .pid / DB ファイル）はこの下に置かれることを想定
- logs/                  — ログ（デフォルト）

よくある操作例
---------------
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動（Paper trading モード例）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視ループ起動（ポーリング間隔 30秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止（オンランでの安全停止）:
  - touch data/stop_requested.flag

さらに詳しく
--------------
各モジュールの docstring に設計方針や挙動の詳細が記載されています。実運用前に必ず validate_config により設定を確認し、paper_trading モードで十分に検証してください。OpenAI を利用する機能は API キーとコストに注意して利用してください。

問題・変更提案
----------------
バグや機能改善は issue を作成してください。開発やデプロイに関する質問があれば、このリポジトリ内の各モジュールの docstring を参照してください。