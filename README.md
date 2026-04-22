# KabuSys

日本株向け自動売買システムのプロトタイプ。  
このリポジトリは発注エンジン、モニタリング、カレンダー管理、ニュース収集などの主要コンポーネントを含み、ローカル開発・ペーパートレード環境での動作を想定しています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- Execution: シグナルに基づく注文発行（ExecutionEngine）、注文管理（OrderManager / OrderRepository）、ブローカークライアント（実ブローカ or Mock）
- Monitoring: システム稼働状況の定期記録・監視（run_monitoring）
- Data: 市場カレンダー管理、ニュース収集などのデータ取得・前処理
- Utilities: ロギング設定やプロセス優先度などの補助機能
- 開発用 CLI:
  - 環境設定ウィザード（.env 作成支援）: `kabusys.config_setup`
  - 設定検証ツール: `kabusys.validate_config`

設計上、DB（SQLite / DuckDB）や外部 API（kabuステーション / J-Quants）との連携を想定していますが、ペーパートレードや Mock Broker によるローカルテスト用の実装も用意されています。

---

## 主な機能一覧

- 環境設定ウィザード（対話形式で .env を生成/更新）
- 設定検証 CLI（必須環境変数・YAML ファイル・パス検査・本番ガード）
- ExecutionEngine: シグナル取り込み → Gate1/2（リスク検査） → 発注 → WebSocket push ドレイン
- Order 管理:
  - OrderRecord（状態遷移の純粋モデル）
  - OrderRepository（SQLite 永続化）
  - OrderManager（送信 / 同期 / 取消）
  - Reconciler（再起動時の OrderSent 照合・ポジション差分検出）
- RiskManager: Gate1 (資金/重複/ポジション上限)、Gate2 (レート制限/サーキットブレーカー)、Gate3 (ドローダウン監視)
- ブローカ API 層:
  - MockBrokerClient（テスト用、fill_mode 制御可能）
  - KabuStationClient（kabuステーション REST / WebSocket 実装）
- Data モジュール:
  - JPX カレンダー管理（DuckDB を前提）
  - ニュース収集（RSS、前処理、SSRF 対策等）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウトしてください。

2. Python 環境を用意（推奨: venv）

   Example:
   python -m venv .venv
   source .venv/bin/activate

3. 必要なパッケージをインストール（プロジェクト用の requirements は同梱されていない想定のため主要依存を例示します）:

   pip install httpx websocket-client duckdb pyyaml defusedxml

   （実際のプロジェクトでは requirements.txt / poetry の指定に従ってインストールしてください）

