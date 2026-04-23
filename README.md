# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買システムのコアライブラリです。シグナルに基づく発注エンジン、ブローカークライアント、リスクガード、監視コンポーネント、データ収集ユーティリティなどを含みます。本リポジトリには実行用スクリプト（監視ループ・エンジン起動）や環境設定ウィザード、起動前チェックツールも含まれます。

## 概要

- 発注フローは Signal Queue Pull 型（ExecutionEngine）を採用。シグナル処理→WebSocket ドレインで注文ライフサイクルを管理します。
- ブローカー実装は抽象化されており、テスト用の MockBrokerClient（ペーパートレード / 開発向け）と将来的な実ブローカークライアント（kabuステーション）を切替可能。
- リスク管理は 3 段階（Gate1: シグナル、Gate2: 実行/レート制限とCB、Gate3: ドローダウン監視）を提供。
- 起動前設定検証ツール、対話式 .env 作成ウィザード、監視ループ・実行ループ用スクリプトを同梱。

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（OS 環境変数を上書きしない既定の挙動）
  - Settings クラスを通した型付きアクセス
- 環境設定ウィザード（config_setup）
  - 対話式で .env を作成 / 更新
- 設定検証 CLI（validate_config）
  - 必須環境変数の確認、YAML 設定ファイル（config/*.yaml）の存在・パース確認、ライブ環境向けガード等
  - --strict オプションで警告も失敗扱い
- 実行エンジン（ExecutionEngine）
  - シグナル処理（発注）と WebSocket push ドレイン
  - OrderManager / OrderRepository による堅牢な注文永続化と状態遷移
  - Reconciler による再起動時の自動同期（OrderSent の復旧など）
- ブローカークライアント層
  - BrokerAPIProtocol（Protocol）で抽象化
  - MockBrokerClient（fill_mode で instant/partial/never/reject を指定可能）
  - KabuStationClient（kabuステーション REST API 実装）
- リスク管理（RiskManager）
  - 余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視
- 監視（monitoring）
  - SystemMonitor を使ったポーリング監視ループ（run_monitoring）
- データユーティリティ
  - DuckDB を用いたマーケットカレンダー管理、RSS ニュース収集（news_collector）等

## セットアップ手順

1. リポジトリをクローンして Python 環境を用意します（推奨: venv）。
   - Python 3.10+ を想定（typing, match等は不要だが型ヒントに Path|None などを使用）

2. 必要なパッケージをインストールします（プロジェクトに requirements.txt がある想定）。
   例:
   ```
   pip install duckdb httpx websocket-client pyyaml defusedxml
   ```
   - PyYAML が無い場合、validate_config の YAML 検証がスキップされます。
   - 実ブローカークライアント（KabuStationClient）を使う場合は httpx と websocket-client が必要です。
   - DuckDB はデータ処理に使用します。

3. データディレクトリを作成します（デフォルトの DB パスが存在しないと警告になりますが、起動時に作成されることもあります）。
   ```
   mkdir -p data
   ```

4. .env の作成
   - 対話式ウィザードを使用するのが簡単です:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザード終了後、.env が作成されます（.env は Git にコミットしないでください）。

5. 設定を検証
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにする:
   python -m kabusys.validate_config --strict
   ```

6. 実際に実行する
   - 実行エンジン（発注）
     ```
     python -m kabusys.run_execution
     ```
     - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient が使用され、パスや DB は paper_trading 用に分離されます。
   - 監視ループ
     ```
     python -m kabusys.run_monitoring
     ```

## 必須 / 任意の環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - live 設定は本番扱いのため注意
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（本番では未設定だと警告）

ペーパートレード / モック関連:
- PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite パス（デフォルト: data/paper_trading.db）

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化（テスト向け）

その他:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

簡易 .env 例（実際のトークン/パスワードは安全に保管してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant
```

## 使い方（主要コマンド）

- .env を作る（対話式ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 起動前に設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジンを起動（発注ループ）
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレード（.env で KABUSYS_ENV=paper_trading）では MockBrokerClient を使用します。
  - 起動時に data/execution.pid（デフォルト）へ PID を書き、停止は data/stop_requested.flag を作成してもらう設計です。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。

- 開発用に MockBrokerClient を直接使う（ライブラリ経由）
  ```py
  from kabusys.execution import create_broker_api
  broker = create_broker_api(mock=True, fill_mode="instant")
  ```

## ディレクトリ構成（主要ファイル）

（プロジェクトルート /src/kabusys 配下の主要モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — J-Quants API ラッパ（参照）
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPIProtocol・データモデル・ファクトリ
    - broker_factory.py      — Settings を使うクライアントファクトリ
    - kabu_client.py         — kabuステーション REST クライアント
    - mock_client.py         — MockBrokerClient（テスト用）
    - execution_engine.py    — ExecutionEngine（シグナル処理 / push drain）
    - order_record.py        — 注文状態モデル・遷移ロジック
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — 外向き注文 API（create/send/sync/cancel）
    - reconciler.py          — リコンシリエーション・再起動復旧
    - risk_manager.py        — 3 段階のリスクガード
  - monitoring/
    - monitoring_db.py      — 監視 DB 初期化 / ログ機能
    - system_monitor.py     — システム監視ロジック（参照）
  - utils/
    - logging_setup.py      — ロギング設定
    - process_priority.py   — プロセス優先度調整ユーティリティ

その他:
- config/*.yaml — 各種設定ファイル（system_config.yaml / data_config.yaml / strategy_config.yaml / risk_config.yaml / execution_config.yaml / monitoring_config.yaml）  
  - validate_config.py はこれらの存在と YAML パースをチェックします（PyYAML が必要）。

## データベース初期化

- OrderRepository のスキーマ作成:
  - run_execution や手動初期化で init_orders_db(sqlite_conn) を呼ぶことで orders テーブルとインデックスが作成されます。
- 監視 DB:
  - run_monitoring / run_execution の起動の中で init_monitoring_db(sqlite_conn) が呼ばれ、必要テーブルが作成されます。

（これらの初期化はスクリプト起動時に自動で行われることを想定していますが、独自スクリプトで明示的に呼び出しても構いません。）

## 運用上の注意

- .env を絶対にリポジトリにコミットしないでください（README のウィザードも注意喚起あり）。
- 本番環境（KABUSYS_ENV=live）は慎重に扱ってください。validate_config は live 設定時に追加の警告を出します。
- kill.flag / stop_requested.flag / PID ファイルによる外部制御が設計に含まれています。運用手順に合わせてファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）を調整してください。
- Reconciler により OrderSent の不確定注文を復旧できますが、ブローカーや DB の状態が不整合な場合は手動確認が必要になります。

---

必要があれば README に以下を追加します:
- 開発向けのローカルテスト例（MockBroker を使ったユニット/統合テストのサンプル）
- 依存パッケージの正確なバージョン
- config/*.yaml の雛形や generate_config.py の使い方（リポジトリにある場合）
- SystemMonitor / monitoring_db の詳細仕様

追加で欲しい情報があれば教えてください。