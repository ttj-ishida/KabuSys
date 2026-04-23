README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
環境変数ベースで設定を管理し、発注エンジン（ExecutionEngine）、監視プロセス（SystemMonitor）、ブローカークライアント（Mock / KabuStation）などの主要コンポーネントを備えています。  
このリポジトリ内のスクリプトとモジュールは、ローカル開発 / ペーパートレード / 本番（live）といった実行環境を想定して設計されています。

主な機能
--------
- 環境変数（.env）自動読み込みと対話式セットアップウィザード
  - python -m kabusys.config_setup で .env を作成・更新可能
  - OS 環境変数 > .env.local > .env の優先順で読み込む
- 設定検証 CLI
  - python -m kabusys.validate_config により .env と config/*.yaml の検証（エラー / 警告 / 情報出力）
  - --strict オプションで警告も失敗扱いにできる
- ExecutionEngine
  - シグナル Pull 型の発注フロー（シグナル処理 + WebSocket push ドレイン）
  - 3段階のリスクガード（Gate 1: シグナル、Gate 2: エグゼキューション、Gate 3: ドローダウン監視）
  - Paper Trading 用の Mock ブローカー実装を同梱（設定で選択）
  - リコンシリエーション（起動時の OrderSent 状態の同期）
- ブローカークライアント層
  - KabuStationClient（kabuステーション REST API 実装）と MockBrokerClient（テスト用）
  - 共通の Protocol / データモデル / 例外クラスを提供
- 監視モジュール
  - SystemMonitor のポーリングループ（run_monitoring.py）
  - 監視用 SQLite / DuckDB への接続と初期化を取り扱う
- データモジュール
  - マーケットカレンダー管理（営業日判定、カレンダー更新ジョブ）
  - ニュース収集（RSS 取り込み、前処理、SSRF 対策等）

要件（推奨）
-----------
- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - pyyaml (config/*.yaml のパース検証用)
  - defusedxml (RSS パースの安全化)
- SQLite（組み込みの sqlite3 を使用）
- （本番で KabuStation を使う場合）kabuステーション® アプリまたはそれに類するモックサーバ

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix/macOS) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 例（requirements.txt が無ければ以下を参考に）:
     - pip install duckdb httpx websocket-client pyyaml defusedxml

4. .env を作成する（対話式）
   - python -m kabusys.config_setup
   - ウィザードに従い必要項目（特に JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD）を設定してください。
   - .env ファイルは絶対に Git にコミットしないでください（ウィザードのヘッダにも記載）。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も含めて CI 等で失敗させたい場合:
     - python -m kabusys.validate_config --strict

使い方（主要スクリプト）
-----------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成 / 更新を対話形式で行う

- 設定検証
  - python -m kabusys.validate_config
  - 出力: INFO / WARNING / ERROR（エラーがあれば exit code 1）
  - --strict を付けると warning も失敗扱い（exit code 1）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を使用します（KABUSYS_ENV に依存しない）

- ExecutionEngine 起動（実際の発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって動作モードが変わる：
    - development: MockBrokerClient（発注なし / 開発用）
    - paper_trading: MockBrokerClient（発注は記録のみ、paper_trading 用 DB に格納）
    - live: 実ブローカークライアントの利用を想定（本実装では NotImplementedError の場合あり）
  - paper_trading 実行時はデフォルトで data/paper_trading.db を使用し、本番 DB と分離

- 停止制御 / PID / Kill Flag
  - 停止フラグファイル: project_root/data/stop_requested.flag
  - ExecutionEngine の PID ファイル: data/execution.pid（設定で変更可能）
  - Kill スイッチ: settings.kill_flag_path（デフォルト data/kill.flag）
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START に応じて起動を拒否または自動クリア

主要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — execution モード (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート通知に使用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0 | 1)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の fill 動作（instant | partial | never | reject）

.env 自動読み込み
-----------------
- 起動時は OS 環境変数 > .env.local > .env の順で読み込まれます。
- 自動読み込みを無効化する場合：
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

簡単な .env の例
----------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（抜粋）
----------------------
プロジェクトルート（省略可能なファイルや設定が存在）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env ウィザード CLI
    - validate_config.py       — 設定検証 CLI
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py          — Broker API の Protocol / データモデル / 例外 / ファクトリ
      - kabu_client.py         — KabuStation REST クライアント
      - mock_client.py         — MockBrokerClient
      - broker_factory.py      — Settings に基づくクライアント生成
      - order_record.py        — 注文状態モデル（純粋ロジック）
      - order_repository.py    — SQLite 永続化層
      - order_manager.py       — 発注フローの外向き API（State Machine 制御）
      - execution_engine.py    — 発注エンジン本体（Signal Pull + Push Drain）
      - reconciler.py          — 起動時リコンシリエーション
      - risk_manager.py        — 3段階リスクガード
      - ...（他サブモジュール）
    - data/
      - calendar_management.py — マーケットカレンダー管理
      - news_collector.py      — RSS ニュース収集
      - ...（J-Quants クライアント等）
    - monitoring/
      - monitoring_db.py       — 監視 DB 初期化・ロギング
      - system_monitor.py      — 監視ロジック
    - utils/
      - logging_setup.py       — ロギング設定ユーティリティ
      - process_priority.py    — プロセス優先度設定
    - strategy/                — 戦略関連（存在する場合）
    - ...（その他）

注意事項 / 運用上のポイント
---------------------------
- 本リポジトリの .env は機密情報を含むため、絶対に Git にコミットしないでください。
- KABUSYS_ENV=live を設定する場合は慎重に。validate_config は live を検出すると警告を出します（LINE 通知等の設定を確認すること）。
- run_execution は stop フラグ / PID / kill.flag を利用して安全停止・起動制御を行います。運用時にはこれらのファイル位置に注意してください。
- Paper trading と本番 DB は分離（paper_trading 用の DB を使用）されていますが、DuckDB は共通で使われる点に留意してください（必要に応じてパスを分離してください）。
- config/*.yaml の検証には PyYAML が必要です。インストールされていない場合は検証をスキップして警告を出します。

貢献 / 開発
------------
- 開発用ブランチルールやコントリビュートポリシーはプロジェクトの CONTRIBUTING.md（存在する場合）を参照してください。
- テスト、CI 設定、デプロイ手順は別途ドキュメント化することを推奨します。

ライセンス
----------
- 本 README ではライセンスに触れていません。実際の配布では適切な LICENSE ファイルをプロジェクトルートに配置してください。

以上。必要であれば README に追加したい情報（CI 手順、デプロイ例、詳細な環境変数一覧の表、サンプル .env.example 等）を教えてください。