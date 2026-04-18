README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤の軽量フレームワークです。本リポジトリには以下の主要機能が含まれます。

- シグナル→ポートフォリオ構築→発注までの Execution エンジン（実運用 / ペーパートレード対応）
- 監視サブシステム（システム状態・発注ログ・リスク監視・Kill Switch）
- ファクター計算・リサーチ用ユーティリティ（DuckDB を利用）
- ニュース NLP（OpenAI）を使ったセンチメントスコアリング、およびレジーム判定
- CLI ツール類（環境設定ウィザード、設定検証、ペーパートレード検証レポート生成 など）

主な設計方針：
- DB（SQLite / DuckDB）中心の軽量構成。発注系は本番 DB とペーパートレード DB を分離。
- 外部 API 呼び出し（OpenAI など）は明示的にキーを受け取るか環境変数に依存。
- フェイルセーフ（API失敗やデータ欠落時はフォールバック）を重視。

機能一覧
--------
- Execution（src/kabusys/run_execution.py）
  - BrokerClientFactory により本番ブローカー / MockBroker を切替。
  - paper_trading 環境時は data/paper_trading.db にログを記録して本番 DB と分離。
  - PID ファイル・停止フラグ（data/stop_requested.flag）で外部から停止可能。

- Monitoring（src/kabusys/run_monitoring.py / monitoring/*）
  - system_monitor（CPU・メモリ・ディスク・データ鮮度・プロセス生存）
  - trade_monitor（発注ログの異常検知）
  - risk_monitor（ドローダウン・ポジション上限監視）
  - kill_switch（危険検知時に data/kill.flag を書き込み Execution を停止）
  - monitoring DB スキーマ管理（monitoring_db.py）

- Portfolio（src/kabusys/portfolio/*）
  - 候補選定、重み算出（等金額／スコア重み）
  - セクターキャップ、レジーム乗数
  - ポジションサイズ算出（単元丸め、リスクベース、aggregate cap）

- Research（src/kabusys/research/*）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB による高速な SQL ベース処理

- AI（src/kabusys/ai/*）
  - news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書込
  - regime_detector: ETF MA200 乖離 + マクロニュースで日次レジーム判定

- ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度・CPU affinity 設定（utils/process_priority.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）

前提条件（推奨）
---------------
- Python 3.10+
- インストール推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリで利用可能）
- ネットワーク接続（OpenAI など外部 API 利用時）

セットアップ手順
----------------
1. リポジトリをクローンし仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML

   ※ requirements.txt がある場合は pip install -r requirements.txt を利用。

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従い必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV など）を入力します。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにしたい場合は --strict を付与。

5. 必要なディレクトリの準備（通常はログ/DB 配下を自動作成するが手動でも可）
   - mkdir -p data logs

使い方（実行例）
----------------

- ExecutionEngine を起動（本番かペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 補足: 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し data/paper_trading.db に記録。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト: 60）
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止検知: プロジェクトルート/data/stop_requested.flag の作成でループが終了します。

- .env の雛形・対話ウィザード
  - python -m kabusys.config_setup

- 設定を検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗（exit 1）扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

設定（主な環境変数）
-------------------
主に .env で管理します。以下は重要なキーとデフォルト/説明。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring 用
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用 DB
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- LOG_DIR (デフォルト: logs/)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0 | 1) — live 環境では 0 推奨
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定モード
- MONITOR_POLL_INTERVAL (秒) — run_monitoring 起動時に上書き可能

注意事項 / 挙動メモ
-------------------
- ペーパートレード: KABUSYS_ENV=paper_trading により発注処理が MockBroker に切替、ログは data/paper_trading.db に記録されます。本番データベースと完全分離されています。
- Kill Switch: risk_monitor 等が条件を満たすと data/kill.flag に理由（文字列）を書き込みます。ExecutionEngine は起動中にこのフラグを検知して安全に停止します。
- Logging: setup_logging() で stdout と 日次ローテートファイル（logs/<app_name>.log）を設定します。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。
- process_priority: 起動スクリプトは最初にプロセス優先度を "high" に設定する試みを行います（psutil が必要）。設定に失敗しても実行は継続します。
- DuckDB/SQLite: Research 系は DuckDB を利用して高速集計を行います。Monitoring/Execution の永続化には SQLite を使用しています。
- OpenAI: news_nlp / regime_detector は OpenAI API を使います。API キーは OPENAI_API_KEY 環境変数か関数引数で渡してください。API 呼び出しはリトライロジックを持ち、失敗時は安全にフォールバックします。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / Settings
- config_setup.py                   — .env 対話式ウィザード
- validate_config.py                — 設定検証 CLI
- run_execution.py                  — ExecutionEngine 起動スクリプト
- run_monitoring.py                 — Monitoring 起動スクリプト

- execution/                         — 発注関連（Broker / Engine / OrderManager 等）  ※詳細は該当ディレクトリ
- monitoring/
  - monitoring_db.py                 — SQLite スキーマ + DB 操作用ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py                 — （通知管理、LINE 等。実装参照）
  - monitoring_engine.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

監視 DB スキーマ（概要）
-----------------------
monitoring_db.init_monitoring_db() により作成されるテーブル（冪等）:
- system_status (cpu/memory/disk/process_ok 等)
- trade_logs (発注イベントログ、latency_ms を含む)
- positions (現在ポジション)
- risk_logs (リスクイベント)
- dashboard (集計、peak_value 等)

開発者向けメモ
---------------
- DuckDB のクエリは大量データの集計に有効。ロジックは SQL と純粋関数で書かれているためテストが容易です。
- 外部 API 呼び出し（OpenAI 等）をテストする場合は該当関数をモックする設計になっています（_call_openai_api を patch など）。
- config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env を自動ロードします。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

お問い合わせ / 貢献
-------------------
バグ報告や機能追加の提案は Issue を作成してください。Pull Request は歓迎します。README に記載のない運用ルールや安全運用に関する疑問があれば、まずは validate_config.py と config_setup.py の挙動を確認してください。

以上。