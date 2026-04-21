README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームのコードベースです。  
ポートフォリオ構築、ポジションサイジング、リスク調整、監視（Monitoring）、発注エンジン（Execution）、リサーチ（DuckDB を使ったファクター計算）、および OpenAI を利用したニュース NLP/レジーム判定などの機能を含みます。

主な特徴
--------
- ポートフォリオ構築（候補選定、等金額・スコア加重）およびポジションサイズ計算
- セクター集中制限・レジーム乗数などのリスク調整
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替対応）
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して paper_trading DB に記録
- Monitoring（System / Trade / Risk）のポーリングと Kill Switch
  - 監視ログは SQLite（data/monitoring.db）に永続化
- DuckDB ベースのリサーチモジュール（ファクター計算・将来リターン・IC 等）
- OpenAI を使ったニュースセンチメント評価（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
- CLI 補助ツール:
  - .env を対話式で生成する config_setup
  - 設定検証 validate_config
  - Paper Trading 検証レポート生成ツール

動作前提 / 必要ライブラリ
------------------------
- Python 3.10 以上（typing の | 演算子等を使用）
- 必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML ファイルをチェックする場合）
- 実行環境に応じたその他ライブラリ（requirements.txt がある場合はそちらを参照してください）

インストール（例）
-----------------
1. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

設定（.env）
-----------
本プロジェクトは環境変数（.env）で設定を行います。対話式ウィザードで初期設定を行うことを推奨します。

- 対話式ウィザード:
  - python -m kabusys.config_setup
  - これによりプロジェクトルートの .env を生成/更新できます。

- 手動で編集する場合は最低限以下の必須環境変数を設定してください:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）

- 重要な環境変数（代表例）:
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - OPENAI_API_KEY: OpenAI を使う機能（ai.*）を利用する場合に必要

設定検証
--------
起動前に設定を検証できます。
- python -m kabusys.validate_config
- --strict オプションをつけると警告も失敗扱い（exit(1)）になります。

使い方（主なコマンド）
--------------------

- ExecutionEngine を起動（通常/本番/ペーパー）
  - KABUSYS_ENV を設定して実行
    - 例（開発）:
      - KABUSYS_ENV=development python -m kabusys.run_execution
    - 例（ペーパートレード）:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレードでは MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録されます。
  - 実行中に停止させたい場合は data/stop_requested.flag を作成するとループが終了します（run_execution/run_monitoring ともに参照）。
  - 実行時に PID ファイル（デフォルト: data/execution.pid）が作成されます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に依らず sqlite_path（本番の monitoring DB）を使用します（監視は常に本番 DB を見る設計）。
  - 監視ループ停止には data/stop_requested.flag を作成してください。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH が未設定の場合は指定）
  - 生成される指標: 稼働率、注文成功率、送信率、レイテンシ（P95）など。PASS/FAIL を判定します。

- AI / レジーム機能
  - ai.news_nlp.score_news と ai.regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。
  - API キーがない場合、該当機能を呼び出すと例外が発生します（実装上はエラーハンドリングありの箇所もありますが、キーの用意を推奨）。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
- デフォルトでは logs/<app_name>.log（日次ローテーション、30 日分保持）に出力され、コンソールは stdout に出力されます。
- LOG_DIR を環境変数で指定可能。

停止・Kill Switch
-----------------
- data/stop_requested.flag:
  - run_execution.py / run_monitoring.py がループを抜けるための停止フラグ（外部で作成・削除して制御）。
- Kill Switch（自動停止）:
  - モニタリングが RiskMonitor の条件（例: ドローダウン閾値超過など）を検出した場合、data/kill.flag を書き込むことで ExecutionEngine に停止を促します。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に自動的に Kill Flag をクリアします（本番では 0 を推奨）。

データベース・主要ファイルパス（デフォルト）
--------------------------------------
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag
- Stop flag: data/stop_requested.flag
- ログディレクトリ: logs/

注意事項 / 運用上のメモ
----------------------
- .env は絶対にリポジトリにコミットしないこと（秘密情報を含む）。
- KABUSYS_ENV=live を指定する場合は設定・通知（LINE 等）を必ず確認してください。validate_config における live 向けの追加ガードがあります。
- Monitoring は監視データの永続化のため、本番の monitoring DB を参照します。監視の読み書きは慎重に扱ってください。
- OpenAI の呼び出しはレート制限・ネットワーク障害に対して指数バックオフなどのリトライ処理が入っていますが、API 利用料やレートに注意して運用してください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py       — 監視 DB（SQLite）操作
  - monitoring_engine.py   — 監視コンポーネント束ね
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン・ポジション監視
  - kill_switch.py         — kill.flag 制御
  - ...（trade_monitor, alert_manager 等）
- execution/
  - execution_engine.py    — ExecutionEngine 本体（参照のみ）
  - broker_factory.py
  - order_manager.py
  - order_repository.py
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

（上記は主要ファイルの抜粋です。実際のリポジトリ内ファイルを参照してください。）

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ で管理されています（現在: 0.1.0）。
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

サポート / 開発者向けメモ
------------------------
- ローカルでの実行・テスト:
  - .env を作成（config_setup） → validate_config を実行して問題ないか確認 → 実行
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等的にテーブル作成と簡単なマイグレーション（カラム追加）を行います。
- テスト・モック:
  - OpenAI など外部 API 呼び出し箇所はテスト時にモックする設計になっています（関数分離・テストフレンドリー）。

以上がこのコードベースの基本的な README 内容です。必要であれば「導入手順の詳細」「例となる .env のテンプレート」「起動/停止の運用手順」などを追記します。どの項目をより詳しく書きたいか教えてください。