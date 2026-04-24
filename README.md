README
======

概要
----
KabuSys は日本株向けの自動売買システムの一部を構成する Python パッケージです。
主に次の責務を持ちます:

- 発注実行用の ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働監視・アラート・Kill Switch（監視ループ）
- ポートフォリオ構築・サイズ計算・リスク調整の純粋関数群（研究・実運用双方で利用）
- 研究用ファクター計算・特徴量解析（DuckDB を使ったオフライン集計）
- OpenAI を使ったニュース NLP / 市場レジーム判定（任意機能）
- 運用補助ツール（.env ウィザード / 設定検証 / ペーパートレード検証レポート など）

設計方針として、DB（SQLite / DuckDB）や外部 API（kabuステーション、J-Quants、OpenAI）へのアクセスを明示的に分離し、
ユニットテストしやすく、起動スクリプトから統一的にログ・プロセス優先度を設定できるようになっています。

主な機能
--------
- ExecutionEngine 起動 (本番 / paper_trading 切替)
  - KABUSYS_ENV により paper_trading モードでは MockBroker を使い DB を分離
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視ループ
  - Kill Switch（条件に応じて data/kill.flag を書き込む）
  - 監視結果を SQLite に永続化（monitoring_db）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、リスクベース発注量計算
  - セクターキャップ適用、レジーム乗数計算
- 研究モジュール
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析
- AI 連携（任意）
  - OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント付与、レジーム判定
  - API エラー時のリトライ／フォールバック処理あり
- 補助ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の起動前検証
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

依存関係（代表）
----------------
（プロジェクト配布時は requirements.txt を用意してください。ここでは代表的なパッケージを記載します）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML をパースしたい場合）
- その他標準ライブラリ

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   または最低限:
   - pip install duckdb psutil

   AI 機能を使う場合:
   - pip install openai

   config 検証で YAML を使用する場合:
   - pip install pyyaml

4. 環境変数（.env）を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - 重要な必須変数（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨で設定する変数の例:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH, SQLITE_PATH
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
   - ウィザード実行後は python -m kabusys.validate_config で検証することを推奨。

5. データディレクトリ
   - デフォルトで data/ に SQLite / PID / フラグファイル を置きます。
   - 必要に応じて .env の SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH を変更してください。

使い方（起動コマンド例）
-----------------------
- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔 (秒) を上書き可能（デフォルト 60 秒）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成するとループが検知して安全終了します

- 実行エンジン起動（発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード用 DB（data/paper_trading.db 等）を使用
  - 実行中はデフォルトで data/execution.pid に PID を書きます
  - 同様に data/stop_requested.flag があると起動・実行中に検知して停止します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指すことも可能

環境変数・重要事項
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用上よく使う:
  - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（paper_trading モード時に使用）
  - OPENAI_API_KEY: AI モジュール使用時に必要
  - LOG_LEVEL / LOG_DIR: ログ出力関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- Kill / Stop フラグ:
  - data/kill.flag: Kill Switch（ExecutionEngine に対する停止シグナルを記録するために書かれる）
  - data/stop_requested.flag: run_monitoring / run_execution が存在を検知して安全に終了するための外部停止フラグ（運用者が作成して停止を要求）
- ペーパートレード:
  - KABUSYS_ENV=paper_trading のとき、run_execution は MockBroker を使用し DB を分離します（実際の約定 API を叩きません）。

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging を通じて統一して設定されます。
- デフォルトは logs/<app_name>.log に日次ローテーション（30 日分保持）。
- LOG_DIR 環境変数または setup_logging の引数で変更可能。
- コンソール出力は stdout に出ます（cron 等でリダイレクトしやすいように）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数・.env 自動ロードロジックと Settings クラス
- config_setup.py
  - .env 作成ウィザード（対話式）
- validate_config.py
  - 起動前設定検証 CLI

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading による分離あり）

- monitoring/
  - monitoring_db.py — SQLite スキーマと永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システムリソース・データ鮮度・プロセス監視
  - risk_monitor.py — ドローダウン / ポジション数監視
  - trade_monitor.py — （発注監視・滞留注文検出等。参照は多数あります）
  - monitoring_engine.py — Monitor を束ねるポーリングエンジン
  - kill_switch.py — Kill Switch 実装
  - alert_manager.py — アラート送信（LINE 等。実装に依存）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - ExecutionEngine と発注周りの主要コンポーネント（run_execution から利用）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み計算・数量決定・セクター制限 等の純粋関数群

- research/
  - factor_research.py, feature_exploration.py
  - DuckDB を使ったファクター計算・将来リターン・IC・要約統計

- ai/
  - news_nlp.py — OpenAI を使ったニュースセンチメント付与
  - regime_detector.py — ETF MA とマクロセンチメントの合成による市場レジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- utils/
  - logging_setup.py — 一貫したログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では必須の設定や通知先（LINE 等）を必ず確認してください。validate_config がいくつかのチェックを行います。
- OpenAI などの外部 API 呼び出し機能は API キーが必要であり、課金が発生します。AI 機能は任意で利用してください。
- run_execution は実際の発注を行います。実行前に設定・リスク管理（risk_config.yaml 等）を十分に確認してください。
- SQLite / DuckDB のパスは .env で管理できます。運用環境ではバックアップや権限設定に注意してください。

その他
-----
- パッケージを配布する際は requirements.txt を用意し、README をプロジェクトルートに配置してください。
- テストや CI で環境変数の自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップします。

おわりに
--------
この README は現行コードベースの主要ファイルと設計意図に基づいて作成しています。実際の運用や拡張時は各モジュール（execution/*, monitoring/*, ai/*）の詳細なドキュメントや設定ファイル（config/*.yaml）を参照してください。必要であれば各モジュールごとの詳細 README を追加で作成できます。