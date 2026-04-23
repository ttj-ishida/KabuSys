# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ + 起動スクリプト / 運用ツール）です。  
このリポジトリは、戦略（リサーチ・ファクター計算）／ポートフォリオ構築（選定・配分・ポジションサイズ）／実行エンジン（発注）／監視（モニタリング・キルスイッチ）／AI 補助（ニュース NLP / レジーム判定）など、取引システムに必要な機能を分離して実装しています。

バージョン: 0.1.0

---

## 主な機能

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートから）
  - 対話式環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード分離（paper_trading 用 DB を使用）
  - BrokerClientFactory によるブローカークライアント切替
  - ExecutionEngine をデーモンスレッドで実行、停止フラグ監視
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視用 SQLite（monitoring.db）にログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止）
  - run_monitoring.py によるポーリングループ起動。MONITOR_POLL_INTERVAL で間隔調整可
- ポートフォリオ構築（純関数群）
  - 候補選定（スコア降順）、等金額/スコア重み、セクターキャップ、レジーム乗数
  - ポジションサイズ計算（リスクベース・配分ベース）と単元株丸め
- リサーチ（DuckDB によるファクター計算）
  - Momentum / Volatility / Value などのファクター計算
  - 将来リターン・IC（スピアマンランク相関）計算、統計サマリー
- AI モジュール（OpenAI を利用）
  - ニュース NLP（gpt-4o-mini で銘柄別センチメント算出 → ai_scores テーブルへ書込み）
  - レジーム判定（ETF MA + マクロニュースの LLM 評価を合成して market_regime に書込み）
  - API エラー時のリトライ戦略・フェイルセーフ設計
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 要件（推奨）

- Python 3.10+
- パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML パース検証を行う場合）
- SQLite は標準ライブラリで利用

（依存はプロジェクトで管理してください。requirements.txt があればそちらを利用します。）

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
     （お使いの環境に合わせて追加／調整してください）
4. 初期ディレクトリ作成（データ / ログ）
   - mkdir -p data logs
5. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（例は下の「重要な環境変数」を参照）
6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development)
  - 値: development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- OPENAI_API_KEY (AI モジュールを使う場合)
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒, default: 60)
- PAPER_FILL_MODE (paper_trading の MockBroker 挙動: instant|partial|never|reject, default: instant)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0|1, default: 0)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（オプション、アラート用）

Notes:
- .env ファイルはプロジェクトルートに置き、config_setup.py が対話式で生成できます。
- Settings モジュールはプロジェクトルートを探索して .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 実行方法（主要なエントリポイント）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が既にある場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成して行います（運用側でフラグを作成）。

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）。デフォルト 60 秒。
  - Monitoring は KABUSYS_ENV にかかわらず monitoring 用 sqlite_path（Settings.sqlite_path）を使用します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ログとプロセス優先度

- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
  - stdout に StreamHandler、logs/<app_name>.log に TimedRotatingFileHandler（日次ローテーション、30日保持）を設定します。
- 起動スクリプト（run_execution/run_monitoring）は開始直後に set_process_priority("high") を呼びプロセス優先度を高く設定しようとします（プラットフォーム依存のフォールバックあり）。

---

## 監視 DB 概要（monitoring_db）

init_monitoring_db() により冪等に作成されるテーブル:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id (always 1), updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

MonitoringDB クラスは上記への読み書きメソッドを提供します（ログ書込み、upsert_dashboard、リスクログのデデュープ等）。

---

## Kill Switch / 停止フラグ

- KillSwitch は設定された flag_path（通常 Settings.kill_flag_path → data/kill.flag）に理由を書き込みます。存在すれば ExecutionEngine の停止トリガーになります。
- run_execution.py / run_monitoring.py では data/stop_requested.flag の存在を監視して、ループ停止やエンジン停止を行います（運用側は stop フラグを作成してシグナルを送る運用）。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
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
    - tools/
      - paper_verification_report.py

（上は主要ファイルの抜粋です。実際のツリーはリポジトリ内をご確認ください。）

---

## 運用上の注意

- production (KABUSYS_ENV=live) の場合は特に注意：
  - OPENAI/API キーやブローカー API の設定、LINE 通知設定などを確実に確認してください。
  - validate_config.py は live 時に追加警告を出します（kill_flag_clear_on_start の確認等）。
- .env は Secrets を含むため絶対に Git にコミットしないでください。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。安全に検証できます。
- AI モジュールは API コールを行うため、API キーと利用料金に注意してください。API エラー時のフォールバックやリトライは組み込まれていますが、過剰な再試行は避けてください。

---

## よく使うコマンド例

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README の内容は実装コードの docstring / コメントを基にまとめています。さらに詳しい API 仕様や実装詳細（ExecutionEngine の振る舞い、BrokerClient の仕様、StrategyModel の設計方針等）は該当ソースコードとドキュメント（Project 内の Markdown）を参照してください。