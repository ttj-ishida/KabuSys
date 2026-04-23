KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／実行スクリプト群です。  
主に以下を提供します。

- 環境変数ベースの設定管理（.env 自動読み込み／設定ウィザード）
- 発注エンジン（ExecutionEngine）と発注フロー（OrderManager / OrderRepository / OrderRecord）
- ブローカークライアント（kabu station 実装 / Mock クライアント）
- リスク管理（3段階ガード: Gate1/2/3、サーキットブレーカー、レート制限、ドローダウン監視）
- リコンシリエーション（起動時の OrderSent 照合・ポジション差分検出）
- 監視プロセス（SystemMonitor のポーリングループ）
- データ系ユーティリティ（マーケットカレンダー、RSS ニュース収集 等）
- 設定検証 CLI（起動前に .env と config/*.yaml をチェック）

主な機能一覧
--------------
- 設定管理
  - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local が上書き）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証ツール: python -m kabusys.validate_config (--strict オプションあり)
- 発注 / 実行
  - ExecutionEngine: シグナルを読み・発注・WebSocket プッシュを処理するセッションランナー
  - Order 管理: OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）、OrderManager（API 連携）
  - ブローカー抽象化: BrokerAPIProtocol、MockBrokerClient、KabuStationClient（httpx ベース）
  - Reconciler: 起動時に OrderSent を照合し自動復旧
- リスク管理
  - Gate1: シグナルレベル（余力、重複、銘柄上限、全体利用率）
  - Gate2: エグゼキューションレベル（トークンバケツによるレート制限、サーキットブレーカー）
  - Gate3: 約定後メトリクス（ドローダウン）チェック
- 監視
  - run_monitoring.py により SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔調整）
- データユーティリティ
  - カレンダー管理（DuckDB 経由、J-Quants 連携想定）
  - ニュース収集（RSS、SSRF/XML インジェクション対策）

セットアップ手順
----------------
前提:
- Python 3.10 以上（型アノテーションに | 演算子を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - pyyaml（YAML 検証を行う場合）
  - その他ログ周りや db ドライバ（sqlite3 は標準組込み）

例（仮想環境作成 & インストール）:
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb httpx websocket-client defusedxml pyyaml

初期設定:
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
   - 既存 .env があれば読み込んで編集できます
2. 作成後、設定検証を実行:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit status 1）

（必要に応じて）依存パッケージはプロジェクト提供の requirements.txt があればそれを使ってください。

重要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

（任意／推奨）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - development / paper_trading: MockBrokerClient を使用（本番発注なし）
  - live: 本番モード。警告や追加チェックが有効になる（本番での運用は慎重に）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に利用、デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番でのアラート通知に使用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）

自動読み込みの挙動:
- 起動時に .env を自動読み込みします（ただし OS 環境変数が優先）
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env 作成）:
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン（発注プロセス）起動:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV によって Mock / Live の動作が変わる
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
- ライブラリとして利用:
  - from kabusys.config import settings
  - settings.jquants_refresh_token などで設定値を参照できます

挙動に関する重要ポイント
------------------------
- paper_trading モード:
  - Broker は MockBrokerClient を使用して実際の発注を行わない
  - DB は paper_sqlite_path（デフォルト data/paper_trading.db）を利用して本番 DB と分離
- リスク管理:
  - Gate1（発注前）で余力・重複・ポジション上限をチェック
  - Gate2（送信前）でレート制限とサーキットブレーカーをチェック
  - Gate3（約定後）でドローダウンをチェックし、NG の場合は kill_switch を発動
- リコンシリエーション:
  - 起動時に OrderSent 状態の注文を broker と照合し状態を回復する
  - broker に注文が見つからない場合は手動確認対象として警告を出す
- kill / stop:
  - 停止フラグ: data/stop_requested.flag（run_monitoring/run_execution で監視）
  - kill.flag（デフォルト data/kill.flag）を検出すると kill_switch を発動して全アクティブ注文をキャンセル
  - 起動時に kill.flag が残っている場合、KILL_FLAG_CLEAR_ON_START により自動クリア（1）か起動拒否（0）かの挙動を制御

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主なファイル／モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数読み込み・Settings クラス（.env 自動ロード含む）
  - config_setup.py            — 対話式 .env 設定ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine を起動するスクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py            — BrokerAPIProtocol、データモデル、ファクトリ
    - kabu_client.py           — kabu station REST API クライアント実装
    - mock_client.py           — MockBrokerClient（テスト用）
    - broker_factory.py        — Settings に応じた Broker 作成ファクトリ
    - order_record.py          — OrderRecord（状態遷移ロジック）
    - order_repository.py      — SQLite を使った永続化層（orders テーブル定義等）
    - order_manager.py         — 外向き API（create/send/sync/cancel）
    - execution_engine.py      — ExecutionEngine（シグナル処理 / push ドレイン 等）
    - reconciler.py            — 起動時リコンシリエーション
    - risk_manager.py          — 3段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py   — マーケットカレンダー管理（DuckDB）
    - news_collector.py        — RSS ニュース収集（SSRF/XML 対策あり）
    - (jquants_client 等 他モジュール)
  - monitoring/
    - monitoring_db.py         — 監視用 DB 初期化 / ログ（init_monitoring_db 等）
    - system_monitor.py        — SystemMonitor 実装（run_monitoring が使用）
  - utils/
    - logging_setup.py         — ロギング初期化ユーティリティ
    - process_priority.py      — プロセス優先度設定ユーティリティ

補足
----
- YAML の内容チェックは PyYAML がインストールされている場合に行われます（validate_config）。
- KabuStationClient は httpx（同期クライアント）を使用しています。将来的な非同期化は httpx.AsyncClient の採用で対応可能です。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- 本番運用（KABUSYS_ENV=live）時は LINE 通知や各種設定を必ず確認してください。validate_config は live 時に追加の注意喚起を行います。

ライセンスや貢献方法、テストの実行方法などはプロジェクトルートに別途ドキュメントを追加してください。

以上。必要であれば README に含めるサンプル .env のテンプレートや具体的な起動例（systemd / supervisor 用の unit ファイル例等）も作成できます。どの情報を追記しますか？