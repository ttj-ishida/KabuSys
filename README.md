KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を想定した小規模なシステム基盤です。
本リポジトリには設定管理、監視プロセス、発注エンジン、ブローカー API 抽象などの
コアコンポーネントが含まれます。実運用（本番）とペーパートレード（模擬発注）を
切り替え可能な設計で、クラッシュ耐性・リコンシリエーション・3段階のリスクガードを備えます。

主な特徴
--------
- 環境設定ウィザード（.env 作成支援）: python -m kabusys.config_setup
- 起動前設定検証 CLI（.env と config/*.yaml のチェック）:
  python -m kabusys.validate_config
  - --strict を指定すると警告も失敗扱いで exit(1)
- 発注エンジン（ExecutionEngine）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し、本番 DB と分離
- 監視プロセス（SystemMonitor ポーリング）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60秒）
- ブローカークライアント抽象（BrokerAPIProtocol）と Mock 実装
- 注文状態管理（OrderRecord）と永続化（SQLite via OrderRepository）
- 起動時リコンシリエーション（Reconciler）で OrderSent 状態の同期
- データ関連ユーティリティ（マーケットカレンダー、ニュース収集など）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成して有効化（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 以下は主に利用されるライブラリの例です:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml (config YAML 検証用、任意)
     - defusedxml (news_collector で利用)
   - 例:
     - pip install duckdb httpx websocket-client pyyaml defusedxml

   （リポジトリに requirements.txt がある場合はそれを使ってください:
    pip install -r requirements.txt）

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - ウィザードは .env を生成し、次のステップとして validate_config を実行することを推奨します。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は出力を確認して .env や config/*.yaml を修正してください。
   - 警告も失敗扱いにするには --strict を付けます。

環境変数（主な項目）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV            — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- LOG_LEVEL              — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABU_API_BASE_URL      — kabu station API の base URL
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（本番では必須推奨）
- LINE_USER_ID              — LINE 通知先ユーザー ID

注意:
- 本番（KABUSYS_ENV=live）では LINE 通知や Kill Switch 設定を特に確認してください。
- KILL_FLAG_CLEAR_ON_START=1 は起動時に kill flag を自動クリアします（開発用、production では 0 推奨）。

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（発注プロセス）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が live の場合は実際に発注が行われる可能性があるため、
    テスト・開発時は paper_trading を使用してください。

- 監視プロセス（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒単位ポーリング間隔を指定可（デフォルト 60）

- 開発・テスト用: Mock ブローカー
  - KABUSYS_ENV=paper_trading または development のとき、MockBrokerClient が選択され自動的に使われます。

運用上のファイル・フラグ
----------------------
- PID ファイル: デフォルト data/execution.pid（設定で上書き可能）
- kill.flag: settings.kill_flag_path（デフォルト data/kill.flag）
  - 起動中に kill.flag を検出するとエンジンは安全停止し、全 active 注文をキャンセルします。
- stop_requested.flag: run_monitoring / run_execution の停止フラグ（data/stop_requested.flag）

ディレクトリ構成
----------------
（プロジェクトルートの src/kabusys を起点に簡易的に示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPIProtocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に基づくクライアント生成
    - kabu_client.py         — kabu station 実装（HTTP + WebSocket）
    - mock_client.py         — MockBrokerClient（テスト用）
    - execution_engine.py    — ExecutionEngine（シグナル処理・push ドレイン）
    - order_manager.py       — OrderManager（発注フロー コーディネート）
    - order_record.py        — OrderRecord（状態遷移の純粋ロジック）
    - order_repository.py    — SQLite 永続化層
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — 3段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集（defusedxml 等で安全対策）
    - (jquants_client 等 他モジュール)
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite スキーマ / ログ保存
    - system_monitor.py      — 監視ロジック（run_monitoring が使用）
  - utils/
    - logging_setup.py       — ログ初期化
    - process_priority.py    — プロセス優先度設定
    - (その他ユーティリティ)

開発・デバッグのヒント
---------------------
- 自動 .env 読み込みは config.py 内で行われます。テストなどで自動ロードを無効化する場合は
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- YAML のパース検証には PyYAML が必要です。インストールされていない場合は
  validate_config が YAML 内容検証をスキップします（存在チェックのみ行います）。
- ExecutionEngine は PID/kill flag を使って複数プロセスの安全性を確保します。特に本番運用時は
  kill flag の扱いと KILL_FLAG_CLEAR_ON_START の設定に注意してください。
- run_execution は KABUSYS_ENV に応じて sqlite の利用先を切り替えます（paper_trading は専用 DB を使用）。

免責事項
--------
- 本コードベースは教育・開発目的での設計を想定しています。実際の資金を動かす前に十分なレビュー・テストを行ってください。
- 本番環境での利用時は各種設定（認証情報、通知、監視、バックアップ等）を慎重に確認してください。

問い合わせ / コントリビュート
----------------------------
- 仕様改善やバグ報告は Pull Request / Issue を通じてお願いします。
- README に含めてほしい追加情報があればお知らせください。