KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視用ライブラリ／実行スクリプト群です。  
主要な機能は発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築、ファクター計算、AI ベースのニュース／レジーム判定、および各種ユーティリティを含みます。  
設計方針として「本番 DB とペーパートレードの明確な分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のフォールバック）」を念頭に置いて実装されています。

主な機能一覧
--------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading なら MockBroker を使用し、data/paper_trading.db に記録（本番と完全分離）
  - PID ファイル管理、停止フラグによる安全停止
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム・データ鮮度・取引ログ・リスク監視（ドローダウン、ポジション上限等）
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止
  - 監視結果を SQLite（monitoring.db）へ永続化
- Portfolio（portfolio パッケージ）
  - 候補選定、重み計算、ポジションサイズ算出、セクター上限・レジーム補正等
- Research（research パッケージ）
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリューなど）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（ai パッケージ）
  - ニュース NLP による銘柄センチメント（OpenAI API 使用）
  - マクロニュース + ETF MA による市場レジーム判定（OpenAI API 使用）
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
  - ロギングセットアップ（logs 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

必要条件
--------
- Python 3.10+
- 推奨パッケージ（主な依存）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- SQLite（Python 標準ライブラリで OK）
- ネットワーク接続（OpenAI 呼び出し等を使う場合）

インストール（ローカル開発用）
------------------------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt があればそれを利用してください）

初期設定 (.env)
---------------
KabuSys は環境変数を使用して動作します。プロジェクトルートの .env, .env.local が自動で読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here

主なオプション（デフォルト値）
- KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- LOG_DIR=logs
- OPENAI_API_KEY=（AI 機能を使う場合必須）

.env を対話的に作成する
- python -m kabusys.config_setup
  - ウィザード形式で .env を生成・更新します。

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1) になります。

使い方（実行例）
----------------

1. 監視プロセス起動
- デフォルトでは監視は本番 sqlite_path（SQLITE_PATH）を使用します。
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
- 実行:
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

2. Execution（発注エンジン）起動
- KABUSYS_ENV の値により挙動が変わります:
  - paper_trading: MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録
  - live: 本番ブローカーを使用（KABU API 設定必須）
- 実行:
  - python -m kabusys.run_execution

3. Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

停止・Kill 機構
-------------
- 手動停止（両スクリプト共通）
  - プロジェクトルートの data/stop_requested.flag ファイルを作成すると、run_execution / run_monitoring のループが検知して停止します。
- Kill Switch（自動停止）
  - 監視が条件を満たした場合（ドローダウン超過等）、KillSwitch が data/kill.flag を書き込み ExecutionEngine 側で検知して停止します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ログ
----
- logs/ にアプリ名別ログが日次ローテーションで保存されます（例: logs/execution.log, logs/monitoring.log）。
- ログレベルは環境変数 LOG_LEVEL、LOG_DIR で調整可能。
- setup_logging() ユーティリティは stdout の StreamHandler と TimedRotatingFileHandler（30日分保持）を設定します。

設定オプション・重要な環境変数まとめ
-----------------------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API（必須）
- OPENAI_API_KEY: AI 機能使用時に必須
- DUCKDB_PATH: DuckDB 保存先（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー専用 DB（paper_trading 用）
- PAPER_FILL_MODE:ペーパートレードの約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring にのみ反映）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効）

ディレクトリ構成（主要ファイル）
------------------------------
（リポジトリルート / src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings 管理
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/                   — 発注関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py          — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                       — 実行時生成：データベース、PID、flag ファイル等（例: data/monitoring.db, data/execution.pid, data/kill.flag）

補足・運用上の注意
-----------------
- 開発時は KABUSYS_ENV=development を使用することで本番 API 呼び出しを抑止する想定です。paper_trading は本番 DB を汚さないために専用 DB を使用します。
- OpenAI を使った機能は API 呼び出しの失敗に対してフェイルセーフ（0.0 にフォールバック等）を行いますが、APIキーの管理には注意してください。
- run_execution/run_monitoring は stop_requested.flag を見てループを抜ける仕組みです（安全停止）。永続運用時は systemd / supervisor 等で管理してください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。

トラブルシューティング
---------------------
- .env が読み込まれない場合
  - PROJECT ルート検出は config._find_project_root() により .git または pyproject.toml を基準に行います。
  - 自動読み込みを無効化したい／テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログファイルが作成されない場合
  - LOG_DIR のパス権限を確認してください。作成失敗時はコンソール出力のみになります（setup_logging の挙動）。
- OpenAI 呼び出しエラー
  - OPENAI_API_KEY が正しいか、ネットワーク/レート制限を確認してください。LLM 呼び出しは指数バックオフでリトライします。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__（現状 "0.1.0"）を参照してください。
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

この README はコードベースの主要動作・運用手順をまとめたものです。詳細な設計やアルゴリズム（PortfolioConstruction.md / StrategyModel.md 等参照）や ExecutionEngine の内部実装は対応するドキュメント・ソースコードコメントをご参照ください。