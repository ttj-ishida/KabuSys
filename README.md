# KabuSys

日本株向け自動売買システム（モジュール群）のリポジトリ。  
この README はリポジトリ内のスクリプト／モジュール群の概要、セットアップ、実行方法、ディレクトリ構成を説明します。

---

概要
- KabuSys は自動売買のコアロジック（ポートフォリオ構築、ポジションサイジング、リスク制御）、監視（System / Trade / Risk）、AI 支援（ニュース NLP、レジーム判定）、リサーチ（ファクター計算）などをモジュール化した Python パッケージです。
- DuckDB（分析用）、SQLite（監視・ペーパートレードログ）をデータストアとして使用します。
- 実際の発注は kabuステーション API 経由（本番）またはモック（paper_trading）で分離されます。

主な特徴（機能一覧）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV による本番 / ペーパートレード切替。
  - Paper Trading 時は専用 DB（data/paper_trading.db）に記録。
  - PID ファイル管理、停止フラグ（data/stop_requested.flag）に対応。
- Monitoring（run_monitoring.py）
  - SystemMonitor を定期ポーリングして system_status / trade_logs / risk_logs / dashboard を更新。
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用。
- 設定ウィザード（config_setup.py）
  - 対話式で .env を作成・更新。
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本検証を行い起動前のミスを検出。
- AI モジュール
  - ニュース NLP（news_nlp）で OpenAI を叩き銘柄ごとのスコアを ai_scores に保存。
  - レジーム判定（regime_detector）で市場レジームを決定し market_regime に永続化。
- 研究用モジュール（research）
  - ファクター計算（momentum/value/volatility 等）、将来リターン、IC 計算など。
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、セクター制約適用、ポジションサイズ計算（単元丸め・資金制約対応）。
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

前提 / 必須依存
- Python 3.9+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 任意 / 推奨:
  - PyYAML（config/*.yaml の検証に使用。未インストールでも動作するが検証が省略されます）

例: 開発環境にパッケージを入れる一例
- 仮想環境作成・有効化（任意）
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- インストール（実際の requirements.txt が無い場合は個別に）
  - pip install duckdb psutil openai

環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の fill モード: instant | partial | never | reject、デフォルト: instant）
- OPENAI_API_KEY（AI 機能を利用する場合）
- LOG_LEVEL（DEBUG|INFO|...、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか: 0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、run_monitoring で参照）

注意:
- 自動で .env を読み込む機構があり、プロジェクトルートにある .env / .env.local を環境変数より低い優先度で読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env は絶対に Git にコミットしないでください。

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境（任意）作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
     - （AI/検証機能を使わない場合は openai / PyYAML は不要）
4. .env を作成
   - python -m kabusys.config_setup
   - あるいは手動で .env を作成（下記のサンプル参照）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
6. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

簡易 .env サンプル（.env.example を参考に作成）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant
- OPENAI_API_KEY=sk-...
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

使い方（主要スクリプト）
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に取引ログを記録します（本番 DB とは分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成することで行えます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（settings.sqlite_path）に対して動作します（環境にかかわらず本番 sqlite_path を使用）。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数を優先）。

- AI モジュール（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡してニュースのスコアリングを実行し ai_scores テーブルへ書き込みます。
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定を実行し market_regime テーブルへ書き込みます。

停止・Kill Switch / フラグ
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py の外部停止（起動・ループ停止）に使用されるフラグファイル。存在を検知すると安全に停止します。
- data/kill.flag
  - KillSwitch によって書き込まれるファイル。ExecutionEngine に対する停止シグナルとして利用可能（Kill Switch はリスクアラート等により評価される）。
- PID ファイル
  - data/execution.pid（ExecutionEngine が書き込むデフォルト例）

ログ
- ロギングは kabusys.utils.logging_setup.setup_logging で統一管理されます。
- デフォルト出力先:
  - stdout（StreamHandler）
  - logs/<app_name>.log（日次ローテートで 30 日保持、ファイル出力に失敗した場合はコンソールのみ）

開発者向け注意点 / 実装メモ
- Settings クラス（kabusys.config）で環境変数の参照・検証を集中管理しています。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Monitoring の初期化は init_monitoring_db() でテーブル／マイグレーションを冪等的に行います。
- Paper Trading は本番 DB から完全に分離されるよう設計されています（settings.paper_sqlite_path を使用）。
- AI 呼び出しは OpenAI SDK をラップしており、429 やネットワーク断、タイムアウト、5xx は指数バックオフでリトライする設計です。API キー管理に注意してください。

ディレクトリ構成（主なファイル／モジュール）
- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動読み込み
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルあり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装ファイルがある想定)
  - execution/                — Execution に関する実装（Engine, OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に作成されることが多い)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - stop_requested.flag, execution.pid, kill.flag など

補足（トラブルシューティング）
- run_execution がすぐ終了する／起動しない:
  - data/stop_requested.flag が存在しないか確認してください。
  - .env の KABUSYS_ENV, KABU_API_PASSWORD 等が正しく設定されているか validate_config で確認してください。
- Monitoring がログを書き込まない:
  - MONITOR_POLL_INTERVAL を短くして手動で run_once を試す（MonitoringEngine.run_once をテストで呼び出す）。
- AI 機能が動作しない:
  - OPENAI_API_KEY の設定と OpenAI SDK のインストールを確認してください。API 使用量に注意してください。

ライセンス / バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）。

最後に
- この README はコードベースから抽出した情報に基づく概要ドキュメントです。実運用前に必ず .env の中身と config/*.yaml を確認し、validate_config を実行してください。開発時はデバッグログ（LOG_LEVEL=DEBUG）を利用すると内部処理が追いやすいです。

必要であれば README にサンプル .env.example ファイルの全文や、systemd / supervisor ユニットファイルのテンプレート、より詳細な運用手順（バックアップや DB スキーマ変更手順）などを追記します。どの情報が欲しいか教えてください。