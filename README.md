KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買を想定した小規模なトレーディングフレームワークです。
主要な責務は以下です。

- シグナルに基づく発注フロー（ExecutionEngine）
- ブローカークライアント抽象化（実働では kabuステーション、テストではモック）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- 起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（RiskManager）
- 監視（SystemMonitor 起動スクリプト）
- 環境設定ウィザード / 設定検証ツール

このリポジトリはモジュール化されており、実際のブローカー接続が不要なペーパートレード（MockBrokerClient）でローカル検証・開発が可能です。

主な機能
--------
- 環境設定ウィザード（.env を対話式に生成・更新）
- 起動前設定検証ツール（.env と config/*.yaml の存在・基本整合性チェック）
- ExecutionEngine：シグナルの読み取り・Gate1/2/3 によるリスク検査・発注・push ドレイン
- Broker API 抽象化（BrokerAPIProtocol）と Mock / KabuStation 実装
- 注文状態の純粋モデル（OrderRecord）と SQLite 永続化
- 起動時リコンシリエーション（OrderSent の突合・ポジション差分検出）
- 監視プロセス（monitoring）用のポーリングスクリプト
- データ処理モジュール（マーケットカレンダー管理、ニュース収集など）

セットアップ手順
----------------
1. Python 環境（3.9+ 推奨）を用意する。仮想環境を推奨します。
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 依存パッケージをインストールします（実プロジェクトでは requirements.txt や poetry を用意してください）。
   - 主要依存例:
     pip install duckdb httpx websocket-client PyYAML defusedxml

   - テストや開発では追加パッケージが必要になることがあります。

3. プロジェクトルートに移動し、.env を準備します。
   - 推奨ワークフロー（対話式ウィザード）:
     python -m kabusys.config_setup
   - あるいは .env を手動で作成（.env.example を参照）してください。

4. 設定検証を実行して不足や警告を確認します:
   python -m kabusys.validate_config
   必要であれば厳格モード（警告も失敗扱い）:
   python -m kabusys.validate_config --strict

5. データディレクトリを作成（必要時）:
   mkdir -p data

使い方
-----
主要なスクリプトと起動方法（いずれもプロジェクトルートで実行）:

- 環境設定ウィザード（.env を生成・更新）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  オプション: --strict（警告も exit(1) とする）

- 実行エンジンを起動（実働セッション）
  python -m kabusys.run_execution
  備考:
  - KABUSYS_ENV によって挙動が変わります。値は development / paper_trading / live のいずれか。
  - paper_trading / development では MockBrokerClient を使用し、実際の発注は行いません。
  - 実行中の停止フラグ: data/stop_requested.flag（存在すると監視・実行プロセスは終了します）。
  - PID ファイル: data/execution.pid（設定で変更可能）。

- 監視ループを起動（SystemMonitor ポーリング）
  python -m kabusys.run_monitoring
  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60）。

主要な環境変数（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。デフォルトは development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — （任意）通知用 LINE 設定
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

注意点
- 自動で .env を読み込む仕組み: プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local を読み込みます。OS 環境変数が優先されます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading 環境では paper 用の SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）に記録され、本番 DB と分離されます。
- 本番（KABUSYS_ENV=live）で警告が多数出る場合は特に注意して設定を確認してください（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
  - パッケージのメタ情報（__version__）

- config.py
  - 環境変数の読み込みロジック（.env 自動ロード）、Settings クラス（アプリ全体の設定アクセサ）
- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine の起動スクリプト（PID 管理、DB 接続、スレッド管理、停止フラグ処理）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - broker_api.py
    - BrokerAPIProtocol、データモデル（OrderRequest / OrderResponse / OrderStatus / Position）、例外クラス、ファクトリ
  - kabu_client.py
    - kabuステーション REST API 実装（httpx、WebSocket）
  - mock_client.py
    - テスト用 MockBrokerClient（fill_mode 等の挙動制御）
  - broker_factory.py
    - Settings に基づいて適切なブローカークライアントを生成
  - execution_engine.py
    - ExecutionEngine 本体（シグナル処理、push ドレイン、kill switch、PID ファイル管理）
  - order_record.py
    - 注文状態の純粋モデル（状態遷移、検証）
  - order_repository.py
    - SQLite 永続化層（orders テーブル定義、CRUD）
  - order_manager.py
    - 注文発行/送信/同期/キャンセルの外向き API（OrderRecord + Repository + Broker）
  - reconciler.py
    - 起動時のリコンシリエーション（OrderSent の突合、ポジション差分検出）
  - risk_manager.py
    - Gate1/2/3 によるリスク管理（余力・重複・ポジション上限、レート制限／サーキットブレーカー、ドローダウン）
  - その他関連モジュール（order_history 等）

- monitoring/
  - monitoring_db.py, system_monitor.py（監視 DB 初期化・監視ロジック）※ run_monitoring で使用

- data/
  - calendar_management.py（マーケットカレンダー管理）
  - news_collector.py（RSS ベースのニュース収集）
  - jquants_client.py（J-Quants API 関連 / カレンダーフェッチ等）

ユーティリティ
- utils/
  - logging_setup.py（ログ設定）
  - process_priority.py（プロセス優先度設定）

補足（運用上のポイント）
---------------------
- kill flag と停止フロー:
  - 実行中に data/kill.flag が存在すると ExecutionEngine は kill_switch を発動して全 active 注文をキャンセルしループを停止します。
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 であれば自動でクリアして起動します（本番では 0 を強く推奨）。

- DB 初期化:
  - 監視 DB（SQLite）や orders テーブルは run_* スクリプト内で初期化関数（init_monitoring_db / init_orders_db）を呼ぶことを想定しています。データディレクトリやパスの権限に注意してください。

- 本番接続:
  - KabuStationClient はローカルで kabuステーション® アプリが起動していることを前提としています（API のベース URL を指定可能）。本番運用時は十分なテストと配慮を行ってください。

ライセンス / 貢献
----------------
- この README にはライセンス情報を含めていません。プロジェクトに適用するライセンスファイル（LICENSE）を追加してください。
- バグ報告や改善提案は Issue を通じてお願いします。

以上がこのコードベースの概要と基本的な使い方です。必要であれば、インストール用の requirements.txt や起動用 systemd ユニットのサンプル、config/*.yaml のテンプレート生成方法などのドキュメントも追加できます。どの部分を詳しく書いてほしいか教えてください。