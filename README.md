# KabuSys

日本株自動売買システムの軽量実装リポジトリ（ライブラリ + 起動スクリプト群）

この README はリポジトリ内の主要なモジュール・起動スクリプトをもとに作成しています。実行前に必ず .env を作成し、設定を検証してください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- 停止 / Kill スイッチの仕組み
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
  主な要素は発注エンジン（ExecutionEngine）、監視/アラート（Monitoring）、ポートフォリオ構築、ファクター計算（research）、ニュースを使った AI スコアリング（ai）などです。
- 設計方針の例：
  - 本番 DB / ペーパートレード DB の分離
  - DuckDB を用いたリサーチ／ファクター計算
  - OpenAI を使ったニュースセンチメント評価（任意）
  - `.env` による設定管理と対話式ウィザード / 検証ツールの提供

---

機能一覧（主要）
- 起動スクリプト
  - run_execution.py — ExecutionEngine（発注エンジン）を起動
  - run_monitoring.py — SystemMonitor のポーリングループを起動
- 設定関連
  - config_setup.py — .env の対話式ウィザード
  - validate_config.py — .env / config/*.yaml の起動前検証
- 監視
  - monitoring/monitoring_db.py — 監視用 SQLite スキーマ / 永続化層
  - monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py
  - kill_switch.py — 監視から ExecutionEngine を停止させる Kill Switch
- 発注
  - execution/* — Broker クライアント生成、OrderManager、ExecutionEngine、リコンシリエーション、リスク管理等（コードベースに依存）
  - Paper Trading 時は MockBrokerClient を使用し DB を分離
- ポートフォリオ構築（純粋関数群）
  - portfolio/*.py — 候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数
- 研究・ファクター計算
  - research/* — momentum / volatility / value 等のファクター計算、IC 等の統計解析
- AI/ニュース
  - ai/news_nlp.py — ニュースをまとめて OpenAI に投げ、銘柄ごとのスコアを ai_scores テーブルに書き込み
  - ai/regime_detector.py — ma200 とマクロニュースを合成して market_regime を判定
- ユーティリティ
  - utils/logging_setup.py — ログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定

---

セットアップ手順（ローカル開発向け）
1. Python 環境を準備
   - 推奨: Python 3.9+（プロジェクトの pyproject.toml を確認してください）
   - 仮想環境を作成して有効化（例: python -m venv .venv && source .venv/bin/activate）

2. 依存パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai （AI 機能を使う場合）
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （本リポジトリでは requirements.txt がない場合があります。実行時に ImportError が出たら足りないパッケージを追加してください。）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - ウィザードを使わない場合はプロジェクトルートに .env を置く（.env.example を参照のこと）。

   注意: config モジュールは自動的にプロジェクトルートの .env / .env.local を読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ / SQLite / DuckDB の初期化
   - 多くの DB スキーマは実行時に自動で作成・マイグレーションされます（monitoring の init_monitoring_db 等）。
   - デフォルト DB パスは .env に記載がない場合 data/ 以下に作られます。

---

使い方（主要コマンド）
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - exit code: 0=OK, 1=FAIL

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（デフォルト 60 秒）。無効な値を指定した場合は 60 秒にフォールバックします。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します（.env の SQLITE_PATH を参照）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 明示指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

---

主要な環境変数（抜粋・主要項目）
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）

- データベース / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch が書き込むフラグパス（デフォルト data/kill.flag）

- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
  - LOG_DIR — ログディレクトリ（デフォルト logs/）

- AI
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector で使用）

- その他
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"0" / "1"、本番では "0" 推奨）
  - PAPER_FILL_MODE — Paper Trading の約定動作（instant / partial / never / reject、デフォルト "instant"）

注意: config モジュールはプロジェクトルートの .env / .env.local を自動読み込みします（OS 環境変数が優先）。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

停止 / Kill スイッチの仕組み
- run_execution / run_monitoring は data/stop_requested.flag の存在を定期的にチェックし、存在する場合は安全にシャットダウンします（運用上の停止フラグ）。
- KillSwitch（監視側）:
  - リスク条件（ドローダウン超過やポジション上限超過）を検出した場合、data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は起動時に kill.flag を検出する設定（KILL_FLAG_CLEAR_ON_START）により挙動が変わります。production では自動クリアをオフにすることを推奨します。
- 手動停止:
  - data/stop_requested.flag を作成すると monitoring/execution のループが終了します。
  - data/kill.flag を作成すると ExecutionEngine が停止するロジックが入っています（監視からの自動書き込みと同等の扱い）。

---

ログ・DB のデフォルトパス
- ログ: logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション、30 日分保持）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

ディレクトリ構成（src/kabusys ベース、抜粋）
- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - execution/                — 発注エンジン関連（Engine, OrderManager, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / 永続化層
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

各ファイルにはドキュメンテーション文字列（docstring）が付与され、設計上の注意や前提（例: ルックアヘッドバイアス防止、DB スキーマと互換性保持のためのマイグレーション処理等）が記載されています。実装の詳細は各モジュールの docstring を参照してください。

---

運用上の注意（抜粋）
- 本番（KABUSYS_ENV=live）では LINE 通知などアラート設定を必ず確認してください（validate_config が注意喚起します）。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。通常は 0 を推奨します。
- OpenAI を使う機能は API 費用・レートリミットの考慮が必要です。API キーは安全に管理してください。
- ロギングディレクトリに書き込み権限がない場合、ファイルハンドラは無効化され stdout のみになります（警告が出ます）。

---

問題発生時
- まず python -m kabusys.validate_config で設定を検証してください。
- ログ（logs/）を確認して例外や警告を確認してください。
- DB（data/*.db）をバックアップしてから操作してください。

---

ライセンス・バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）

---

この README はコードベースのドキュメント抜粋です。実際に運用する際は config/*.yaml（存在する場合）や各モジュールの docstring を参照し、適切なテスト環境で十分に検証したうえで本番運用してください。