KabuSys
======

概要
----
KabuSys は日本株の自動売買システムの基礎実装です。  
シグナルに基づく発注フロー、注文状態管理、リスクガード（3段階）、リコンシリエーション、監視ループ、マーケットカレンダーやニュース収集などのコンポーネントを備えています。  
設計方針は「DB とブローカ API を分離し、クラッシュ耐性・再起動時自動復旧（Reconciliation）を実現する」ことにあります。

主な機能
--------
- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 対話式ウィザードで .env を生成・更新（python -m kabusys.config_setup）
  - 起動前に設定を検証する CLI（python -m kabusys.validate_config）
- 実行エンジン（ExecutionEngine）
  - シグナルプル方式の発注（シグナル処理時間帯、ドレインループ）
  - OrderRecord を用いた状態遷移（状態遷移検証を含む）
  - OrderManager / OrderRepository による永続化と broker 連携
  - 3段階のリスクガード（Gate1: シグナル，Gate2: 実行，Gate3: メトリクス）
  - リコンシリエーション（起動時に OrderSent の不確定注文を照合）
- ブローカークライアント
  - MockBrokerClient（paper_trading / development 用、fill_mode 切替可能）
  - KabuStationClient（kabuステーション REST API 実装、未使用時は Mock を利用）
  - create_broker_api ファクトリで切替
- 監視（Monitoring）
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
  - 監視データ保存用の SQLite を使用（監視は本番 sqlite_path を参照）
- データ関連
  - DuckDB を利用したシグナル・カレンダー等の分析基盤
  - マーケットカレンダー管理（J-Quants からの差分更新 / フォールバック）
  - ニュース収集モジュール（RSS 取得、正規化、SSRF 回避等の安全対策）

セットアップ手順
--------------
1. リポジトリをチェックアウトする（プロジェクトルートに pyproject.toml / .git が存在する想定）。

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が存在する場合はそれを利用してください。なければ最低限以下が必要です:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml (config/*.yaml のパース検証を行いたい場合)
     - defusedxml (ニュース取得で使用)
   - 例:
     - pip install duckdb httpx websocket-client pyyaml defusedxml

4. 環境変数ファイルの作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を手動で作成する。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - デフォルトの DB パスは data/ 以下にあるため、権限やディレクトリ構成を確認してください。

利用方法（実行例）
-----------------
- 設定ウィザード（.env の生成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告を FAIL として exit(1)）
    - python -m kabusys.validate_config --strict

- 実行エンジン（発注プロセス）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（data/paper_trading.db）に記録します。
    - KABUSYS_ENV=live は注意喚起があり、BrokerClientFactory では未実装（NotImplementedError）とする設計です。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL 環境変数（秒）を設定

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

オプション（重要なもの）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）
- KABU_API_BASE_URL（kabu station の base URL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。デフォルト 0）

自動読み込みの仕様:
- 起動時にプロジェクトルート（.git または pyproject.toml がある場所）を探し、.env を読み込みます。
- 優先度: OS 環境変数 > .env.local > .env
- テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

簡易 .env 例
-------------
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

（注意: .env は絶対にリポジトリにコミットしないでください）

プロセス制御とフラグ
-------------------
- PID ファイル（デフォルト: data/execution.pid）にプロセス ID を書き込みます。
- 停止・停止要求:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring はループを終了します（スクリプト側で監視）。
  - data/kill.flag は ExecutionEngine の kill switch トリガーに利用されます。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアできますが、本番では推奨されません。

注意事項
--------
- KABUSYS_ENV=live の場合は本番運用となります。LINE 通知やその他設定の確認を必ず行ってください。validate_config は live 時に追加警告を出します。
- Broker の実際の Live クライアントは現状未実装（BrokerClientFactory は live 時に NotImplementedError を投げます）。paper_trading / development は MockBrokerClient を使って安全に動作確認可能です。
- config/*.yaml（system_config.yaml など）の存在は期待されますが、PyYAML がインストールされていない場合はパース検証がスキップされます（validate_config 上の挙動）。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py                 — パッケージ定義（__version__ 等）
  - config.py                   — 環境変数 / Settings 管理（自動 .env ロード、Settings クラス）
  - config_setup.py             — .env 対話式ウィザード CLI
  - validate_config.py          — 起動前の設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — 監視ループ起動スクリプト
  - execution/
    - broker_api.py             — ブローカ API の Protocol / データモデル / ファクトリ
    - kabu_client.py            — KabuStation REST API クライアント
    - mock_client.py            — MockBrokerClient（テスト用）
    - broker_factory.py         — 設定に応じたクライアント生成
    - order_record.py           — OrderRecord（状態遷移ロジック）
    - order_repository.py       — SQLite 永続化層（orders テーブル）
    - order_manager.py          — 注文管理（作成・送信・同期・キャンセル）
    - execution_engine.py       — ExecutionEngine（セッション管理・シグナル処理）
    - reconciler.py             — リコンシリエーション（再起動時復旧）
    - risk_manager.py           — リスクガード（Gate1/2/3）
  - monitoring/
    - monitoring_db.py          — 監視データ DB 初期化 / ログ関数
    - system_monitor.py         — システム監視ロジック（別途実装想定）
  - data/
    - calendar_management.py    — マーケットカレンダー管理（J-Quants 連携）
    - news_collector.py         — RSS ニュース収集・正規化
  - utils/
    - logging_setup.py          — ロギング設定ユーティリティ
    - process_priority.py       — プロセス優先度設定ユーティリティ

開発・拡張メモ
---------------
- ブローカ実装: 現在 MockBrokerClient が充実しているため、テストは Mock でほぼ網羅可能。実ブローカを追加する場合は broker_api.BrokerAPIProtocol を実装してください。
- リコンシリエーション: 起動時に OrderSent の不確定注文を突合する処理が組み込まれています。DB スキーマの安定性が重要です。
- カレンダー更新（J-Quants 経由）やニュース取得は外部 API に依存するため、API キーやネットワークのエラー処理に注意してください。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンス情報や貢献方法を記載してください）

以上が KabuSys の概要と使い方です。設定作成 → 設定検証 → 実行（paper_trading で動作確認）という流れで試してください。必要であれば各モジュールの詳細なドキュメントも作成します。