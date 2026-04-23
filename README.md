KabuSys — 日本株自動売買システム
=================================

このリポジトリは KabuSys（日本株自動売買システム）の実装コード群です。  
ここに含まれる主な機能、起動・開発時のセットアップ方法、使い方、ディレクトリ構成をまとめます。

プロジェクト概要
---------------
KabuSys は以下を目的としたモジュール群を含む自動売買フレームワークです。

- シグナルに基づく発注（ExecutionEngine）
- ブローカークライアント（kabu station の実装 / モック実装）
- 注文永続化（SQLite）
- 発注状態管理（OrderRecord の状態遷移ロジック）
- リコンシリエーション（再起動時の復旧）
- 3段階のリスクガード（Gate1/2/3）
- 市場カレンダー管理（DuckDB + J-Quants）
- ニュース収集（RSS）
- 監視プロセス（SystemMonitor）
- 環境設定ウィザード / 設定検証用 CLI

特徴（機能一覧）
----------------
- 設定ウィザード（python -m kabusys.config_setup）で .env を対話式に生成・更新
- 起動前に .env / config/*.yaml を検証する CLI（python -m kabusys.validate_config, --strict オプションあり）
- ExecutionEngine によるシグナルプル型発注（8:50–9:10 シグナル処理、9:10–15:30 push ドレイン）
- ブローカー抽象化（BrokerAPIProtocol）によりモッククライアントでローカル動作可能
- 発注の耐障害性を考慮した 2 相永続化（OrderSent 前後の扱い）と Reconciler による同期
- RiskManager による Gate1/2/3（余力・重複・ポジション上限、レート制限・CB、ドローダウン）
- DuckDB を使ったデータ/カレンダー管理、SQLite を使った監視・注文履歴保存
- WebSocket による kabu station push 処理（存在する場合）

前提・セットアップ
------------------
※実行環境に合わせて適切にセットアップしてください（下記は一般的な手順例）。

1. Python バージョン
   - Python 3.9 以降を想定しています（typing / Path 周りの機能を使用）。

2. 依存パッケージ
   - requirements.txt があれば:
     pip install -r requirements.txt
   - 必須／推奨パッケージ（抜粋）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - pyyaml（config/*.yaml の内容検証を行う場合に必要）
   - PyYAML が未インストールでも validate_config は YAML 検証をスキップしますが、インストールを推奨します:
     pip install pyyaml

3. リポジトリルートの .env
   - .env を作成して環境変数を設定します。対話的に作るには:
     python -m kabusys.config_setup
   - .env と .env.local (存在する場合は上書き読み込み) は起動時に自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にするには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須 / 推奨の環境変数
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabu station API パスワード

- 任意（デフォルトあり／運用で利用）:
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
    - paper_trading: MockBrokerClient を使用して paper_trading 用 DB に記録
    - live: 本番（注: live 用の broker は未実装箇所があります）
  - DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill flag を自動クリアするか（0/1）

主要コマンド・使い方
------------------

- 環境設定ウィザード
  - 実行:
    python -m kabusys.config_setup
  - .env の既存値を読み、対話式で更新・新規作成できます。作成後に validate を推奨。

- 設定検証
  - 実行:
    python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります:
    python -m kabusys.validate_config --strict
  - .env の必須項目未設定、KABUSYS_ENV の不正値、YAML のパースエラー等を検出します。

- 実行エンジンの起動（本番／テスト用スクリプト）
  - ExecutionEngine（発注処理）:
    python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient が使われます。
    - 起動前に stop フラグ (data/stop_requested.flag) があれば起動しません。
    - PID ファイル: data/execution.pid（設定で変更可）
  - Monitoring プロセス（SystemMonitor のポーリング）:
    python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60）。
    - Monitoring は常に sqlite_path を使用します（paper/live にかかわらず本番 sqlite_path を使用する設計）。

- DB 初期化（必要に応じて手動実行）
  - orders テーブルの初期化例:
    python -c "import sqlite3; from kabusys.execution.order_repository import init_orders_db; c=sqlite3.connect('data/monitoring.db'); init_orders_db(c); c.close()"
  - 監視 DB 初期化関数 init_monitoring_db() が用意されています（run_* スクリプトで自動的に呼ばれます）。

運用上の注意
------------
- .env は決して Git にコミットしないこと（config_setup のヘッダにもその旨が記載されています）。
- KABUSYS_ENV=live は本番運用を意味します。validate_config は live 時に特別警告を出します。live では LINE 通知や kill flag の取扱いを必ず確認してください。
- BrokerClientFactory は paper_trading / development ではモッククライアントを返します。live 用クライアントは未実装の箇所があります（起動時に NotImplementedError が出ます）。
- kill flag（data/kill.flag）や stop flag（data/stop_requested.flag）を用いた安全停止機構があります。KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番は 0 推奨）。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数の自動読み込みロジックと Settings クラス（アプリ設定取得）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor 起動スクリプト（python -m kabusys.run_monitoring）
  - execution/
    - broker_api.py — BrokerAPI のデータモデル、Protocol、ファクトリ
    - kabu_client.py — kabu station REST API クライアント実装（httpx 使用）
    - mock_client.py — テスト用 MockBrokerClient（paper_trading 用）
    - broker_factory.py — Settings を使って適切なブローカークライアントを生成
    - order_record.py — 注文状態モデルと状態遷移ロジック（純粋ビジネスロジック）
    - order_repository.py — SQLite を使った永続化層（orders テーブル）
    - order_manager.py — 外向き API（create/send/sync/cancel）と状態管理の調停
    - execution_engine.py — セッション管理・シグナル処理・push ドレイン等のコアロジック
    - reconciler.py — 再起動時のリコンシリエーション（OrderSent の突合せ等）
    - risk_manager.py — Gate1/2/3 の実装（レート制限・CB・ドローダウン等）
  - data/
    - calendar_management.py — JPX カレンダー管理（DuckDB に保存・営業日判定）
    - news_collector.py — RSS ニュース収集（正規化・SSRF 対策など）
    - jquants_client.py —（J-Quants API クライアント想定、fetch/save 実装）
  - monitoring/
    - monitoring_db.py — 監視DBの初期化・ログ保存（init_monitoring_db 等）
    - system_monitor.py — システム監視ロジック（CPU/メモリ/ディスク閾値設定）
  - utils/
    - logging_setup.py — ロギング設定
    - process_priority.py — プロセス優先度設定ユーティリティ
  - config/ (プロジェクト直下)
    - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
      - validate_config が存在確認を行う（PyYAML があれば中身のパース検証も実行）

補足（開発者向け）
-----------------
- 設定の自動読み込み順序:
  OS 環境変数 > .env.local > .env
- validate_config は .env のプレースホルダ値（例: endswith "_here" や "your_value"）を警告にします。
- ExecutionEngine は PID ファイルや kill.flag を用いた起動制御を行います。再起動時の自動復旧は Reconciler に依存します。
- MockBrokerClient の PAPER_FILL_MODE（instant|partial|never|reject）で開発時の挙動を切り替え可能。Settings.paper_fill_mode で制御。

ライセンス・貢献
----------------
（この README ではライセンス情報・貢献ガイドは省略しています。必要に応じてリポジトリの LICENSE / CONTRIBUTING を参照してください。）

以上が本コードベースの概要・基本的な使い方・構成説明です。  
具体的な実行や追加の開発手順については、各モジュールの docstring・ソースコメントを参照してください。