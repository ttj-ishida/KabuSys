KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買を想定した小規模な取引プラットフォームの骨組みです。  
主に以下を提供します：

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカークライアントの抽象化（実運用では kabuステーション、開発/テストではモック）
- 注文状態管理・永続化（SQLite）
- 起動時リコンシリエーション（Reconciler）
- 監視用ループ（SystemMonitor 用スクリプト）
- 環境設定ウィザードと設定検証 CLI
- データ処理ユーティリティ（マーケットカレンダー、ニュース収集など）

特徴（主要機能）
----------------
- 設定ウィザード（.env の対話式生成 / 更新）
- 設定検証 CLI（必須環境変数 / YAML ファイル等のチェック、--strict モードあり）
- 発注のクラッシュ耐性を考慮した2相的永続化フロー（OrderCreated → OrderSent → broker_order_id 保存 → OrderAccepted 等）
- 発注時の 3 段階リスクガード（Gate1: シグナル/余力/重複/ポジション上限、Gate2: レート制限・サーキットブレーカー、Gate3: ドローダウン監視）
- 起動時のリコンシリエーション（OrderSent の突合、ポジション差分検出）
- 開発向け MockBrokerClient（fill_mode の切替で instant/partial/never/reject をシミュレート）
- DuckDB を用いたデータ分析向けテーブルアクセス、SQLite を監視/注文永続化に使用

セットアップ手順
----------------
1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   リポジトリに requirements ファイルがない場合、主な依存は以下です（インストール推奨）:
   - duckdb
   - httpx
   - websocket-client
   - PyYAML (YAML 検証を行う場合)
   - defusedxml (ニュース収集で使用)
   例:
   - pip install duckdb httpx websocket-client pyyaml defusedxml

   そのほか標準ライブラリ（sqlite3 等）を使用します。

3. プロジェクトルートに .env を作成
   - 対話式ウィザードで生成するのが簡単です（下記を参照）。

使い方
-------

環境設定ウィザード（.env を作成 / 更新）
- コマンド:
  - python -m kabusys.config_setup
- 説明:
  - 対話式に環境変数を入力し .env を生成します。既存 .env があれば読み込み、Enter で既存値を再利用できます。
  - ウィザード後に .env を保存するか確認します。
  - 生成された .env ファイルは絶対に Git にコミットしないでください（README 内ヘッダにも注意書きが書き込まれます）。

