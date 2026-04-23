KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株自動売買のためのシンプルなフレームワークです。  
設計上は以下を分離して実装しています。

- 環境設定読み書き (.env) と検証（対話式ウィザード / validate CLI）
- 発注エンジン（ExecutionEngine）と注文状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカークライアント層（MockBrokerClient / KabuStationClient）
- リスク管理（3段階ガード）
- 起動時リコンシリエーション（Reconciler）
- 監視（SystemMonitor 起動スクリプト）
- データ関連モジュール（マーケットカレンダー、ニュース収集など）

現状、実際の kabuステーション連携はクライアント実装（KabuStationClient）を用意していますが、Factory はテスト用途に MockBrokerClient を主に返す設計です（KABUSYS_ENV=live の Live クライアント利用は未実装箇所あり）。

主な機能
--------
- .env 対話式ウィザード（config_setup.py）で初期設定を容易に作成
- .env / config/*.yaml の事前検証 CLI（validate_config.py）で起動前チェック
- ExecutionEngine による「シグナル取得 → Gate1/2 リスクチェック → 発注 → Push ドレイン」フロー
- OrderRecord による状態遷移の厳密管理（不正遷移は例外）
- SQLite による注文永続化（OrderRepository）、DuckDB を分析/シグナル取得に利用
- 起動時のリコンシリエーション（OrderSent 状態の突合せ & ポジション差分検出）
- MockBrokerClient によるテスト可能な発注振る舞い（fill_mode: instant/partial/never/reject）
- 監視用ポーリングループ（run_monitoring.py）で CPU/MEM/DISK などの監視とログ記録

セットアップ手順
--------------
前提
- Python 3.10 以上を推奨（型注釈と一部構文に依存）
- SQLite（組み込み）、DuckDB（Python パッケージ）を利用

1. リポジトリをクローン/配置
   - プロジェクトルートに src/ 以下があることを想定しています。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

3. 必要パッケージをインストール
   - 代表的な依存（プロジェクトに requirements.txt がある場合はそちらを使用してください）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config の YAML 検証を有効にする場合）
   例:
     pip install duckdb httpx websocket-client defusedxml pyyaml

4. .env の初期作成
   - 対話式ウィザードを用意しています。
     python -m kabusys.config_setup
   - ウィザードは .env を生成／更新します（デフォルトはプロジェクトルートの .env）。

5. 設定検証
   - .env と config/*.yaml の整合性チェック:
     python -m kabusys.validate_config
   - 警告も FAIL として扱う（CI 等で有用）:
     python -m kabusys.validate_config --strict

主な環境変数（.env）
-------------------
ウィザードで扱う主要なキーと意味（代表的なもの）:

- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KILL_FLAG_CLEAR_ON_START: 起動時 kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject）

重要な挙動・注意点
-----------------
- .env の自動ロード:
  - プロジェクトルートの .env（および .env.local）を自動で読み込みます（既存の OS 環境変数を保護）。
  - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は PyYAML が無ければ YAML 内容の検証をスキップします（警告）。
- KABUSYS_ENV=live の場合、実行時に本番向けの注意（LINE 通知やキルフラグ等）を強調するチェックがあります。
- run_execution は paper_trading 環境では paper_trading 用の SQLite（data/paper_trading.db）を使用して本番 DB と分離します。
- Live ブローカー（実ブローカークライアント）については一部 NotImplemented の箇所があります。production 運用前にコードを確認してください。

基本的な使い方
--------------
- 設定ウィザード（.env 作成／更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor のポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。

- 発注エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV により mock (paper_trading / development) と live の挙動が変わります。
  - stop フラグ: プロジェクトルート/data/stop_requested.flag が作成されると安全に停止します。
  - PID ファイル: data/execution.pid などに PID を書きます。

- テスト・開発用モック
  - BrokerFactory を通じて MockBrokerClient が生成されます。PAPER_FILL_MODE により発注挙動を変更できます:
    - instant: 即時全量約定
    - partial: 一部約定
    - never: 注文は pending（OrderSentPendingError）になる
    - reject: 発注拒否（OrderRejectedError）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なファイルと説明（抜粋）:

- src/kabusys/__init__.py
  - パッケージ定義、バージョン

- src/kabusys/config.py
  - 環境変数/.env の読み込みロジックと Settings クラス（アプリ設定取得）

- src/kabusys/config_setup.py
  - .env 対話式ウィザード（run_wizard）

- src/kabusys/validate_config.py
  - .env および config/*.yaml の起動前検証 CLI

- src/kabusys/run_execution.py
  - ExecutionEngine 起動用スクリプト（セッション管理、PID、stop フラグ）

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - broker_api.py         — BrokerAPIProtocol, データモデル、例外、ファクトリ
  - broker_factory.py     — Settings に基づく broker クライアント生成
  - kabu_client.py        — kabuステーション実装（HTTP + WebSocket）
  - mock_client.py        — MockBrokerClient（テスト用）
  - order_record.py       — 注文状態遷移モデル（純粋ロジック）
  - order_repository.py   — SQLite 永続化層
  - order_manager.py      — OrderManager（外向き API、send/sync/cancel）
  - execution_engine.py   — ExecutionEngine（シグナル処理・push ドレイン等）
  - reconciler.py         — 再起動時のリコンシリエーション
  - risk_manager.py       — 3 段階のリスクガード（Gate1/2/3）

- src/kabusys/data/
  - calendar_management.py — マーケットカレンダー管理（next_trading_day 等）
  - news_collector.py      — RSS 収集・前処理ロジック
  - （jquants_client などデータ取得モジュール参照あり）

- src/kabusys/monitoring/
  - monitoring_db.py, system_monitor.py など（監視 DB 初期化・監視ロジック）

- src/kabusys/utils/
  - logging_setup.py, process_priority.py などユーティリティ

補足 / トラブルシューティング
-----------------------------
- PyYAML が無い場合、validate_config は YAML のパース検査をスキップします（警告表示）。CI などで厳密に検査したい場合は pyyaml をインストールしてください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。配布後やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- KABUSYS_ENV=live を使う場合は LINE 通知設定や kill flag の扱いなど安全性面を十分に確認してください（validate_config に警告が出ます）。
- 実ブローカー（kabu station）連携は実行環境で kabuステーションアプリが PC 上で起動していることが前提です。テストは MockBrokerClient で行ってください。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。
- バグ報告・機能提案・PR は歓迎します。変更を加える際はテストを追加してください。

以上が概要と基本的な使い方です。具体的な API（OrderManager / ExecutionEngine / BrokerAPIProtocol 等）の詳細はソース内ドキュメント（docstring）を参照してください。必要であれば README にサンプル .env や起動例、ユースケース別の注意点を追記します。