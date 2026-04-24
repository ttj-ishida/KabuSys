README
======

概要
----
KabuSys は日本株向けの自動売買・研究基盤です。本リポジトリは以下の主要機能を持ちます。

- 発注エンジン（ExecutionEngine） — live / paper_trading モード対応
- 監視サブシステム（Monitoring） — システム状態・注文の監視、Kill Switch
- ポートフォリオ構築ユーティリティ（選定・重み付け・株数決定）
- リサーチ（ファクター計算 / 特徴量探索）
- AI 支援モジュール（ニュースのセンチメント分析、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート）
- 共通ユーティリティ（ロギング設定、プロセス優先度設定、DB 初期化など）

主な特徴
--------
- 環境切替: KABUSYS_ENV による development / paper_trading / live の切替
- Paper Trading モードは発注処理をモック化し、本番 DB と分離（デフォルト: data/paper_trading.db）
- DuckDB を用いた時系列データ解析（prices_daily / raw_financials 等）
- OpenAI を利用したニュース NLP（gpt-4o-mini 想定）およびレジーム判定
- 監視サブシステムは SQLite にログを永続化し、kill.flag による安全停止を提供
- ロギングはコンソール + 日次ローテーションファイルで統一管理

セットアップ手順
----------------
1. 必要な Python バージョン
   - Python 3.10 以降（型ヒントに | を使用しているため）

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - YAML 検証を行いたい場合: pip install PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. データ・ログ用ディレクトリ作成
   - mkdir -p data logs

5. .env の作成（推奨）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 生成後に設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール実行時に必要）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

使い方
------

基本的な起動方法（モジュール実行）
- 環境作成後、.env を準備し検証してください。

1. 設定ウィザード（.env を対話的に作る）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - オプション: --strict

3. ExecutionEngine の起動（発注エンジン）
   - 本番/開発は KABUSYS_ENV に依存します。
   - paper_trading の例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - live モード:
     - KABUSYS_ENV=live python -m kabusys.run_execution

   実行時のポイント:
   - paper_trading モードは専用 DB を使用し、本番 DB と分離されます。
   - 起動時に data/stop_requested.flag が存在すれば起動しません。
   - 実行中、停止シグナルは data/stop_requested.flag により受け付けます。
   - 実行中は data/execution.pid（または Settings.pid_file_path）に PID を書きます。

4. Monitoring の起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: 30）
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - Monitoring は常に（KABUSYS_ENV に関わらず）Settings.sqlite_path（監視用 DB）を参照します。
   - 停止フラグ（stop_requested.flag）を検知するとループを終了します。

5. Paper Trading 検証レポート（ツール）
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を明示する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 関連（ニュース NLP / レジーム判定）
- OpenAI API キーが必要です（環境変数 OPENAI_API_KEY）。
- プログラム的に呼び出す例:
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)  # api_key を None にすると env を参照
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

監視・安全停止の仕組み
- kill.flag:
  - KillSwitch が条件（例: ドローダウン閾値超過）を満たすと Settings.kill_flag_path（デフォルト: data/kill.flag）に理由を書き込みます。
  - ExecutionEngine 起動時にこのフラグがあると起動しない・停止時に検出して安全停止します。
- stop_requested.flag:
  - run_execution.py / run_monitoring.py は repository 内の data/stop_requested.flag を監視し、存在を検知するとループを終了します。

ログ
- ログは logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。
- setup_logging が各起動スクリプトで呼ばれます。LOG_DIR 環境変数でログディレクトリを上書きできます。

開発時のユーティリティ
- config_setup.py : 対話式 .env 生成
- validate_config.py : .env と config/*.yaml の検証（PyYAML があれば YAML パースも実施）
- tools/paper_verification_report.py : Paper Trading のパフォーマンス/安定性検証レポートを生成

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理（Settings）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化・永続化層
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — （注文監視ロジック）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みユーティリティ
  - monitoring_engine.py   — 個別モニタを束ねる
  - alert_manager.py       — （アラート送信ロジック）
- execution/
  - execution_engine.py    — 発注エンジンコア（EngineConfig など）
  - order_manager.py       — 発注管理
  - order_repository.py    — Order の永続化層
  - broker_factory.py      — BrokerClient の生成（Mock/実運用切替）
  - reconciler.py, risk_manager.py, ...
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・資金配分
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — Momentum/Value/Volatility ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — ロギング設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定

重要な設計ノート / 運用上の注意
-----------------------------
- Paper Trading と本番 DB は分離するよう設計されています。paper_trading の場合は Settings.paper_sqlite_path を確認してください。
- AI モジュールは OpenAI API を利用するため API キー・呼び出し制限に注意してください。API 呼び出しはリトライやフォールバックを備えていますが、コスト管理は利用者の責任です。
- run_monitoring は MONITOR_POLL_INTERVAL によりポーリング間隔を制御します。0 以下の値や無効な値は無視されデフォルト 60 秒が使われます。
- SQLite / DuckDB のパスは Settings でデフォルトを持ちますが、運用環境では明示的に .env で設定することを推奨します。
- .env ファイルは絶対にリポジトリへコミットしないでください（config_setup でも注意喚起があります）。

貢献・拡張
---------
- 監視ルール、リスク閾値、AI プロンプト、ファクター定義などは config ファイルやコードを通じて拡張できます。
- 開発時は validate_config.py で設定整合性を確認し、config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py が存在する場合）を利用してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ に記載されています（現状 0.1.0）。

お問い合わせ
------------
- この README にない実装詳細や補足が必要であれば、具体的に知りたいファイル名・機能を指定して質問してください。