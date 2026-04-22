KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買を想定した小規模なトレーディングフレームワークです。  
主な役割はシグナルに基づく発注（ExecutionEngine）、発注の永続化・復旧（OrderRepository / Reconciler）、ランタイムの監視（SystemMonitor）、および環境設定・検証ツールの提供です。

本リポジトリはローカル開発 / ペーパートレードを念頭に設計されており、実ブローカー（kabuステーション）を使う本番連携は限定的（KabuStationClient は実装済みだがファクトリは paper/dev を優先）です。KABUSYS_ENV=live の完全運用は慎重に扱ってください（README 参照）。

主な機能
--------
- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検査）: kabusys.validate_config
- 発注エンジン（ExecutionEngine）: シグナル読み込み → Gate1/2 リスク検査 → 発注 → リコンシリエーション
- ブローカー抽象化: MockBrokerClient（テスト／ペーパー用）、KabuStationClient（kabuステーション REST / WebSocket）
- 注文状態管理（OrderRecord の状態遷移ロジック）
- 注文永続化（SQLite に orders テーブルを保存）
- リコンシリエーション（OrderSent の突合せとポジション差分検出）
- 監視ループ（SystemMonitor を周期的に実行、Monitoring sqlite DB を使用）
- データ処理補助（DuckDB を用いたシグナル/カレンダー/ニュース収集のユーティリティ）

セットアップ手順
----------------
1. Python 環境を用意する（3.9+ 推奨）。
2. 依存パッケージをインストール（例）:
   - duckdb
   - httpx
   - websocket-client
   - pyyaml (設定検証で必要)
   - defusedxml (ニュース収集で使用)
   例:
     pip install duckdb httpx websocket-client pyyaml defusedxml
   ※ sqlite3 は標準ライブラリです。

3. プロジェクトルートに .env を配置する（自動ロード機能あり）。
   - 自動ロード順: OS 環境 > .env.local > .env
   - 自動ロードを無効にする場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. .env の生成を支援するウィザードを実行:
     python -m kabusys.config_setup
   - 対話式で主要な環境変数を設定できます。
   - 生成した .env は絶対に Git にコミットしないでください。

5. 設定を検証:
     python -m kabusys.validate_config
   - --strict を付けると警告も FAIL（exit code 1）になります。
   - PyYAML がない場合は YAML の中身検証がスキップされます（警告）。

主要な環境変数
----------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意 / よく使う:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL: kabuステーション API（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START: 0|1（デフォルト 0。本番では 0 推奨）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

- Paper trading 特有:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

使い方（主なスクリプト）
-----------------------
- 環境ウィザード（.env 作成）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番相当の発注フロー実行）
    python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading / development の場合は MockBrokerClient を使用します（create_broker_api(mock=True)）。
  - KABUSYS_ENV=live を選ぶと live ブローカーは NotImplementedError が投げられる設計箇所があります。実ブローカー接続は十分な確認のもとで使用してください。
  - 起動時に data/execution.pid（デフォルト）へ PID を書き込みます。停止は data/stop_requested.flag（run scripts が検出）や data/kill.flag により制御されます。

- 監視ループを起動
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視は常に（環境にかかわらず）本番 sqlite_path を使用します。

実装上の注意・ポリシー
---------------------
- .env は機密情報（API トークン・パスワード）を含むため Git 等へコミットしないこと。
- Settings モジュールは起動時にプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑制できます。
- 発注フローはクラッシュ耐性を考慮して設計されています（OrderSent の永続化、broker_order_id の早期保存、Reconciler による復旧）。
- Paper trading（mock）と Live（実ブローカー）は明確に分離されているため、テスト環境で動作確認を行ってから本番に移行してください。
- 設定検証ツールは config/*.yaml の有無や YAML のパースをチェックします（PyYAML が必要）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                   — 環境変数読み込み / Settings
- config_setup.py             — .env 対話式ウィザード
- validate_config.py          — 設定検証 CLI

- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト

- execution/
  - __init__.py
  - broker_api.py              — Broker API の Protocol / データモデル / ファクトリ
  - broker_factory.py          — Settings に基づくクライアント生成
  - kabu_client.py             — kabuステーション REST/WebSocket クライアント
  - mock_client.py             — テスト用 MockBrokerClient
  - order_record.py            — 注文の状態遷移ロジック（純粋ロジック）
  - order_repository.py        — SQLite 永続化層（orders テーブルの init も）
  - order_manager.py           — 外向き API（作成 / 送信 / 同期 / キャンセル）
  - execution_engine.py        — 発注エンジン本体（シグナル処理・push drain）
  - reconciler.py              — リコンシリエーション（復旧）
  - risk_manager.py            — 3段階リスクガード（Gate1/2/3）

- monitoring/                  — 監視関連（SystemMonitor, monitoring_db 等）
- data/
  - calendar_management.py     — マーケットカレンダー管理（JPX / J-Quants 連携想定）
  - news_collector.py          — RSS ニュース収集（安全対策あり）

その他ファイル
- config/*.yaml                — 各種設定ファイル（存在しない場合は警告）
- data/                        — デフォルトで DB / flag / pid を置く場所（自動作成）

運用関連
--------
- PID ファイル: PID_FILE_PATH 環境変数（デフォルト data/execution.pid）
- 停止フラグ: data/stop_requested.flag（run スクリプトが監視）
- Kill スイッチ: KILL_FLAG_PATH（デフォルト data/kill.flag）。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると起動時に自動クリアされるため本番では 0 を推奨。
- 監視 DB 初期化: run_monitoring/run_execution 内で init_monitoring_db が呼ばれます（ファイルがなければ作成されます）。

トラブルシューティング
----------------------
- validate_config が警告やエラーを出す場合は .env の未設定やプレースホルダ（your_value/_here）が残っていないか確認してください。
- config/*.yaml が無ければ generate スクリプト（scripts/generate_config.py）で生成する想定です（プロジェクトに scripts がある場合）。
- PyYAML がないと YAML の内容検証をスキップします。YAML まで検証したい場合は pyyaml をインストールしてください。

貢献とライセンス
----------------
- 本リポジトリの設計方針に沿って、まずはローカル・ペーパートレード環境で十分テストを行ってください。  
- 機密情報（.env）は絶対に公開リポジトリへコミットしないでください。

以上。必要であれば README にサンプル .env のテンプレート（例）や起動コマンドの実例、よくある設定例（development / paper_trading 用）を追記します。どの程度の詳細を追加しますか？