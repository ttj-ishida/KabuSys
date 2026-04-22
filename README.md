# KabuSys

日本株向けの自動売買システムのコアライブラリ（ミニマル実装）。
このリポジトリは発注エンジン、ブローカークライアントの抽象、監視・リコンシリエーション、
データ収集（カレンダー・ニュース）など、運用に必要な主要コンポーネントを含みます。

注意: 本 README はコードベースから抽出した情報を基にしています。実運用前に必ず設定検証とテストを行ってください。

## 概要
- 発注フローは Signal Queue を Pull して Order を生成 → broker API に送信 → 状態管理（SQLite）という設計。
- paper_trading（ペーパートレード）モードでは MockBrokerClient を使い、発注はローカル DB（data/paper_trading.db）に記録され本番 DB と分離されます。
- 起動時リコンシリエーション（Reconciler）で OrderSent 状態の注文をブローカーと照合し復旧します。
- RiskManager による 3 段階（Gate1/Gate2/Gate3）のリスクガードを搭載。
- 実行環境を .env で管理し、対話式ウィザードと検証ツールを提供します。

## 主な機能
- .env 対話式セットアップ（kabuys.config_setup）
- .env / config/*.yaml の事前検証（kabusys.validate_config）
- ExecutionEngine（シグナル処理 + WebSocket push ドレイン）
- Broker クライアント抽象（Mock / KabuStation 実装）
- 注文永続化（SQLite）
- 起動時リコンシリエーション（OrderSent の照合、ポジション差分検出）
- 監視用ポーリングループ（SystemMonitor 起動）
- データモジュール：マーケットカレンダー管理、RSS ニュース収集（前処理・SSRF 対策等）

## 必要条件
- Python 3.10 以上（`X | Y` の型表記を使用）
- 以下の主要パッケージ（用途に応じて追加してください）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml の中身を検証する場合に必要）
- 標準ライブラリ: sqlite3, logging, threading, etc.

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```
（実際の requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

オプション（代表例）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABU_API_BASE_URL — kabuステーション API ベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

自動ロード挙動:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## セットアップ手順（最小）
1. リポジトリをクローンして Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. 対話式で .env を生成:
   ```
   python -m kabusys.config_setup
   ```
   ウィザード終了後、`.env` に保存されます。
4. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする:
   python -m kabusys.validate_config --strict
   ```
   このコマンドは `.env` と `config/*.yaml` の存在・一部内容（PyYAML インストール時）を検証します。
5. data ディレクトリ等を作る（必要に応じて）:
   ```
   mkdir -p data
   ```

## 起動 / 使い方
- 設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告を FAIL 扱い（exit code 1）
  ```

- Execution（発注エンジン）を起動
  - 通常（development / paper_trading）:
    ```
    python -m kabusys.run_execution
    ```
  - 実行時の挙動:
    - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
    - PID ファイル: data/execution.pid（設定 PID_FILE_PATH を変更可能）
    - 停止は `data/stop_requested.flag` の作成で検知します。kill.flag（data/kill.flag）は kill スイッチ関連です。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- 注意点:
  - KABUSYS_ENV=live の設定は本番動作です。validate_config が警告を出します（LINE 通知設定など）。
  - 実際に kabuステーション API を使う場合は `KabuStationClient` の設定（KABU_API_PASSWORD, KABU_API_BASE_URL 等）を正しく行ってください。現在 live ブローカクライアントについては実装上の制約がある箇所があります（BrokerClientFactory のコメント参照）。

## 重要なファイル / フラグ
- data/stop_requested.flag — 外部からの停止要求（存在を監視）
- data/kill.flag — kill switch（発見時に致命的停止挙動）
- data/execution.pid — Execution の PID ファイル
- data/monitoring.db, data/paper_trading.db — SQLite DB（監視 / ペーパートレード用）
- data/kabusys.duckdb — DuckDB（分析 / シグナル等）

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の代表モジュール）

- kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数の読み込み・Settings クラス（自動 .env ロードを含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（発注エンジン）
  - run_monitoring.py — SystemMonitor 起動スクリプト（監視）
  - execution/
    - broker_api.py — BrokerAPI の Protocol / データモデル / ファクトリ
    - broker_factory.py — Settings に基づくブローカー生成
    - kabu_client.py — KabuStation REST API 実装（httpx）
    - mock_client.py — MockBrokerClient（テスト / ペーパートレード用）
    - order_record.py — Order の状態遷移モデル（純粋ロジック）
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — OrderManager（OrderRecord + OrderRepository + Broker API 結合）
    - execution_engine.py — ExecutionEngine（セッション管理、シグナル処理、push drain）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — 3 段階リスクガード
  - monitoring/
    - monitoring_db.py — 監視用 DB 関連（初期化等）  (参照)
    - system_monitor.py — システム監視ロジック（参照）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB / J-Quants 統合）
    - news_collector.py — RSS ニュース収集（正規化・SSRF 対策・前処理）
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ（参照）
    - process_priority.py — プロセス優先度設定ユーティリティ（参照）

（上記は主要ファイルの抜粋です。実際のディレクトリは src/kabusys 以下の完全なツリーを参照してください。）

## 開発・運用上の注意
- .env は絶対に Git にコミットしないでください（README と config.example を別途用意すること）。
- validate_config を CI やデプロイ前に実行して設定不備を検出することを推奨します。--strict モードで警告も FAIL にできます。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch の取り扱いを慎重に確認してください。
- DB スキーマ初期化関数（例: init_orders_db, init_monitoring_db）を使って初期テーブル作成を行ってください。
- WebSocket を使う際はネットワーク・認証（トークン）周りのリトライや例外処理の挙動に注意してください。

---

この README はコードからの抜粋説明です。詳細は各モジュールの docstring（関数・クラスの説明）も参照してください。問題・改善点があればリポジトリ内で issue を作成してください。