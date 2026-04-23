# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システムのコア実装です。ポートフォリオ構築、ポジションサイジング、リスク調整、監視、ペーパートレード検証、LLM を用いたニュースセンチメントやレジーム判定などのコンポーネントを含みます。

以下はプロジェクトの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

## プロジェクト概要
- 自動売買（ExecutionEngine）と監視（MonitoringEngine）を分離して設計。
- DuckDB を分析向けデータベース、SQLite を監視・注文ログに使用。
- 本番（live） / ペーパー（paper_trading） / 開発（development）の3環境をサポート。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai.news_nlp）やレジーム判定（ai.regime_detector）機能を実装（APIキー必要）。
- モジュールは純粋関数的実装を重視し、磁気的な副作用を最小化（多くの関数は DB に直接依存しない）。

## 主な機能一覧
- 環境設定ウィザード（kabusys.config_setup）で .env を対話的に作成
- 設定検証 CLI（kabusys.validate_config）で起動前チェック
- ExecutionEngine 起動（src/kabusys/run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading 用 DB に分離
- MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor（監視・アラート・Kill Switch）
- Portfolio construction
  - 候補選定、等金額/スコア重み、リスクベースのポジションサイズ計算、セクターキャップ、レジーム乗数
- Research: ファクター計算（momentum/value/volatility）、特徴量探索（IC、統計サマリ）
- AI モジュール:
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に格納
  - regime_detector: ma200 + マクロニュースで市場レジーム判定・永続化
- ツール:
  - paper_verification_report: ペーパートレードの検証レポート生成（成功率・レイテンシ等）
- ユーティリティ:
  - ロギング設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - 設定読み込み（kabusys.config）: .env 自動読み込み（必要に応じて無効化可）

## 前提 / 必要パッケージ
（実際の requirements.txt はリポジトリに含まれていないため、必要な主要パッケージを例示します）
- python >= 3.9
- duckdb
- psutil
- openai（AI 機能を使う場合）
- pyyaml（config 検証で YAML をパースする場合に必要）

例:
pip install duckdb psutil openai pyyaml

## セットアップ手順

1. リポジトリをクローンして、Python 仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストールします（上記を参照）。
   - pip install duckdb psutil openai pyyaml

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザードで必須の値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。

   自動ロードを無効化したい場合:
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定を検証します:
   - python -m kabusys.validate_config
   - 警告をエラー扱いにしたい場合: python -m kabusys.validate_config --strict

5. 必要に応じてデータディレクトリを作成（デフォルトの DB/ログ先は data/ および logs/）。
   - mkdir -p data logs

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能使用時に必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - paper_trading: 発注は MockBrokerClient、データベースは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading のフィルモード: instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（本番環境での自動 kill flag クリア: 0/1、デフォルト: 0）

## 使い方（代表的コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - run_execution は Settings に基づいて SQLite / DuckDB に接続します。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し、本番 DB とは分離されます。
  - 停止方法: data/stop_requested.flag を作成するとスレッド検出で停止します。
  - ExecutionEngine の PID は data/execution.pid に書き込まれます（設定で変更可）。

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path を参照します（監視情報は環境に依らず同じ監視 DB に記録される設計）。
  - 停止は data/stop_requested.flag を作成して行います。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db（または環境変数 PAPER_TRADING_SQLITE_PATH）

- AI スコアリング / レジーム判定（ライブラリとして利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。

## 停止 / Kill Switch の仕組み
- KillSwitch は監視の結果に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時にこのフラグを検出して停止します。
- 手動で停止させたい場合、data/stop_requested.flag を作成すると run_execution / run_monitoring のループが安全に終了します。
- 設定により起動時に kill.flag を自動クリアするかどうかを KILL_FLAG_CLEAR_ON_START で制御できます（本番では 0 推奨）。

## ロギング
- ログは stdout とファイル（logs/<app_name>.log）に出力されます（TimedRotatingFileHandler による日次ローテーション、デフォルトで30日保持）。
- ログディレクトリは環境変数 LOG_DIR または setup_logging 引数で変更可能。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主要モジュールを抜粋した構成です（実際のリポジトリルートに合わせて調整してください）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - ...（trade_monitor, alert_manager 等）
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - risk_manager.py
    - reconciler.py
  - data/ (実行時に生成される)
    - monitoring.db (SQLite, 監視ログ)
    - paper_trading.db (SQLite, ペーパー用)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

## 実運用上の注意
- KABUSYS_ENV=live の場合は本番口座に発注が行われます。設定（LINE 通知、Kill Switch 設定、DB パス、API キー等）を十分に確認してください。
- .env は絶対に Git にコミットしないでください（config_setup のコメントにも注意書きあり）。
- AI 機能は API キーや料金に注意して運用してください。API エラー時はフェイルセーフとしてスコア0やデフォルト挙動にフォールバックする実装になっていますが、設計上の注意は必要です。
- process_priority / cpu_affinity の変更は権限が必要・OS により動作差があるため、ログや警告を確認してください。

---

この README はリポジトリ内のソースコード（主要モジュール）に基づいて作成しています。さらに詳しい仕様や設計方針はコード内の docstring、コメント、関連ドキュメント（例: PortfolioConstruction.md や StrategyModel.md が存在する場合）を参照してください。必要であれば README を拡張して、デプロイ手順や運用手順（systemd サービス定義、監視運用フローなど）を追加できます。