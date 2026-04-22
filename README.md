README — KabuSys
=================

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システム向けのライブラリ／実行フレームワークです。本リポジトリには以下の主要機能が含まれます:

- シグナルに基づく注文発行の実行エンジン (ExecutionEngine)
- ブローカー API クライアント（kabuステーション 実装 & Mock クライアント）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- 起動時のリコンシリエーション（Reconciler）
- リスク制御（RiskManager: Gate1/2/3）
- 監視プロセス（SystemMonitor 起動スクリプト）
- 環境設定ウィザード (.env 生成) と設定検証ツール（YAML/.env の事前チェック）
- データ処理ユーティリティ（DuckDB を使ったカレンダー管理、ニュース収集など）

主に本番／ペーパートレード／開発（development）モードを切り替えて動作させる設計です。

機能一覧
---------
- 環境変数管理と .env 自動ロード（Settings）
- 対話式 .env ウィザード（config_setup.py）
- 起動前の設定検証 CLI（validate_config.py）: 必須環境変数欠如や config/*.yaml の構文チェック
- ExecutionEngine: シグナル取得 → Gate1/2 による検査 → 発注 → push ドレイン
- Broker クライアントファクトリ: Mock と KabuStation 実装を切替
- Order 管理: 永続化（SQLite）／状態遷移検証／送信・同期・キャンセル
- Reconciler: 起動時に OrderSent の不確定注文をブローカーと照合して復旧
- RiskManager: 余力・重複・ポジション上限・レート制限・サーキットブレーカー・ドローダウン監視
- 監視ループ起動スクリプト（run_monitoring.py）: SQLite + DuckDB 利用
- データモジュール: カレンダー管理、ニュース収集など

前提（依存関係）
----------------
少なくとも以下を備えた Python 環境を想定しています（バージョンはプロジェクト方針に従ってください）。

推奨インストールパッケージ（一例）:
- duckdb
- httpx
- websocket-client
- PyYAML (validate_config で YAML 検証を行う場合)
- defusedxml
- その他標準ライブラリ（sqlite3, logging 等）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（requirements.txt がない場合は下記を個別に pip）。
   - pip install duckdb httpx websocket-client PyYAML defusedxml

   （パッケージは環境・用途に応じて調整してください）

3. プロジェクトルートに .env を配置します。対話式ウィザードで作ることもできます（後述）。

環境設定 (.env)
---------------
本プロジェクトは .env（および .env.local）をプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨／任意:
  - KABUSYS_ENV — execution 環境: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station base URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知設定（本番で推奨）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアする（0/1、デフォルト 0）

.env の生成は対話式ウィザードを推奨（下記参照）。

使い方
------

1) 環境の対話式作成（.env ウィザード）
   - python -m kabusys.config_setup
   - 既存の .env を読み込んで編集できます。最後に .env を保存するか確認されます。

2) 起動前の設定検証
   - python -m kabusys.validate_config
     - warnings を FAIL として扱う厳格モード: --strict
   - exit コード:
     - 0: OK（致命的なエラー無し / 警告ありでも非 strict）
     - 1: エラーあり、または --strict で警告あり

3) ExecutionEngine を起動（実行スクリプト）
   - python -m kabusys.run_execution
   - 実行概要:
     - settings によって paper_trading なら MockBrokerClient を使用し、本番 DB と分離された paper_trading 用 SQLite を使用
     - PID ファイル（デフォルト data/execution.pid）を作成
     - data/stop_requested.flag（または kill.flag）による外部停止機構に対応
     - セッションの流れ:
       - 起動時に Reconciler による同期（設定されている場合）
       - 8:50 にシグナル処理ループ（発注）を実行（設定で変更可）
       - 9:10〜15:30 の間は WebSocket push のドレイン処理
   - 注意:
     - 本番モード（KABUSYS_ENV=live）は Live broker の実装が未実装の箇所があるため、paper_trading/development をお勧めします

4) 監視ループを起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（デフォルト 60 秒）。
   - 監視は sqlite_path を使用（環境にかかわらず本番 sqlite_path を参照する設計）

5) 実装済みの Broker クライアント
   - MockBrokerClient: テスト／開発で即座に利用可能（fill_mode により挙動を変えられる）
   - KabuStationClient: kabuステーション REST API 実装（httpx 使用）。本番接続には kabuステーション の起動・設定が必要。

運用上の注意点
--------------
- kill.flag / stop_requested.flag:
  - 実行中の停止指示はファイル（data/kill.flag など）の存在で検知されます。kill.flag が存在する状態での起動は基本拒否されます（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動可能）。
- PID ファイル:
  - ExecutionEngine は起動時に PID ファイルを書きます（デフォルト data/execution.pid）。終了時に削除されます。
- 設定検証:
  - validate_config は .env と config/*.yaml の存在や形式をチェックします。PyYAML が無ければ YAML の中身チェックはスキップされます（警告）。
- データベースパス:
  - DUCKDB_PATH / SQLITE_PATH の親ディレクトリが無ければ警告が出ます。起動時に自動作成される場合がありますが、事前にディレクトリを準備しておくことを推奨します。

ディレクトリ構成（抜粋）
-----------------------
以下はソースルート（src/kabusys）内の主要ファイル／モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み・Settings 定義（.env 自動ロード含む）
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — 監視ループ起動スクリプト
  - execution/
    - broker_api.py               — BrokerAPI Protocol / データモデル / ファクトリ
    - broker_factory.py           — Settings に応じたブローカークライアント生成
    - kabu_client.py              — kabu station REST API 実装
    - mock_client.py              — MockBrokerClient（テスト用）
    - execution_engine.py         — ExecutionEngine 本体
    - order_record.py             — OrderRecord データモデルと状態遷移
    - order_repository.py         — SQLite 永続化層
    - order_manager.py            — OrderManager（外向き API）
    - reconciler.py               — 起動時リコンシリエーション
    - risk_manager.py             — RiskManager（Gate1/2/3）
  - data/
    - calendar_management.py      — マーケットカレンダー管理（DuckDB）
    - news_collector.py           — RSS ベースのニュース収集
  - monitoring/
    - monitoring_db.py            — 監視用 DB 初期化／ログ機能（参照）
  - utils/
    - logging_setup.py            — ロギング設定ユーティリティ（参照）
    - process_priority.py         — プロセス優先度設定ユーティリティ（参照）
  - config/                       — YAML 設定ファイル（system_config.yaml 等、プロジェクトルートの config/）
  - data/                         — デフォルトで DB ファイル等を置くディレクトリ（data/kabusys.duckdb, data/monitoring.db など）

補足・トラブルシューティング
-----------------------------
- PyYAML が無い場合:
  - validate_config は YAML のパース検証をスキップし、警告を出します。YAML 構文チェックを行いたい場合は PyYAML をインストールしてください。
- データベースの親ディレクトリが無い:
  - validate_config や起動時に親ディレクトリが無ければ警告になります。必要に応じて手動で作成してください（例: mkdir -p data）。
- KABUSYS_ENV の値:
  - 有効値は development, paper_trading, live。live は本番扱いとなり追加の注意喚起（LINE 通知設定など）があります。
- 本番（live）接続:
  - 現状、一部で Live broker の完全実装が未実装または要注意の箇所があります。まずは paper_trading/development で動作確認することを推奨します。

開発・拡張
-----------
- BrokerAPI の実装を追加して live 環境を完全にサポートすることが可能です（broker_factory.create で切替）。
- ExecutionEngine / RiskManager / Reconciler のパラメータや Gate ロジックは要件に応じて調整可能です。
- DuckDB を使ったデータ処理（signals / portfolio_targets / calendar 等）は既存の SQL を拡張して活用できます。

最後に
------
この README は提供されたソースコードを基にした導入ガイド／運用メモです。実運用の前にローカルで十分なテスト（特に注文フローとリコンシリエーション）を行ってください。不明点があればソースの該当モジュール（execution/*.py、config.py 等）を参照してください。