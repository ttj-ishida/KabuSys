# KabuSys

日本株向け自動売買システムのモジュール群です。ポートフォリオ構築、ポジションサイジング、発注エンジン、監視・アラート、研究用ファクター計算、OpenAI を使ったニュース評価などを含む設計済みのライブラリ／起動スクリプト群を提供します。

## 概要
- モジュール構成は軽量で疎結合を意識しており、運用（live）、ペーパートレード（paper_trading）、開発（development）に対応します。
- DuckDB を用いた分析用 DB、SQLite を用いた監視／注文ログを使い分けます。
- ExecutionEngine は Kabu ステーション等のブローカークライアントを用いて発注制御を行い、Monitoring 系はシステム監視・リスク検出・Kill Switch を提供します。
- ニュースの NLP スコアリングや市場レジーム検出は OpenAI API（gpt-4o-mini 等）を利用するオプション機能です（APIキーが必要）。

## 主な機能一覧
- Execution / 発注処理（run_execution.py）
  - 本番 / ペーパートレード（MockBroker）切替
  - OrderManager / OrderRepository / RiskManager / Reconciler 等の組立て
- Monitoring（run_monitoring.py）
  - SystemMonitor, TradeMonitor, RiskMonitor を用いた定期ポーリング
  - Kill Switch（条件に応じて data/kill.flag を書き込み Execution を停止）
- 監視用 DB 層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル（冪等初期化）
- ポートフォリオ構築（portfolio パッケージ）
  - 銘柄選定、等ウェイト／スコアウェイト計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究／ファクター（research パッケージ）
  - Momentum / Volatility / Value ファクター計算、将来収益やIC計算、統計サマリー
- AI 系（ai パッケージ）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- ツール
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - 統一ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）

## 要求環境（主な依存）
- Python 3.9+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 推奨（オプション）:
  - PyYAML（config の YAML 検証に使用）
- インストール例:
  - pip install duckdb psutil openai pyyaml

※プロジェクトに requirements.txt がある場合はそれを使用してください。

## セットアップ手順

1. リポジトリをクローン／配置
   - ソースルートに `src/` 配置に合わせてください（本コードは `src/kabusys` 配下を想定）。

2. Python 環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml

3. .env を作成する
   - 対話ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能利用時）
   - その他: KABUSYS_ENV（development / paper_trading / live）、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、PAPER_TRADING_SQLITE_PATH など
   - 注意: .env はリポジトリにコミットしないでください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. 初期ディレクトリ作成
   - 監視用 SQLite DB やログディレクトリは起動時に自動作成されますが、必要に応じて `data/` や `logs/` を作成してください。

## 使い方（主要スクリプト）

- Execution エンジン起動（本番 or paper_trading に応じて動作）
  - python -m kabusys.run_execution
  - 動作概要:
    - Settings によって DB パスの切替（paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用）
    - BrokerClientFactory によるブローカークライアント生成（Mock または 本番）
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による停止監視を行う
    - PID ファイル: data/execution.pid（Settings.pid_file_path で参照）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作概要:
    - SystemMonitor を初期化してポーリングループを実行
    - ポーリング間隔はデフォルト 60 秒。環境変数で上書き可:
      - MONITOR_POLL_INTERVAL（秒、1 以上）
    - 停止はプロジェクトルートの data/stop_requested.flag を作成
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存しない）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使用するか環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 機能（スコアリング / レジーム検出）
  - 必要: OPENAI_API_KEY を環境変数または関数引数で指定
  - 例（スクリプトを用意して呼び出す想定）:
    - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

## 重要な環境変数とファイルパス（デフォルト値）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し DB を分離（data/paper_trading.db）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能利用時に必須）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO（デフォルト）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- PID / フラグファイル:
  - data/execution.pid（Execution の PID）
  - data/stop_requested.flag（run_* スクリプトの外部停止フラグ）
  - data/kill.flag（Kill Switch によって書き込まれる Execution 停止フラグ）

## ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- コンソール出力は stdout（stderr ではない）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging(app_name=...) で統一されています。

## 運用メモ / 注意点
- Monitoring は常に Settings.sqlite_path（本番 DB）を参照します。監視は環境（KABUSYS_ENV）にかかわらず本番 DB を対象とする設計です。
- paper_trading モードは発注処理を完全に分離するため、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）を使用します。
- Kill Switch（risk 閾値超過等）は data/kill.flag を書き込みます。本番で自動クリアを設定するのは危険です（KILL_FLAG_CLEAR_ON_START は 0 推奨）。
- OpenAI を使う機能は API 呼び出しの失敗に対してリトライやフェイルセーフを備えていますが、API キーとコスト管理に注意してください。
- DuckDB / SQLite 関連の SQL は一部バージョン依存のバインド挙動対策（executemany の空リスト回避など）が実装されています。

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — 統一ログ設定
    - process_priority.py    — プロセス優先度・CPU affinity
  - execution/               — Execution 関連コンポーネント（OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - monitoring_engine.py
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
  - data/ (実行時に作成される想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 時)
    - execution.pid
    - kill.flag / stop_requested.flag
  - tools/
    - paper_verification_report.py

（実際のリポジトリでは上記に加えて execution/*.py、data パイプライン、strategy、order_repository 等の補助モジュールが含まれます）

---

問題が発生した場合や特定モジュールの使用例が必要であれば、どの機能（例: Execution の起動フロー、ポジションサイジングのパラメータ、AI スコアリングのテスト方法）について詳細を出力するか指定してください。