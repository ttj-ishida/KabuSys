KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買システム用のコンポーネント群です。  
主な機能は、発注エンジン（ExecutionEngine）、発注状態管理、リスクガード、リコンシリエーション、監視（SystemMonitor）およびデータ/ニュース収集などの補助機能を提供します。  
本リポジトリはコンポーネントをモジュール化しており、ローカル開発やペーパートレード環境で動作することを想定しています（本番用ブローカークライアントは未実装の箇所があります）。

特徴（主な機能）
----------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup で対話式に .env を生成・更新できます。
- 設定検証ツール
  - python -m kabusys.validate_config で .env や config/*.yaml の不足や誤りを起動前に検出（--strict で警告も FAIL 扱い）。
- 実行エンジン（ExecutionEngine）
  - シグナルを読み取り Gate1/Gate2/Gate3 のリスクチェックを経て発注。
  - ペーパートレード時は MockBrokerClient を使用し、本番 DB と分離された SQLite を利用可能。
- ブローカークライアント層
  - MockClient（テスト用）、KabuStationClient（kabuステーション REST API 実装）を提供。
- 注文永続化（SQLite）
  - OrderRepository による永続化、リコンシリエーション用の list_uncertain 等のサポート。
- リスク管理
  - 3段階のリスクガード（シグナル単位・送信前・約定後メトリクス）。
  - サーキットブレーカー・レート制限等を備える。
- 監視ループ
  - run_monitoring.py による定期的なシステム監視（MONITOR_POLL_INTERVAL で間隔指定）。
- データユーティリティ
  - DuckDB を用いたマーケットカレンダー管理、RSS ニュース収集（SSRF/XML 脆弱性対策実装済み）。

セットアップ手順
----------------

1. 前提
   - Python 3.10 以上（typing の添字構文や | 型合成を利用）。
   - system に sqlite3 があれば標準モジュールで利用可能。
   - DuckDB を利用するため duckdb パッケージが必要。

2. 仮想環境 & パッケージ（例）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - 必要なライブラリをインストール（プロジェクトに requirements.txt がない場合の推奨パッケージ）
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   推奨パッケージ一覧（最低限）
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config/*.yaml のパース検証を行うために推奨）

3. .env の作成
   - 対話式ウィザードで作成（推奨）
     - python -m kabusys.config_setup
   - ウィザード実行後、生成された .env を編集して必要情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を適切に設定してください。

4. 設定の自動読み込み
   - ライブラリは起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env を自動読込します。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD     — kabuステーション API パスワード

- 任意 / デフォルト
  - KABUSYS_ENV           — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH           — DuckDB パス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL             — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - KABU_API_BASE_URL     — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1, デフォルト: 0）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）

使い方（主要コマンド）
--------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成/更新します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告もエラー扱いで exit 1）
  - config/*.yaml の有無や .env の必須環境変数をチェックします。PyYAML がない場合は YAML 内容検証はスキップされます。

- 実行エンジン（本番/ペーパートレード共通インターフェース）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって mock (= paper_trading / development) または live の挙動が変わります。
  - paper_trading は settings.paper_sqlite_path（data/paper_trading.db 等）に記録され、本番 DB と分離されます。

- 監視ループ
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔変更可能（デフォルト 60秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- 停止 / 制御ファイル
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して停止します。
  - settings.kill_flag_path（デフォルト data/kill.flag）を用いた kill switch 機構により、起動中のエンジンを安全に停止できます。

実行環境別の注意点
-------------------
- development / paper_trading
  - MockBrokerClient が使われ、外部 kabu station は不要。PAPER_FILL_MODE によって発注のモック挙動を制御できます:
    - instant / partial / never / reject
- live
  - live 設定は本番挙動を想定します。WARNING: 本番環境では LINE 通知などの設定や kill flag の取り扱いを十分確認してください。
  - 現在 BrokerClientFactory は live クライアントを未実装（NotImplementedError）箇所あり。利用前に実装が必要です。

. env ファイル例（抜粋）
-----------------------
以下は .env の例です（機密情報はダミー表示）。config_setup で生成されるフォーマットに準拠しています。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込みと Settings クラス（自動 .env ロード含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPI の Protocol、データモデル、ファクトリ
    - kabu_client.py         — kabu station REST API クライアント（httpx）
    - mock_client.py         — テスト用 MockBrokerClient
    - broker_factory.py      — Settings に基づくクライアント生成
    - order_record.py        — 注文状態と状態遷移ロジック（純粋ロジック）
    - order_repository.py    — SQLite による永続化層
    - order_manager.py       — OrderRecord + Repository + Broker を統合する外向き API
    - execution_engine.py    — セッション実行ロジック（シグナル処理・push ドレイン・kill）
    - reconciler.py          — 起動時リコンシリエーション（OrderSent 照合等）
    - risk_manager.py        — 3段階リスクガード

  - monitoring/
    - monitoring_db.py       — 監視用 DB 初期化 / ログ
    - system_monitor.py      — システム監視ロジック（使用: run_monitoring）

  - data/
    - calendar_management.py — カレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集 / 前処理

  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

運用に関する注意
-----------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）での起動時は LINE 通知設定や kill_flag の取り扱い、DB パス、ログレベルなどを必ず確認してください。
- Reconciliation やリスクガードの動作は設計に依存しているため、プロダクション導入前に充分なテストを行ってください。
- KabuStationClient はローカル上の kabuステーションアプリ（REST API）への接続を想定しているため、実際の接続環境の準備が必要です。

開発・テストに便利なヒント
-------------------------
- テストやローカルデバッグ時は KABUSYS_ENV=development または paper_trading を使うと MockBrokerClient が利用でき外部依存が不要です。
- validate_config を先に実行して設定漏れを検出してください。
- run_execution/run_monitoring は停止トリガーとして data/stop_requested.flag を利用します（ファイル作成で安全に停止を促す）。

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

サポート / 追加実装メモ
----------------------
- Live 用の KabuStationClient の完全な運用検証（生産ブローカーとの連携）や、監視アラート（LINE 等）の本番向け堅牢化は今後の実装・検証が必要です。
- その他補助スクリプト（config/generate_config.py 等）はリポジトリに存在する場合それらも利用できます。validate_config は config/*.yaml の存在もチェックします。

以上が README の概要です。必要であればさらに具体的なコマンド例、起動オプション、テスト手順や DB スキーマの詳細（orders テーブル定義など）を追加できます。どの部分を詳しく出力しますか？