4. .env を作成する

   - 対話式ウィザードを使う（推奨）:

     python -m kabusys.config_setup

   - 手動で作る場合はリポジトリルートに `.env` を置く。最低限以下の必須環境変数を設定してください:

     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   .env の自動読み込みはデフォルトで有効です。OS 環境変数より .env は優先されません（読み込み順: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. （オプション）config/*.yaml ファイルを準備する  
   リポジトリに `config/` 以下を使う機能があります。サンプル生成スクリプトが存在する場合はそれを利用してください（README 内では `python scripts/generate_config.py` を参照する箇所があります）。

---

## 使い方

- 設定ウィザード（.env を対話作成）

  python -m kabusys.config_setup

- 設定検証

  - 通常モード（警告は OK として表示）:

    python -m kabusys.validate_config

  - `--strict` を付けると警告も FAIL 扱い（exit code 1）になります:

    python -m kabusys.validate_config --strict

  検証は必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在、config/*.yaml の存在と（PyYAML があれば）パースを確認します。KABUSYS_ENV=live の場合は追加の安全ガード（LINE 通知設定など）をチェックします。

- 実行エンジン起動（Execution）

  - 実行:

    python -m kabusys.run_execution

  - 概要:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用の SQLite（デフォルト `data/paper_trading.db`）に記録します。
    - デフォルトで PID ファイルや停止フラグ（data/kill.flag、data/stop_requested.flag）を利用します。起動時に kill.flag があり `KILL_FLAG_CLEAR_ON_START=0` の場合は起動を拒否します。
    - 実行中に停止させるには `data/stop_requested.flag` を作成するか、プロセスをシグナルで終了してください。

- 監視プロセス起動（Monitoring）

  python -m kabusys.run_monitoring

  - モニタは sqlite (settings.sqlite_path) と duckdb (settings.duckdb_path) に接続します。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書きできます（デフォルト 60 秒）。不正な値はデフォルトにフォールバックします。

- 環境変数の主な一覧（重要なもの）

  - 必須:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD

  - 任意 / 推奨:
    - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
    - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
    - KABU_API_BASE_URL: kabuステーションの API ベース URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用
    - KILL_FLAG_CLEAR_ON_START: 0 または 1（デフォルト 0、本番では 0 推奨）
    - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
    - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

---

## 開発・運用上の注意

- 環境モード:
  - development: 開発・テスト向け（デフォルト）
  - paper_trading: 発注ロジックは動作するが実発注は行わない（MockBroker を利用）
  - live: 本番（実ブローカーを想定） — 設定ミスによる致命的事故を避けるため本番向けチェックが多数存在します

- Kill / Stop フラグ:
  - 起動時および実行中の安全措置として `KILL_FLAG`（デフォルト `data/kill.flag`）を使用します。
  - `KILL_FLAG_CLEAR_ON_START=1` が設定されていると起動時に kill.flag を自動クリアします（本番では危険です）。
  - 停止要求は `data/stop_requested.flag` を作成することで実行ループが検知して終了します。

- DB:
  - orders は SQLite に永続化されます（init_orders_db が DB スキーマを作成します）。
  - DuckDB は分析・シグナル取得用の DB として機能します。デフォルトファイルは `data/kabusys.duckdb`。

- Reconciliation:
  - 起動時に OrderSent の状態が残っているケースに備えて Reconciler が存在し、ブローカーと再照合して状態を復旧します。

- テスト:
  - MockBrokerClient を使えば外部サービス無しで発注フローやリスク制御の単体テストが可能です。

---

## .env の例（最小）

以下は動作に最低限必要な項目の例です（実運用では秘密情報を Git 管理しないでください）:

KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル / モジュール構成は次のとおりです:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env ロードと Settings クラス
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py         — BrokerAPI のデータモデル・Protocol・ファクトリ
    - broker_factory.py     — Settings に応じた Broker クライアント生成
    - kabu_client.py        — kabuステーション REST/WebSocket クライアント
    - mock_client.py        — MockBrokerClient（テスト用）
    - order_record.py       — Order 状態遷移モデル
    - order_repository.py   — SQLite 永続化層
    - order_manager.py      — 発注 / 同期 / 取消 の高レベル API
    - execution_engine.py   — セッション制御・シグナル処理・push ドレイン
    - reconciler.py         — 起動時リコンシリエーション
    - risk_manager.py       — Gate1/2/3 リスク制御
    - ...（その他補助クラス）
  - data/
    - calendar_management.py — JPX カレンダー管理
    - news_collector.py      — RSS ニュース収集・前処理
    - ...（J-Quants クライアント等）
  - monitoring/
    - monitoring_db.py      — 監視DB 初期化・書き込み
    - system_monitor.py     — システムメトリクス収集
  - utils/
    - logging_setup.py      — ログ設定
    - process_priority.py   — プロセス優先度設定
  - config/                 — YAML 設定ファイル群（system_config.yaml 等）

---

## 付録 / よくある質問

- Q: 設定検証で PyYAML が無いと YAML の中身検証が飛ばされます。  
  A: その場合は `pip install pyyaml` をしてください。validate_config は PyYAML 未インストール時にパース検証をスキップしますが、存在チェックは行います。

- Q: 本番（live）で使えますか？  
  A: コードには本番想定のチェックやガードがありますが、KabuStationClient の実運用検証や安全周りの厳密な監査は必須です。現状は development / paper_trading を主に想定しています。BrokerClientFactory は live の場合 NotImplementedError を投げます（実ブローカ実装は未実装/未検証）。

- Q: テスト実行時に .env の自動ロードを抑止したい  
  A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動で .env を読み込まなくなります（テストで独自に環境を差し替える際に有用です）。

---

必要であれば README に含めるコマンド例や運用手順、CI 用のチェック手順（validate_config を CI に組み込む例）を追記します。どの情報をより詳しく載せたいか教えてください。