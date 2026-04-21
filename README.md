README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤を想定した Python パッケージです。  
主な機能は以下の通りです:

- 注文実行エンジン（ExecutionEngine）: 実際のブローカー / モック（ペーパートレード）で発注処理を行う
- 監視（Monitoring）: システム稼働状況・データ鮮度・注文ログ・リスク指標の定期チェック
- ポートフォリオ構築ユーティリティ: 候補選定、重み付け、ポジションサイズ計算、セクター制約等
- 研究／リサーチモジュール: ファクター計算、将来リターン、IC 計算、特徴量探索
- AI 支援モジュール: ニュースを LLM（OpenAI）でスコアリング、マーケットレジーム判定
- 補助ツール: .env 設定ウィザード、設定検証、Paper Trading 検証レポート出力 など

主要な設計方針:
- 環境変数/.env による設定管理
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用途（prices_daily 等）に利用、SQLite を監視・トレース用に利用
- OpenAI API 呼び出しはフェイルセーフで最大再試行を実装

機能一覧
--------
- 実行:
  - run_execution.py: ExecutionEngine を起動（本番 / ペーパートレード切り替え）
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading.db を使用
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを記録
    - MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）
- 設定 / 検証:
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境設定・config/*.yaml の検証（--strict オプションあり）
- ツール:
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポート生成（期間指定可）
- モジュール群:
  - kabusys.portfolio: 銘柄選定・重み・ポジションサイズ・セクター制約
  - kabusys.research: ファクター計算、将来リターン、IC、統計サマリ
  - kabusys.ai: news_nlp（ニュースの LLM スコアリング）、regime_detector（レジーム判定）
  - kabusys.monitoring: monitoring_db、system_monitor、trade_monitor、risk_monitor、kill_switch、monitoring_engine
  - kabusys.utils: logging_setup、process_priority 等のユーティリティ

セットアップ手順
--------------
1. Python 環境の準備
   - Python 3.10+ を推奨
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（代表的なパッケージ）
   - pip install duckdb psutil openai PyYAML
   - 実際のプロジェクトでは requirements.txt を用意している可能性があります。

3. プロジェクトルートに移動（.git または pyproject.toml が存在するディレクトリ）
   - config_setup.py はプロジェクトルートの .env を更新します。

4. .env 作成（対話式推奨）
   - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - リスクを厳密に検査したい場合は --strict を付与

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリア（開発用、0/1）

使い方（主要 CLI / スクリプト）
--------------------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のときは専用の paper_trading DB を使用し、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動しません（停止制御）。
    - 実行中は data/execution.pid に PID が書き込まれます。

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 注意:
    - 監視は環境にかかわらず本番 sqlite_path を参照して監視ログを記録します（設計上の注意）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使う（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI モジュール（ニュース NLP / レジーム判定）
  - OpenAI API キーが必須（環境変数 OPENAI_API_KEY を設定）
  - 呼び出し例（Python から）:
    - from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="...")

ログ
---
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log に日次ローテーションで出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
- LOG_DIR 環境変数でログ保存場所を変更可能。

運用・停止制御
--------------
- Kill Switch:
  - kabusys.monitoring.kill_switch.KillSwitch はリスク条件（ドローダウンやポジション上限）で data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 停止フラグ:
  - data/stop_requested.flag が存在すると run_monitoring / run_execution のループが停止または起動を拒否する仕組みがあります（簡易的な外部停止用フラグ）。
- PID ファイル:
  - ExecutionEngine は起動時に data/execution.pid（パスは Settings で指定）へ PID を書き込みます。

注意事項 / 実装上のメモ
--------------------
- .env の自動ロード:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を基に .env と .env.local を自動ロードします。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト用途向け）。
- Paper Trading の分離:
  - KABUSYS_ENV=paper_trading のとき、paper_sqlite_path が使用され、本番 sqlite_path とは別ファイルで記録されます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は既存 DB に対する簡易マイグレーション（カラム追加等）を行います。
- 外部依存:
  - OpenAI 呼び出し、DuckDB、psutil、PyYAML（config 検証）などが必要です。環境に応じてインストールしてください。
- Safety:
  - 本番（live）環境に切り替える前に必須環境変数や LINE 通知設定等を validate_config.py で必ず検証してください。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトルート（src/ を展開した形を示す）

- src/
  - kabusys/
    - __init__.py
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py (省略されているが存在想定)
      - kill_switch.py
      - alert_manager.py (省略されているが存在想定)
    - execution/                — Execution 系の実装（order_manager 等）
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (上記は存在が想定され、validate_config で確認されます)

- data/
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (デフォルト PAPER_TRADING_SQLITE_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/
  - execution.log
  - monitoring.log
  - ... （日次ローテート）

参考コマンド集
--------------
- .env を作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期リリース想定）

最後に
------
この README はリポジトリ内のソースコード（各モジュールの docstring と実装）に基づいて作成しています。実環境への導入前に .env、config/*.yaml、及び外部 API キー（OpenAI / kabuステーション / J-Quants）を適切に設定し、validate_config.py による検証を必ず実行してください。質問や補足が必要であれば教えてください。