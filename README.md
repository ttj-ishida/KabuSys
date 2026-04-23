# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）です。  
このリポジトリには、環境設定管理、監視ループ、発注エンジン、ブローカー API 抽象化、リスクガード、データ処理ユーティリティなど、オートメーション取引に必要な主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を想定したモジュール設計を提供します。

- 環境変数 / .env の読み書き・検証（config_setup / validate_config）
- ExecutionEngine：シグナル駆動の発注エンジン（発注・リスクガード・WebSocket ドレイン）
- ブローカー抽象化（MockBrokerClient と kabuステーションクライアントのファクトリ）
- 注文状態管理（OrderRecord, OrderRepository, OrderManager）
- 起動時リコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor 起動スクリプト）
- データユーティリティ（マーケットカレンダー管理、ニュース収集など）
- テスト／開発向けに MockBroker を利用可能（paper_trading / development）

設計思想として、ビジネスロジック（OrderRecord 等）と永続化層（OrderRepository）を分離し、クラッシュ耐性・リコンシリエーションを考慮した2相永続化やサーキットブレーカー等の安全機構を組み込んでいます。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式に `.env` を作成／更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env および config/*.yaml の基本チェック（--strict で警告も FAIL）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - ExecutionEngine の起動（paper_trading / development では MockBroker を使用）
  - PID ファイル、kill.flag の扱い
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor の定期ポーリング（MONITOR_POLL_INTERVAL で間隔変更可）
- ブローカー API 層
  - create_broker_api() により MockBroker / KabuStation クライアントを生成
  - OrderRequest / OrderResponse / OrderStatus / Position 等のデータモデル
- 注文管理・状態遷移
  - OrderRecord（状態遷移検証）、OrderManager（発注フロー）、OrderRepository（SQLite 永続化）
- リスク管理
  - 3段階ガード（Gate1: シグナル / Gate2: レート制限 & サーキットブレーカー / Gate3: ドローダウン）
- データ処理ユーティリティ
  - マーケットカレンダー（DuckDB ベース）
  - ニュース収集（RSS 前処理、安全対策組込）

---

## セットアップ手順（ローカル開発向け）

1. Python 環境（3.9+ 推奨）を準備
   - 仮想環境を作成して有効化することを推奨します。

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate    # Linux / macOS
   .venv\Scripts\activate       # Windows
   ```

2. 依存パッケージをインストール  
   （requirements.txt がないため、主要依存を例示します）

   ```
   pip install duckdb httpx websocket-client defusedxml PyYAML
   ```

   注意:
   - sqlite3 は標準ライブラリに含まれます。
   - PyYAML がない場合、validate_config は YAML 内容チェックをスキップします（警告表示）。

3. プロジェクトルートに移動（.env の自動読み込みはプロジェクトルートを .git または pyproject.toml で検出します）

4. 初期設定（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   これにより `.env` を対話的に作成できます。作成後、`python -m kabusys.validate_config` で検証してください。

---

## 必要な環境変数（主要）

validate_config と Settings クラスで扱われる主要な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL（kabu station のベース URL）
- LINE_CHANNEL_ACCESS_TOKEN（本番でのアラート用、live 環境で設定推奨）
- LINE_USER_ID（アラート受取先）

kill / pid 関連:
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（0/1。1=起動時に kill.flag を自動クリア）

Paper Trading 関連:
- PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）

詳しい既定値・バリデーションは `src/kabusys/config.py` の Settings を参照してください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  - 通常モード（警告は OK）
    ```
    python -m kabusys.validate_config
    ```
  - 厳格モード（警告も FAIL）
    ```
    python -m kabusys.validate_config --strict
    ```

- 実行エンジン起動（本番相当のフロー。paper_trading / development では MockBroker を使います）
  ```
  python -m kabusys.run_execution
  ```
  動作概要:
  - PID ファイルを書き出す（config で指定）
  - DB（SQLite / DuckDB）に接続
  - BrokerClient を作成（paper_trading/development→Mock、live は未実装）
  - ExecutionEngine.run_session() をスレッドで開始

  停止:
  - プロジェクトルートの data/stop_requested.flag を作成すると優雅に停止します。
  - kill.flag（KILL_FLAG_PATH）を検出すると kill_switch（全 active 注文のキャンセル）を実行します。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト: 60）
  - 監視は常に production の sqlite_path を使用します（KABUSYS_ENV に依らず）

---

## .env の例（config_setup により生成されるフォーマットの例）
config_setup が生成する .env の一部（出力例）:

```
# --- J-Quants API ---
JQUANTS_REFRESH_TOKEN=...

# --- kabuステーション API ---
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# --- LINE Messaging API (アラート通知用) ---
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# --- データベース ---
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# --- システム設定 ---
KABUSYS_ENV=development
LOG_LEVEL=INFO

# --- Kill Switch ---
KILL_FLAG_CLEAR_ON_START=0
```

※ .env は決してバージョン管理（Git）にコミットしないでください（README へも注意喚起あり）。

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV=live を指定すると本番モード扱いになります。validate_config は live の場合に追加の警告（LINE 設定未設定など）を行います。live 運用時は十分に確認してください。
- ブローカーの本番クライアント（KabuStationClient）での live 対応は部分的に実装されていますが、リリース時には十分な検証が必要です。現状の BrokerClientFactory は development / paper_trading では Mock を返し、live は NotImplementedError を投げます（実装する場合は create_broker_api を実際のパラメータで呼び出します）。
- kill.flag（デフォルト data/kill.flag）は緊急停止用のフラグです。本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動でクリアします（開発用）。
- ExecutionEngine はクラッシュ耐性を高めるため、OrderSent 状態の注文や broker_order_id を DB に残す 2 相永続化を採用しています。リコンシリエーション（Reconciler）は起動時に未確定の注文をブローカー照合します。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトのトップに README.md / pyproject.toml 等がある想定。ここでは src/kabusys 配下を列挙）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（Settings）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py               — Broker API の Protocol / データモデル / factory
    - broker_factory.py           — Settings に応じたブローカークライアント生成
    - kabu_client.py              — kabuステーション REST クライアント（httpx）
    - mock_client.py              — テスト用 MockBrokerClient
    - order_record.py             — 注文状態モデル・遷移ロジック
    - order_repository.py         — SQLite 永続化レイヤ
    - order_manager.py            — 発注フロー（OrderState Machine 外向き API）
    - execution_engine.py         — 実行エンジン（シグナル処理 + push ドレイン）
    - reconciler.py               — 起動時のリコンシリエーション
    - risk_manager.py             — 3段階リスクガード
  - monitoring/
    - monitoring_db.py            — 監視 DB 初期化・ログ
    - system_monitor.py           — システム監視ロジック（別ファイルとして想定）
  - data/
    - calendar_management.py      — マーケットカレンダー管理（DuckDB ベース）
    - news_collector.py           — RSS ニュース収集
    - jquants_client.py           — J-Quants API クライアント（参照される想定）
  - utils/
    - logging_setup.py            — ロギング初期化ユーティリティ
    - process_priority.py         — プロセス優先度設定ユーティリティ

（実際のリポジトリでは上記以外の補助モジュールやスクリプトが存在する可能性があります）

---

## テスト / 開発時のポイント

- 多くのブローカー呼び出しは MockBrokerClient に対して検証できます（fill_mode による挙動切替あり）。
- validate_config で PyYAML が無ければ YAML パースチェックをスキップします。YAML 検証を行う場合は PyYAML をインストールしてください。
- DuckDB／SQLite を使うため、適切なファイルパス（DUCKDB_PATH / SQLITE_PATH）を .env で設定してから実行してください。
- 実行中の graceful stop は data/stop_requested.flag、緊急停止は kill.flag により行います。

---

もし README に追加したい「使い方の具体例（発注・リコンシリエーションのシーケンス）」や「運用チェックリスト（デプロイ時の確認項目）」などがあれば、目的に合わせて節を追加します。必要があればテンプレートの .env.example も作成します。