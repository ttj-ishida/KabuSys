README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python コードベースです。  
このリポジトリには、発注実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築・リスク制御ロジック、リサーチ用ファクター計算、AI（OpenAI）を用いたニュースセンチメント評価などの主要機能が含まれます。

主な設計方針・特徴
- 実行環境（development / paper_trading / live）を .env で切り替え可能
- Paper Trading モードは本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用 DB、SQLite を監視／トレードログ用 DB として利用
- OpenAI を使ったニュース NLP / レジーム判定機能を含む（API キー必須）
- ロギングは共通ユーティリティで日次ローテーション（logs/*.log）
- Kill Switch / flag ファイルによる外部停止（安全機構）

機能一覧
---------
主要機能（抜粋）:
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録
  - プロセス優先度を「high」に設定して実行
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視・アラート評価
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - Monitoring は環境に関わらず production sqlite_path を使用
- 設定ウィザード（config_setup.py）
  - 対話式に .env を作成・更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本的な整合性チェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB を解析して稼働率、注文成功率、レイテンシなどを出力
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限適用、レジーム乗数
- 研究用モジュール（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）や IC / 統計サマリー
- AI モジュール（ai パッケージ）
  - ニュースのセンチメントスコアリング、マクロレジーム判定（OpenAI）

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.9+（本プロジェクトの型注釈に合わせてください）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 主な外部依存: duckdb, psutil, openai, pyyaml（validate_config の YAML 検証用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   注: 実プロジェクトでは requirements.txt または poetry/poetry.lock による管理を想定します。存在しない場合は上記を参考に必要ライブラリを追加してください。

3. データディレクトリ作成
   - デフォルトでは data/ 以下に DB・フラグが格納されます。必要に応じて作成:
     - mkdir -p data logs

4. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な任意/設定項目（デフォルト値を示す）:
     - KABUSYS_ENV=development | paper_trading | live  (default: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY (AI 機能を使う場合に必須)
     - MONITOR_POLL_INTERVAL (run_monitoring 用; デフォルト 60 秒)
     - KILL_FLAG_CLEAR_ON_START=0（本番では 0 推奨）

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付ける

基本的な使い方
--------------
起動スクリプト・ツールの例:

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用。
    - 起動時に data/stop_requested.flag があれば起動せず終了。
    - 実行中は data/execution.pid（デフォルト）を書き込む。

- Monitoring 起動
  - MONITOR_POLL_INTERVAL を指定して起動（省略時は 60 秒）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依存せず本番 DB で監視）。

- 設定ウィザード（.env 編集）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit code 1

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・フラグの扱い
- 停止フラグ（run_* スクリプトで使用）
  - data/stop_requested.flag を作成すると、run_execution/run_monitoring 内のループが検知して安全に停止します。
- Kill Switch（監視 → ExecutionEngine 停止）
  - 監視側の KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与える仕組みを持ちます（Settings.kill_flag_path 経由で取得）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアを防ぐ）。

ロギング
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定
  - ログファイル: <LOG_DIR>/<app_name>.log（デフォルト logs/）
  - 例: setup_logging(app_name="execution")

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — Monitoring が常に使用
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用
- OPENAI_API_KEY — AI 機能（news_nlp, regime_detector）を使用する場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で削除するか（0/1）

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - Monitoring ポーリング起動スクリプト

パッケージ（機能別）
- ai/
  - news_nlp.py        — ニュース NLP（OpenAI）による銘柄別センチメント
  - regime_detector.py — マクロ + ma200 で市場レジーム判定
- monitoring/
  - monitoring_db.py   — SQLite テーブル定義・永続化 API
  - system_monitor.py
  - trade_monitor.py (未表示があるが存在想定)
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py (参照はあるがファイルはコードベースに依存)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- data/（実行時生成想定）
  - monitoring.db (default)
  - paper_trading.db (paper_trading の場合)
  - kill.flag, stop_requested.flag, execution.pid などのフラグ・PID ファイル
- logs/（ロギング出力先）

開発時のヒント
---------------
- 自動で .env を読み込む: config.py はプロジェクトルート（.git または pyproject.toml を検知）を基準に .env を自動ロードします。テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading の分離: paper_trading モードでは MockBroker を用い、paper_trading 専用 SQLite に記録されます。実データと混ざりません。
- OpenAI 呼び出し部分はリトライ・バックオフや部分書き込み保護などの安全策を持っていますが、API キーやネットワークに依存するため本番環境では注意してください。

ライセンス・バージョン
--------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ で管理（現状 "0.1.0"）。

サポート
-------
コードの各モジュールは docstring とコメントで設計意図・注意点を多く記載しています。まずは:
- python -m kabusys.config_setup で .env 作成
- python -m kabusys.validate_config で簡易チェック
- ローカルで paper_trading モードを試す場合は KABUSYS_ENV=paper_trading を設定してから python -m kabusys.run_execution を実行

不明点があれば、どのコマンドや機能について詳しく知りたいか教えてください。README の補足（例: 実行例、依存パッケージの pin など）を追加します。