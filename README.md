# KabuSys

日本株自動売買システム KabuSys のリポジトリ向け README（日本語）です。

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究・監視ツール群です。主な目的は以下です。

- 日次のファクター計算・研究（DuckDB を用いた履歴データ解析）
- シグナルに基づくポートフォリオ構築（候補選定・重み付け・株数算出）
- ExecutionEngine による発注管理（本番 / ペーパートレードを切り替え可能）
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch、アラート）
- AI を利用したニュースセンチメント（OpenAI）や市場レジーム判定
- 運用・検証用ツール（設定ウィザード、設定検証、ペーパー検証レポート等）

設計上の特徴:
- 環境変数 / .env による設定管理
- 実行スクリプトはモジュールとして起動可能（例: python -m kabusys.run_execution）
- 本番 DB とペーパートレード DB を分離
- フェイルセーフ（API 失敗時はスキップやフォールバック）を重視

---

## 機能一覧

- Execution
  - ExecutionEngine（発注、注文管理、リスク管理、リコンサイル）
  - Broker クライアント切替（本番 / Mock（paper_trading））
  - Paper trading 用 DB（data/paper_trading.db、環境により分離）

- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、プロセス存続確認、データ鮮度チェック
  - TradeMonitor: 注文滞留や約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン監視・ポジション上限監視
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）を書き込み
  - MonitoringEngine: 各 Monitor を束ねポーリング実行

- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン / IC / 統計サマリ等の研究用関数
  - ポートフォリオ構築: 候補選定、等配分/スコア配分、リスクベースの株数算出
  - セクターキャップ、レジーム乗数などのリスク調整

- AI
  - news_nlp: OpenAI を用いたニュースセンチメント集約（ai_scores 書き込み）
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成し市場レジーム判定

- ユーティリティ
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env と config/*.yaml の検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成
  - logging_setup: 共通のログ設定（stdout + 日次ファイルローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

以下は基本的なローカルセットアップ手順（Linux/macOS 想定）。

1. ソースをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を行う場合は PyYAML も: pip install pyyaml
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成
   - 自動ロード: モジュール起動時にプロジェクトルートの `.env` / `.env.local` が自動読み込みされます。
     - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする際は: python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルト DB / PID / フラグは `data/` に保存されます（自動生成されますが権限等は確認してください）
   - ログは `logs/` に保存（環境変数 LOG_DIR で変更可）

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- LOG_LEVEL（例: INFO）
- LOG_DIR（ログ保存先）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔を秒で上書き、デフォルト 60）

PAPER_FILL_MODE（paper_trading の MockBroker 動作）
- instant | partial | never | reject（デフォルト: instant）

---

## 使い方（主要コマンド）

基本はモジュールを直接実行します。各コマンドはプロセス優先度設定やログ設定を共通に行います。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用してデータは data/paper_trading.db に保存されます（本番 DB と分離）。
    - 起動前に data/kill.flag（Kill Switch）をクリアする必要がある場合があるため、必要時は削除してください。
    - 実行中に停止させるには data/stop_requested.flag を作成すると監視ループ/Engine が終了します。

- 監視ループ起動（SystemMonitor 単体起動）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
    - Monitoring は環境に関係なく `settings.sqlite_path`（デフォルト data/monitoring.db）を使用します（監視ログは本番 DB を見る設計）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告を失敗扱い（exit 1）

- Paper Trading 検証レポート（期間指定可）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が環境変数に設定されているか、api_key 引数を渡す必要があります。

停止・フラグについて
- stop_requested.flag: 実行スクリプトが監視している「早期停止要求」ファイル（run_execution.py, run_monitoring.py が参照）
  - 位置: project_root/data/stop_requested.flag
- kill.flag: KillSwitch が書き込む停止信号（ExecutionEngine に停止を要求するために外部に置く）
  - 位置は Settings.kill_flag_path（デフォルト data/kill.flag）
- PID ファイル: run_execution で _EXECUTION_PID = data/execution.pid を使用（プロセス管理用途）

ログ
- デフォルトログディレクトリ: logs/
- アプリごとにファイル: logs/execution.log, logs/monitoring.log など（TimedRotatingFileHandler、日次ローテート）

---

## サンプル .env（最小例）

例（絶対に Git にコミットしないこと）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

.env は `python -m kabusys.config_setup` で対話的に生成できます。

---

## ディレクトリ構成（主要ファイル）

以下はソースベース内の主要ファイル / ディレクトリのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数読み込み・Settings
    - config_setup.py          # .env ウィザード
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # Monitoring ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - execution/               # ExecutionEngine 関連（発注/リスク/リポジトリ等）
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py       # SQLite 永続化層
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
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
    - data/ (ランタイム生成想定)
      - monitoring.db (デフォルト SQLite)
      - paper_trading.db (paper_trading 用)
      - kill.flag / stop_requested.flag / execution.pid
    - logs/ (ランタイム生成想定)

注意: 実際のリポジトリには上記以外の補助ファイルや追加モジュールが含まれる場合があります。

---

## 補足・運用上の注意

- 本番（KABUSYS_ENV=live）設定の場合は LINE 通知設定や Kill Switch の扱いを慎重に確認してください。validate_config は live の場合に追加警告を出します。
- AI 機能は外部 API（OpenAI）を使用するため API キー管理とコストに注意してください。API エラーは多くの箇所でフォールバック実装がありますが、期待する結果が得られない可能性があります。
- データファイル（data/）およびログディレクトリ（logs/）は運用上の権限・バックアップポリシーを検討してください。
- .env は秘匿情報を含むため絶対に VCS にコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

必要であればこの README をさらに詳細化（コマンド例、設定ファイルテンプレート、運用手順、監視アラートの挙動や DB スキーマ説明等）します。どのセクションの追記が必要か教えてください。