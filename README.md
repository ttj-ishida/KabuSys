README
======

概要
----
KabuSys は日本株向けの自動売買・研究基盤です。  
戦略のファクター計算、ポートフォリオ構築、ポジションサイジング、発注エンジン（ExecutionEngine）、稼働監視（Monitoring）や AI を用いたニュースセンチメント評価など、一連の機能を備えています。  
コードベースはモジュール化されており、ローカル開発／ペーパートレード／本番（live）の各実行モードを想定しています。

主な特徴
--------
- ExecutionEngine：発注ロジック、オーダー管理、リスク管理を統合（paper_trading 環境では MockBroker を使用して本番 DB と分離）
- Monitoring：システム稼働・データ鮮度・取引ログ・リスク監視を定期ポーリングで実行、kill switch による安全停止
- Portfolio モジュール：候補選定、重み算出、ポジションサイズ計算、セクター制限・レジーム乗数
- Research：DuckDB を用いたファクター計算（Momentum / Volatility / Value）・将来リターン・IC 等の分析ユーティリティ
- AI モジュール：OpenAI を利用したニュースセンチメント評価（news_nlp）・市場レジーム判定（regime_detector）
- ユーティリティ：ロギング設定、プロセス優先度／CPU affinity 設定、.env 自動読み込み
- 開発ツール：.env 対話式ウィザード、設定検証 CLI、Paper Trading 検証レポート生成

前提条件（推奨）
----------------
- Python 3.9+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証用）
- OS: Linux / macOS / Windows（process priority の一部機能はプラットフォーム依存）

インストール（例）
-----------------
1. リポジトリを取得し、仮想環境を用意：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt があればそれを使用、なければ個別に）:
   - pip install duckdb psutil openai
   - （開発で YAML 検証を使う場合）pip install pyyaml

環境変数・設定ファイル
--------------------
KabuSys は .env（および .env.local）から環境変数を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（主要）
- JQUANTS_REFRESH_TOKEN：J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API のパスワード

主な任意／設定変数（デフォルト含む）
- KABUSYS_ENV：実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH：Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL：ログレベル（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY：OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE：paper_trading の約定挙動（instant / partial / never / reject）
- LOG_DIR：ログ出力ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START：起動時に kill.flag を自動クリアするか（0/1）

.env の作成（対話式ウィザード）
------------------------------
対話式に .env を作成・更新するには以下を実行します：
- python -m kabusys.config_setup

設定検証
--------
作成後、起動前に設定検証を行うことを推奨します：
- python -m kabusys.validate_config
- 警告も FAIL 扱いにしたい場合:
  - python -m kabusys.validate_config --strict

主要な実行スクリプト（使い方）
-----------------------------

1) 実行エンジン（ExecutionEngine）
- 説明: 発注処理を開始します。KABUSYS_ENV が paper_trading の場合は MockBroker を使用し、データは data/paper_trading.db に記録され本番 DB と分離されます。
- 起動:
  - python -m kabusys.run_execution
- ログ: logs/execution.log（setup_logging による日次ローテート）
- PID ファイル: data/execution.pid（Settings で変更可）
- 停止:
  - data/stop_requested.flag を作成すると run_execution のループは停止処理を行います（スクリプト内部でチェック）。
  - KillSwitch により data/kill.flag が作成されると ExecutionEngine 側で検知して安全停止する仕組みがあります（通常は Monitoring が判定して書き込む）。

2) 監視ループ（Monitoring）
- 説明: SystemMonitor / TradeMonitor / RiskMonitor をポーリングしてログ・アラート・KillSwitch 評価を行います。監視は KABUSYS_ENV に関係なく本番の SQLite（Settings.sqlite_path）を参照します。
- 起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
- 停止:
  - data/stop_requested.flag を作成すると監視ループは終了します（run_monitoring はこのフラグを監視）。
- ログ: logs/monitoring.log

3) Paper Trading 検証レポート
- 説明: data/paper_trading.db から指定期間の稼働率・注文成功率・レイテンシ等を算出してレポートを出力します。
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数: PAPER_TRADING_SQLITE_PATH を使用できます（--db が優先）

4) AI 関連
- ニュースセンチメント評価:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 実行時は OPENAI_API_KEY を環境変数か引数で渡す必要あり
  - 出力は ai_scores テーブルへ書き込み
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に OpenAI API キーが必要

停止／Kill Switch の振る舞い
---------------------------
- stop_requested.flag: run_execution と run_monitoring が監視している停止フラグ。ファイルが存在すると両スクリプトは安全に終了します。
  - 場所: プロジェクト root の data/stop_requested.flag（既定）
- kill.flag: KillSwitch が書き込み、ExecutionEngine 停止をトリガーするために使われるフラグ（Monitoring がリスク等から書き込む）。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨。

ログ・データベース・ファイル配置（デフォルト）
---------------------------------------------
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- ログディレクトリ: logs/
- PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

開発時の注意点・設計メモ
-----------------------
- .env 自動読み込みはプロジェクトルートが見つかった場合にのみ行われ、OS 環境変数は優先されます。
- Settings クラス経由で設定を参照することで、環境による分岐（is_paper / is_live / is_dev）が可能です。
- Monitoring の DB 初期化（init_monitoring_db）は冪等で、既存スキーマに対する軽微なマイグレーション（column 追加）を含みます。
- AI モジュールは API の失敗に対してフェイルセーフ（フォールバック値）を採用しており、部分失敗時でも他データを保持するよう DB 書き込み戦略が工夫されています。
- process_priority は psutil を使いプラットフォーム差を吸収しますが、アクセス権限や OS によって設定が失敗する場合があります（警告ログを出してスキップ）。

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys をルートとした簡易ツリー）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        (実装ファイルがある前提)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        (実装ファイルがある前提)
  - execution/
    - execution_engine.py     (実装ファイルがある前提)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                      — 実行時に作成される想定のディレクトリ（DB / PID / flags）

（実際のファイルは上記以外にも多数あります。ここでは主要モジュールを列挙しています）

よくあるコマンドまとめ
--------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サンプル .env（最小例）
----------------------
（.env は絶対にバージョン管理へコミットしないでください）

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

ライセンス・貢献
----------------
各自のプロジェクト方針に従ってライセンスを追加してください。貢献や改善提案はプルリクエストで歓迎します。

サポート / 問い合わせ
--------------------
この README はコードの概要・起動手順をまとめたものです。個別のモジュールや関数の使い方は各ソースファイルの docstring を参照してください。必要があればモジュールごとの詳細ドキュメントやチュートリアルを追加できます。