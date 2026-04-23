KabuSys
======

日本株自動売買システム（ミニマル実装）  
この README はリポジトリ内の主要なスクリプト / 設定方法 / ディレクトリ構成をまとめたものです。

概要
----
KabuSys はローカル環境での戦略実行・発注・監視を想定した自動売買フレームワークの骨組みです。  
主な特徴は以下の通りです。

- 環境設定ウィザード（.env の作成/更新）と設定検証ツールを備える
- 発注エンジン（ExecutionEngine）と監視ループ（SystemMonitor）を独立して起動可能
- 本番 / ペーパートレード / 開発モードを切替え可能（KABUSYS_ENV）
- Mock ブローカークライアントを用意し、kabuステーションなしでテスト可能
- 注文の状態管理（State Machine）、永続化（SQLite）、起動時のリコンシリエーション機能
- DuckDB を用いたデータ分析（シグナル、ポートフォリオ等）

主な機能一覧
-------------
- .env ウィザード（config_setup.py）
  - 対話式に .env を生成 / 更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の存在・基本整合性を起動前にチェック
- 実行エンジン（run_execution.py）
  - ExecutionEngine を起動してシグナルに基づく発注を実行
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し paper_trading 用 SQLite を利用
- 監視ループ（run_monitoring.py）
  - SystemMonitor のポーリングループを実行（監視用 SQLite を利用）
- ブローカークライアント群（execution/*.py）
  - KabuStationClient（kabuステーション用）
  - MockBrokerClient（テスト用）
  - BrokerAPIProtocol / ファクトリ create_broker_api()
- 注文管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（外向き API: create/send/sync/cancel）
  - Reconciler（OrderSent 状態の自動照合・ポジション差分検出）
- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: 実行レベル（レート制限・サーキットブレーカー）
  - Gate3: 約定後メトリクス（ドローダウン監視）
- データ関連
  - DuckDB ベースのカレンダー管理（market_calendar）
  - ニュース収集（RSS → raw_news）、URL 正規化・SSRF 対策など

セットアップ手順
----------------
1. Python 環境を用意する（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールする
   - このリポジトリに requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な依存例（機能を使うために必要）:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   ※ 実際の requirements はプロジェクト内のファイルに従ってください。

3. プロジェクトルートで .env を作成する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を直接作成（例は下記「環境変数」を参照）

4. 設定検証を行う
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリを作成（必要に応じて）
   - デフォルトで data/ 以下に DB や pid/flag ファイルが置かれます。
   - 例: mkdir -p data

主要な環境変数（.env）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

任意・上書き可能（デフォルト値は括弧内）:
- KABUSYS_ENV (development | paper_trading | live) （default: development）
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db) — 監視 DB（monitoring は常に本番 sqlite を使用）
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — paper_trading 用 SQLite
- LOG_LEVEL (INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL (http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — alert 通知（任意）
- KILL_FLAG_CLEAR_ON_START (0 or 1) — 起動時の kill.flag 自動クリア（開発用）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）

自動ロード:
- プロジェクトルートに .env および .env.local がある場合、起動時に自動で読み込まれます（OS 環境変数が優先されます）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要コマンド（使い方）
--------------------
- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - strict モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading または development のときは MockBrokerClient を使用
    - paper_trading では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整（秒、default: 60）

停止フラグ / PID ファイル
- stop_requested.flag（data/stop_requested.flag）:
  - run_monitoring / run_execution の外部停止トリガとして使用
  - 存在を検知するとループを終了します
- kill.flag（デフォルト: data/kill.flag）:
  - 実行中に致命的な条件で kill_switch() を発動し全 active 注文をキャンセル
  - 起動時にファイルが存在する場合、KILL_FLAG_CLEAR_ON_START によって挙動が変わります
- PID ファイル:
  - ExecutionEngine は data/execution.pid（デフォルト）に PID を書き込みます

ペーパートレード設定（テスト用）
- KABUSYS_ENV=paper_trading に設定すると MockBrokerClient が使用されます。
- PAPER_FILL_MODE により挙動を切替可能:
  - instant: 即時全量約定（デフォルト）
  - partial: 部分約定（テストで fill_order を呼んで全量化可能）
  - never: pending（OrderSentPendingError を発生）
  - reject: 発注拒否を常に返す

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割の抜粋です。

- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - Settings クラス: 環境変数・.env の読み込みと設定値取得ロジック
  - 自動 .env ロード（.env / .env.local）

- config_setup.py
  - .env を対話式に作成/更新するウィザード

- validate_config.py
  - 起動前の環境変数・config/*.yaml の基本チェック CLI

- run_execution.py
  - ExecutionEngine を組み立てて起動するスクリプト

- run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト

- execution/
  - broker_api.py — BrokerAPIProtocol, データモデル, 例外, create_broker_api
  - kabu_client.py — kabuステーション REST クライアント (httpx + websocket)
  - mock_client.py — MockBrokerClient（テスト用）
  - broker_factory.py — Settings に基づくブローカーファクトリ
  - order_record.py — OrderRecord（状態遷移の純粋モデル）
  - order_repository.py — SQLite 永続化レイヤ
  - order_manager.py — Order の外向き API（create/send/sync/cancel）
  - reconciler.py — 起動時のリコンシリエーション（OrderSent 照合 / ポジション差分）
  - execution_engine.py — ExecutionEngine（シグナル処理 + WebSocket ドレイン）

- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB を利用）
  - news_collector.py — RSS ニュース収集（SSRF 対策・前処理・冪等保存）

- monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル初期化 / ログ

- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度設定

設計上の注意点 / 運用上の留意点
--------------------------------
- 本番（live）モードは特に注意が必要です。validate_config は live では警告を出します（LINE 通知設定等）。
- データベースファイル（DuckDB, SQLite）はデフォルトで data/ 配下に置かれます。バックアップや権限管理を行ってください。
- kill.flag / stop_requested.flag の運用ルールを明確化しておくと安全です。
- KabuStationClient を直接使うにはローカルに kabuステーションアプリが起動していることが前提です（API パスワード等の設定が必要）。

開発・拡張のヒント
------------------
- create_broker_api(mock=True) で MockBrokerClient を簡単に差し替え可能。単体テストで便利です。
- ExecutionEngine はテスト用に _process_signals() / _drain_push_queue() を直接呼べるように設計されています。
- Reconciler はクラッシュ復旧とポジション差分検出を行うため、運用前に十分なテストを推奨します。

ライセンス / 貢献
-----------------
（このリポジトリのライセンス・貢献ルールがあればここに記載してください）

--------

問題や補足したい点があれば教えてください。README の内容を用途（運用向け、開発者向け、簡易チュートリアル付き など）に合わせて調整します。