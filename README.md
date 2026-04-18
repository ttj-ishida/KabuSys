README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
このリポジトリはトレーディング実行エンジン、監視 (monitoring)、ファクター計算・研究、ニュース NLP（LLM）によるセンチメント評価、ペーパートレード検証などのコンポーネントを含むモジュール群で構成されています。  
設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗はスキップして継続）」などが採用されています。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading / live / development を切り替え
  - paper_trading 時は MockBroker を用い、専用 SQLite（data/paper_trading.db）へ記録
  - 停止フラグ（data/stop_requested.flag）で安全に停止
- 監視ポーリング（run_monitoring.py）
  - CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - Monitoring 用 SQLite（data/monitoring.db）へログ永続化
- 監視コンポーネント群
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager（アラート送信は LINE 等と連携可能）
- Portfolio 構築ユーティリティ
  - 候補選定、等配分・スコア加重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research（DuckDB ベース）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC（Information Coefficient）計算、統計要約
- AI（OpenAI）連携
  - ニュース NLP（news_nlp.py）で銘柄ごとのセンチメントを ai_scores に保存
  - 市場レジーム判定（regime_detector.py）で MA200 とマクロセンチメントを合成
- ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ログ設定・プロセス優先度制御
  - 統一的なログ設定（kabusys.utils.logging_setup）
  - psutil を使ったプロセス優先度・CPU affinity 設定

セットアップ
----------
前提:
- Python 3.10 以上（typing の | None 表記等を使用）
- 推奨: 仮想環境 (venv, virtualenv, conda 等)

1. リポジトリをクローンし、プロジェクトルートへ移動
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意（config YAML の検証を行いたい場合）: pip install PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 初期設定 (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）
     - 重要な環境変数:
       - JQUANTS_REFRESH_TOKEN（必須）
       - KABU_API_PASSWORD（必須）
       - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（デフォルト: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス）
       - OPENAI_API_KEY（AI 機能利用時に必要）
       - LOG_LEVEL（例: INFO）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

使い方（主要スクリプト）
-----------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite を使用
    - data/stop_requested.flag が存在すると起動を中止
    - data/execution.pid に PID を書く（設定により）
    - プロセス優先度を high に設定（psutil が許す場合）

- 監視ポーリングを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能
    - 例: MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path を使用してログを残します

- 設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH で PAPER_TRADING_SQLITE_PATH の代替を指定可能

- AI 系（ニューススコア / レジーム判定）
  - duckdb 接続を作成し、kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: OPENAI_API_KEY（または api_key 引数）の設定が必要

停止・フラグファイル
-------------------
- 停止（実行エンジンや監視）を外部から指示するためのフラグ:
  - data/stop_requested.flag : run_execution / run_monitoring が検知して安全に停止
  - data/kill.flag : KillSwitch が書き込み、ExecutionEngine に停止シグナルを送る（通常は監視コンポーネントが作成）
- KillSwitch の動作:
  - リスク監視（ドローダウン等）でトリガーした場合に data/kill.flag を作成し、理由をファイルに書き込む

データベース
----------
- SQLite
  - 監視ログ: data/monitoring.db（init_monitoring_db で必要テーブルを自動作成・マイグレーション）
  - Paper Trading: data/paper_trading.db（paper_trading モードで使用）
- DuckDB
  - 分析・リサーチ用: data/kabusys.duckdb（デフォルト）
  - research / ai モジュールは DuckDB 接続を受け取り SQL で処理を行う

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されます。
- デフォルトは logs/<app_name>.log に日次ローテーションで出力（30 日保持）し、コンソールにも出力します。
- LOG_DIR や LOG_LEVEL は環境変数で上書き可能。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照あり)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/                    (発注周りの実装)
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
  - data/ (想定される配置)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
  - config/
    - *.yaml (system_config.yaml, data_config.yaml, strategy_config.yaml, ...)

補足 / 運用メモ
----------------
- KABUSYS_ENV によって動作が分岐します。特に paper_trading は実口座とデータを分離するため安全に挙動を試験できます。
- run_execution と run_monitoring は両方ともプロセス優先度を "high" に設定しようとしますが、権限不足や OS によってはスキップされます（警告ログのみ）。
- OpenAI を使う機能は API 呼び出し失敗時にフォールバックやリトライを行う実装ですが、API キーの管理・レート制限に注意してください。
- monitoring_db.init_monitoring_db はテーブル存在を保ちながら必要カラムのマイグレーションを行います（冪等）。

ライセンス / 貢献
-----------------
（必要に応じてライセンスや貢献ガイドをここに追記してください）

以上。開発・運用時に README へ追記したい点（例: 実行例ログ、systemd ユニット例、Heroku / Docker 利用手順等）があれば教えてください。必要に応じて追補します。