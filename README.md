# KabuSys

日本株自動売買システム (KabuSys) — 軽量な実行エンジン、モニタリング、設定ウィザードを含むリポジトリ。

---

## プロジェクト概要

KabuSys は日本株向けに設計された自動売買プラットフォームの一部です。本リポジトリには以下の主要要素が含まれます。

- 環境設定ウィザード（.env の生成/更新）
- 起動前の設定検証ツール（.env / config/*.yaml のチェック）
- 発注を行う ExecutionEngine（本番／ペーパートレード対応）
- 実行時の監視ループ（SystemMonitor）
- ブローカークライアント抽象（実運用の kabuステーション／モッククライアント）

設計方針として、ビジネスロジック（注文状態管理など）は DB や IO と分離され、テストしやすい構成になっています。

---

## 主な機能一覧

- .env 対話式ウィザード（config_setup）
  - .env/.env.local への入力補助、既存値の再利用、秘密値のマスク表示
- 起動前検証（validate_config）
  - 必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの存在チェック、config/*.yaml の存在・（PyYAML があれば）パース検証
  - `--strict` オプションで警告も失敗として扱う
- 実行エンジン（run_execution）
  - Signal Queue からシグナルを読み取り Gate1/2/3 によるリスク制御を行い発注
  - Paper Trading（モック）対応、実運用時は KabuStationClient（未実装の部分あり）
  - リコンシリエーション（再起動後の OrderSent 照合）
  - kill.flag / PID 管理・キャンセル処理
- 監視ループ（run_monitoring）
  - SystemMonitor をポーリングしてシステムリソースや監視情報を記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- ブローカー抽象（broker_api）
  - Protocol 定義・MockBrokerClient・KabuStationClient（REST/WebSocket 実装）
- データモジュール
  - カレンダー管理、ニュース収集等のユーティリティ（DuckDB 前提）

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローンしてパッケージをインストール
   - 例（venv 推奨）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     ```
   - 必要なパッケージ（例）:
     ```
     pip install duckdb httpx websocket-client defusedxml PyYAML
     ```
   - 実際のプロジェクトでは requirements.txt / Poetry がある想定です。上は主要依存の例です。

2. .env の作成
   - ウィザード実行:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成してください。
   - 自動ロード:
     - デフォルトで OS 環境変数 > .env.local > .env の順で読み込みます。
     - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

3. 必須環境変数（最低限セット）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - その他（任意／デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - KABU_API_BASE_URL
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
     - PAPER_FILL_MODE（paper_trading 用: instant|partial|never|reject）
     - KILL_FLAG_CLEAR_ON_START（0|1）

4. DB の初期化
   - Execution/Monitoring は内部で初期化処理（init_orders_db / init_monitoring_db 等）を呼び出します。特別な初期化スクリプトがある場合はそれを利用してください。

---

## 使い方

- 設定ウィザード（.env の作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も FAIL 扱い（exit code 1）
  ```
  - validate_config は .env と config/*.yaml（system_config.yaml 等）をチェックします。
  - PyYAML 未インストール時は YAML の内容検証をスキップして警告を出します。

- 実行エンジン起動（通常はサービスとして実行）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV:
    - development / paper_trading: MockBrokerClient を使用（デフォルト）
    - live: 実ブローカークライアントは未実装 → NotImplementedError（警告）
  - 停止フラグ: `<project_root>/data/stop_requested.flag` を作成すると安全に停止します。
  - PID ファイル: デフォルト `data/execution.pid`（Settings.pid_file_path）

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
  - 監視は常に本番の sqlite_path を使います（paper_trading でも本番 sqlite を参照します）。

---

## 重要な動作・振る舞いメモ

- .env 自動ロード
  - OS 環境変数（既存）を保護しつつ .env を読み込みます。
  - `.env.local` は `.env` の上書きに使われます。
  - テストなどで自動読み込みを防ぐには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- ペーパートレード
  - Settings.is_paper が True の場合、MockBrokerClient を使い paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / default data/paper_trading.db）に記録して本番 DB と分離します。

- kill flag / PID 管理
  - kill.flag のデフォルトパス: `data/kill.flag`
  - stop_requested.flag（起動ディレクトリの data/stop_requested.flag）を置くことでループ終了をトリガーできます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に既存の kill.flag を自動でクリアします（危険なので本番は 0 推奨）。

- Reconciliation（再起動後の復旧）
  - 起動時に OrderSent 状態の注文をブローカーと突合して同期を試みます（Reconciler）。
  - OrderSent → broker_order_id をもとに状態復旧が可能な設計（2相永続化戦略など）。

- validate_config の対象 config ファイル（config/*.yaml）
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  - 存在しない場合は警告を出します（生成スクリプトの案内メッセージあり）。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用
- PAPER_FILL_MODE — paper_trading の約定モード: instant / partial / never / reject
- KILL_FLAG_CLEAR_ON_START — 0/1
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings 定義（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPI の Protocol、データモデル、ファクトリ
    - broker_factory.py      — Settings に応じたクライアント生成
    - kabu_client.py         — kabuステーション REST/WebSocket 実装
    - mock_client.py         — MockBrokerClient（テスト・開発用）
    - order_record.py        — 注文状態モデルと遷移ロジック（純粋ロジック）
    - order_repository.py    — SQLite 永続化（orders テーブル定義）
    - order_manager.py       — 発注フローの高レベル API
    - execution_engine.py    — 発注セッションの主要ロジック
    - reconciler.py          — 再起動時のリコンシリエーション
    - risk_manager.py        — Gate1/2/3 リスク制御
    - ...（その他補助モジュール）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB を利用）
    - news_collector.py      — RSS ニュース収集・前処理
    - jquants_client.py      — （想定）J-Quants API クライアント
    - ...
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・書き込みユーティリティ
    - system_monitor.py      — システム監視ロジック
    - ...
  - utils/
    - logging_setup.py       — ロギング初期化ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ
    - ...

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (上記はプロジェクト固有の設定ファイル。存在しない場合は生成案内が出ます)

- data/
  - （デフォルト DB や PID / flag ファイルが置かれる場所）
  - monitoring.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - execution.pid, kill.flag, stop_requested.flag, ...

---

## 参考コマンドまとめ

- ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```

---

README はここまでです。追加で以下が必要であれば教えてください：
- 詳細な依存関係（requirements.txt / Poetry の例）
- config/*.yaml のサンプルテンプレート
- データベース初期化手順サンプル（SQL / DuckDB スキーマ）