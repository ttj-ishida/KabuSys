# KabuSys

日本株自動売買システムのコアライブラリ（プロトタイプ）。  
このリポジトリは発注エンジン、リスクガード、監視・リコンシリエーション機能、データ収集ユーティリティなどの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした自動売買基盤の骨組みです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象化（kabu station 実装 & Mock 実装）
- 注文状態遷移（OrderRecord）と永続化（SQLite）
- 起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（Gate1/2/3）
- 監視ループ（SystemMonitor 起動スクリプト）
- J-Quants／カレンダーやニュース収集用のデータモジュール
- .env 対話式セットアップ & 設定検証ツール

設計方針として、DB 操作とビジネスロジックを分離し、クラッシュ後の整合性（2相永続化・リコンシリエーション）を考慮しています。

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env ファイルを対話式に作成・更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数・config/*.yaml の存在／パースチェックなど
- 発注エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV に応じて Mock / 実ブローカーを選択
  - PID / kill.flag 管理、リコンシリエーション、WebSocket push ドレイン
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - システムリソース監視や監視DBへのログ記録
- Execution 層
  - OrderRecord（状態遷移）、OrderManager（送信・同期・キャンセル）、OrderRepository（SQLite 永続化）
  - BrokerAPI の抽象化（Protocol）と factory
  - KabuStationClient（httpx ベース）・MockBrokerClient（テスト用）
  - RiskManager（Gate1/2/3）
  - Reconciler（起動時の注文同期とポジション差分検出）
- Data 層
  - カレンダー管理（DuckDB-based）
  - ニュース収集モジュール（RSS 取得・正規化・保存）

---

## 前提条件（主要依存）

- Python 3.8+
- 標準ライブラリ: sqlite3, threading, logging, pathlib, etc.
- 外部パッケージ（少なくとも以下が必要／推奨）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（設定検証で YAML 内容を検証したい場合）
- 注意: パッケージ名は pip でインストール可能です。

例:
pip install duckdb httpx websocket-client defusedxml pyyaml

（requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (または Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml pyyaml
4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは既存の .env を読み込み、入力を促します。保存すると .env に書き込みます。
   - .env は決して Git にコミットしないでください（README 内にも注意書きが書き込まれます）。
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit(1)）扱いになります。

---

## 必須環境変数（最低限）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主な任意/推奨変数（ウィザードで設定可能）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR 等
- KABU_API_BASE_URL — kabu station base URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）

詳しい項目は python -m kabusys.config_setup で確認できます。

---

## 使い方

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告も FAIL 扱いで exit(1)）
- 発注エンジン起動（本番/ペーパー両対応）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/execution.pid に PID を書き込みます。停止は data/stop_requested.flag を作成する等で行います。
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず本番 DB を参照する設計）。
- ログのセットアップは内部で行われる（utils.logging_setup を使用）。LOG_LEVEL を環境変数で制御します。

注意点:
- KABUSYS_ENV=live を使用する場合は設定を慎重に確認してください（validate_config が警告を出します）。
- kabu station 実ブローカーを利用するにはローカルに kabuステーション® アプリが起動している必要があります（KabuStationClient を使用する場合）。
- PID / kill.flag / stop_requested.flag を使った外部制御が組み込まれています。

---

## ディレクトリ構成

以下は主要なファイルとディレクトリ（src/kabusys 以下）の概要です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — .env 自動ロード（.env / .env.local）、Settings クラス（環境変数のラッパ）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - execution/ (発注関連)
    - broker_api.py — BrokerAPIProtocol・データモデル・例外・ファクトリ
    - broker_factory.py — Settings からクライアントを生成するファクトリ
    - kabu_client.py — KabuStationClient（httpx 実装）
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite 永続化層（orders テーブル定義等）
    - order_manager.py — OrderStateMachine の外向き API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン・kill switch）
    - reconciler.py — 起動時リコンシリエーション（OrderSent sync、ポジション差分）
    - risk_manager.py — 3段階リスクガード（Gate1/2/3）

  - data/ (データ関連)
    - calendar_management.py — JPX カレンダー管理（DuckDB ベース）
    - news_collector.py — RSS ニュース取得・正規化・保存
    - jquants_client.py (参照あり) — J-Quants API クライアント（別ファイルとして存在する想定）

  - monitoring/ (監視関連)
    - monitoring_db.py — 監視用 DB 初期化・ログ関数（run_monitoring から利用）
    - system_monitor.py — システムリソース監視ロジック（run_monitoring で使用）

  - utils/
    - logging_setup.py — ログ初期化ヘルパ
    - process_priority.py — プロセス優先度設定ユーティリティ

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

  （上記 YAML はプロジェクトルートの config ディレクトリに配置。validate_config は存在とパースをチェックします。PyYAML がない場合は内容検証をスキップします。）

- data/
  - デフォルトの DB・フラグファイル格納先（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag など）

---

## 運用メモ / トラブルシュート

- 設定検証で YAML のパースエラーが出る場合:
  - PyYAML をインストールしていれば validate_config が内容を検査します。問題の YAML を確認してください。
- KabuStationClient を使うには kabuステーション® のローカル起動が前提です。API の base URL を KABU_API_BASE_URL で調整できます。
- paper_trading モード:
  - 実 DB と分離するため PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
  - MockBrokerClient の fill_mode は PAPER_FILL_MODE（instant/partial/never/reject）で制御します。
- Kill Switch:
  - 起動時に data/kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動可能）。
  - 実行中に kill_switch が発動すると全 active 注文をキャンセルします。
- リコンシリエーション:
  - クラッシュや不確定状態（OrderSent）の回復を意図しており、起動時に自動実行されます。

---

## 開発・拡張のヒント

- BrokerAPIProtocol を実装すれば別ブローカー（実装）にも容易に対応できます。
- ExecutionEngine はテスト用に _process_signals() / _drain_push_queue() を直接呼べる設計です。ユニットテストを作成しやすくなっています。
- カレンダーやニュース収集は DuckDB を利用する設計になっているため、分析処理と連携しやすいです。

---

必要であれば、README に具体的な .env のサンプルやサンプルコマンド（systemd / supervisor 用の起動例）、テスト例（MockBrokerClient を使ったユニットテストの簡単なテンプレ）も追記します。どの情報を追加したいか教えてください。