# KabuSys

日本株向け自動売買システムのプロジェクト骨格。発注ロジック・注文管理・リスクガード・モニタリング・データ収集などの主要コンポーネントを含むモジュール群です。

## 概要
KabuSys は、kabuステーション（ローカル REST/WebSocket API）や J-Quants 等を利用して取引シグナルを実行するためのフレームワークです。本リポジトリは以下を提供します。

- 発注エンジン（ExecutionEngine）
- 注文状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカークライアント（実装: MockBrokerClient、実装予定: KabuStationClient）
- リスク管理（3段階ガード: Gate1/2/3）
- 起動時リコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor をポーリングする run_monitoring）
- 環境設定ウィザード（.env 生成）と設定検証ツール

## 主な機能
- シグナルを DuckDB から読み込み、発注フローを実行
- 注文の永続化（SQLite）と状態遷移の検証
- 発注時のクラッシュ耐性を考慮した2相永続化設計（OrderSent 前後の保全）
- 3段階リスクガード（シグナルレベル、エグゼキューションレベル、メトリクスレベル）
- MockBroker によるペーパートレード・開発/テスト支援（fill_mode: instant/partial/never/reject）
- .env 対話式ウィザード（config_setup）および起動前の設定検証 CLI（validate_config）
- マーケットカレンダー管理・ニュース収集などのデータモジュール

## 前提条件
- Python 3.9+
- SQLite（標準ライブラリ）
- DuckDB（pip パッケージ: duckdb）
- httpx, websocket-client（実際の kabu ステーション実装を使う場合）
- defusedxml（news_collector）
- PyYAML（設定検証で YAML パースを行う場合）

例:
pip install duckdb httpx websocket-client defusedxml pyyaml

※プロジェクトに requirements.txt がある場合はそれを利用してください。

## セットアップ手順（ローカル開発向けの最小手順）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化（例: python -m venv .venv && source .venv/bin/activate）
3. 必要パッケージをインストール
   - 例: pip install duckdb httpx websocket-client defusedxml pyyaml
4. 環境変数ファイルを作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成
5. 設定を検証: python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

## 主要な環境変数（抜粋）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意／設定推奨:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading の場合に使用）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabuステーションのベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（live で推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1、デフォルト 0)

監視関連:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

停止フラグ / PID:
- PID / flag ファイルはデフォルトで data/ 下に作成されます（例: data/execution.pid, data/stop_requested.flag, data/kill.flag）

## 使い方（コマンド）
- 環境ウィザード（.env を対話的に作成/更新）
  - python -m kabusys.config_setup

- 設定検証（起動前のチェック）
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン起動（発注プロセス）
  - python -m kabusys.run_execution
  - 途中で停止させたいときはプロセスを終了、またはプロジェクトルートの data/stop_requested.flag を作成

- 監視プロセス起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能

## 開発者向けメモ
- MockBrokerClient（kabusys.execution.mock_client）はテストで使いやすく、fill_mode によって実際の約定挙動を模擬できます。
- 実際の kabu ステーションクライアントは KabuStationClient（kabusys.execution.kabu_client）に実装済み。create_broker_api で mock/real を切り替えられます。
- ExecutionEngine はセッションルール（8:50 発注処理、9:10 発注締切、15:30 セッション終了）に従って動作します。テストでは _process_signals や _drain_push_queue を直接呼ぶことが想定されています。
- 注文状態の不整合解消（クラッシュ後の復旧）は Reconciler が担当します。OrderSent のまま残った注文は sync_order で復旧を試みます。
- データベース初期化: orders テーブルは init_orders_db（order_repository）で冪等に作成されます。監視 DB 初期化関数 init_monitoring_db が存在します（monitoring モジュール）。

## 停止・安全機構
- kill.flag（デフォルト data/kill.flag）を設置すると発注ループは kill_switch を呼び、全 active 注文をキャンセルして停止します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。
- run_monitoring と run_execution は data/stop_requested.flag を検知してループを終了します。
- ExecutionEngine は PID ファイルを書き込みます（デフォルト data/execution.pid）。終了時に削除されます。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 下の主要ファイルと簡単な説明です。

- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数の自動読み込み・Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI

- run_execution.py — ExecutionEngine を起動するスクリプト
- run_monitoring.py — 監視ループを起動するスクリプト

- execution/
  - broker_api.py — BrokerAPI のデータモデル・Protocol・例外・ファクトリ
  - kabu_client.py — kabuステーション向け HTTP/WebSocket クライアント（実装）
  - mock_client.py — 開発用 MockBrokerClient（fill_mode を指定可能）
  - broker_factory.py — Settings に応じたクライアント生成
  - order_record.py — OrderRecord（状態遷移ロジック）
  - order_repository.py — SQLite 永続化（orders テーブル管理）
  - order_manager.py — 発注フロー（create/send/sync/cancel）の外向き API
  - execution_engine.py — 発注エンジン本体（セッション制御 / push ドレイン）
  - reconciler.py — 起動時のリコンシリエーション（OrderSent 照合 / ポジション差分）
  - risk_manager.py — Gate1/2/3 のリスク制御

- data/
  - calendar_management.py — JPX カレンダー管理（J-Quants API 経由の更新ロジック）
  - news_collector.py — RSS ニュース収集・前処理・保存ロジック

- monitoring/ (参照のみ: 実装ファイルが存在する前提)
  - monitoring_db.py — 監視 DB 初期化・書き込みユーティリティ（init_monitoring_db 等）
  - system_monitor.py — システム監視ロジック（ポーリングで各種メトリクス収集）

- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ

（上記はソース内の import 参照に基づく主要ファイルの抜粋です。実際のファイル一覧はリポジトリのツリーを参照してください。）

## 例: よく使うコマンドまとめ
- .env を作る（対話式）:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 実行エンジン起動（開発・ペーパートレード）:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring

## 注意事項
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- KABUSYS_ENV=live を設定すると本番発注が行われます。設定・アラート周りを十分に検証してください。
- 本コードベースは一部機能（例: Live の本番ブローカークライアント）を未実装とする箇所があり、デフォルトでは mock を使用する設計です。

---

問題や拡張したい箇所（テストの書き方、CI での validate 実行、requirements.txt の整備など）があれば教えてください。README に追記します。