設定検証 CLI
- コマンド:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告も FAIL 扱い）
- 説明:
  - .env / 環境変数、config/*.yaml の存在やパース（PyYAML があれば）をチェックします。
  - 主要なチェック内容:
    - 必須環境変数の未設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
    - KABUSYS_ENV の妥当性（development, paper_trading, live）
    - LOG_LEVEL の妥当性
    - DB パスの親ディレクトリ存在有無
    - config/*.yaml （存在・YAML パース）: system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
    - KABUSYS_ENV=live のときの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）
  - exit code:
    - エラーあり → 1
    - 警告ありかつ --strict → 1
    - それ以外 → 0

実行エンジン（発注）
- コマンド:
  - python -m kabusys.run_execution
- 説明:
  - ExecutionEngine を起動してセッション（シグナル読み取り → 発注 → push ドレイン）を行います。
  - 設定により paper_trading（モックブローカー）を使うと local/paper DB（data/paper_trading.db）へ記録します。live 環境の本番ブローカーは未実装でエラーとなります。
  - 起動時に PID ファイルを書き、停止フラグ（data/stop_requested.flag）を検知すると安全終了します。
  - kill.flag（設定でパス変更可）が存在する場合、KILL_FLAG_CLEAR_ON_START によって起動可否が決まります。

監視ループ（SystemMonitor）
- コマンド:
  - python -m kabusys.run_monitoring
- 説明:
  - SystemMonitor のポーリングループを開始します。デフォルトポーリング間隔は 60 秒で、環境変数 MONITOR_POLL_INTERVAL で上書き可能（1 以上の整数）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データは常に本番 DB に保存する設計）。
  - 停止フラグ file により終了します。

主要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。省略時は development。
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL — kabu station API の base URL（default: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（本番でのアラート用）
- LINE_USER_ID — LINE 通知先ユーザー ID
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、default 0）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE — paper_trading 向けモックの fill 動作（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite パス（default: data/paper_trading.db）

.env 自動読み込みの挙動
- 起動時、Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）を検出できると:
  - .env を読み込み（既存 OS 環境変数を上書きしない）
  - .env.local を後から上書き読み込み（同じく OS 環境変数は保護）
- 自動ロードを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env（最低限）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO

動作メモ / 運用ポイント
-----------------------
- ExecutionEngine はシグナル処理（通常 8:50〜9:10）と WebSocket push のドレイン（9:10〜15:30）を行う設計になっています（実時間ベースのループ）。
- 発注フローはクラッシュ耐性を考慮した段階的永続化を採用しています（OrderSent を DB に残すケースを想定）。
- Reconciler は起動時に OrderSent レコードを broker と突合し、状態を回復します。
- paper_trading / development 環境では MockBrokerClient を使うため、kabuステーションをローカルで用意する必要はありません。
- 本番（live）環境ではさらに慎重な設定確認が必要です（LINE 通知や kill フラグの扱い等）。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py — パッケージ情報（バージョン等）
- config.py — 環境変数読み込み / Settings（.env 自動読み込みロジック、プロパティアクセス）
- config_setup.py — 対話式 .env ウィザード CLI
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ / モジュール（概要）
- kabusys/execution/
  - broker_api.py — ブローカー API の Protocol、データモデル、ファクトリ
  - kabu_client.py — kabuステーション REST API 実装（httpx）
  - mock_client.py — テスト用 MockBrokerClient
  - broker_factory.py — Settings に応じてブローカークライアントを生成
  - order_record.py — 注文状態モデルと遷移ロジック（純粋ビジネスロジック）
  - order_repository.py — SQLite を用いた永続化層
  - order_manager.py — ビジネス向け注文操作 API（create/send/sync/cancel）
  - reconciler.py — 起動時のリコンシリエーション
  - execution_engine.py — Signal Queue Pull 型発注エンジン
  - risk_manager.py — 3 段階リスクガード
- kabusys/data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB + J-Quants 連携）
  - news_collector.py — RSS 取得・前処理・raw_news 保存ロジック（defusedxml 等を使用）
  - jquants_client (参照実装想定) — J-Quants API 連携（カレンダー等用）
- kabusys/monitoring/
  - monitoring_db.py — 監視用 DB 初期化 / ログ保存など
  - system_monitor.py — システムリソース監視（CPU/MEM/DISK 閾値等）
- kabusys/utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ

テスト / 開発
-------------
- 開発環境では KABUSYS_ENV=development / paper_trading を使用してください（MockBrokerClient が利用されます）。
- 単体テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動 .env 読み込みを無効化すると実行環境を固定できます。
- MockBrokerClient の fill_mode を変更して、即時約定 / 部分約定 / 約定なし / 拒否 の挙動をシミュレーションできます。

ライセンス / 注意
-----------------
- .env 等秘密情報は決して Git リポジトリにコミットしないでください。
- live 環境では実際に資金が動きます。KILL_FLAG_CLEAR_ON_START 等の設定は慎重に扱ってください。

追加情報 / 依存関係の補足
-------------------------
- YAML の検証は PyYAML がインストールされている場合にのみ実行されます（未インストール時は警告を出してスキップ）。
- news_collector では defusedxml を使って XML の安全なパースを行っています。
- WebSocket 接続は websocket-client ライブラリを使用しています。
- DuckDB は解析系のデータ格納に用いられます（signals, portfolio_targets, market_calendar 等）。

問題が発生したり、詳細な設計意図や実装を知りたい場合は該当モジュール（例: execution_engine.py, order_manager.py, risk_manager.py 等）を参照してください。README に記載されていない実行オプションや細かな仕様は各モジュールの docstring を優先してください。