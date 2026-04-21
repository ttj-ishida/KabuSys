# KabuSys

日本株自動売買システムの一部実装（ライブラリ + 起動スクリプト群）。

このリポジトリは、システム設定管理、監視ループ、発注エンジン、ブローカークライアント抽象化、リスクガード、リコンシリエーション、ニュース収集・マーケットカレンダー管理などの主要機能を含みます。実運用を想定した堅牢性（クラッシュ耐性・二相永続化・サーキットブレーカー等）を備えています。

---

## 主な特徴 (Features)
- 環境変数/.env 管理ウィザード（対話式）と自動読み込み
- 設定検証 CLI（.env と config/*.yaml のチェック、--strict オプション）
- ExecutionEngine：信号プル型の発注エンジン（シグナル処理・WebSocket ドレイン）
- Order 管理（OrderRecord, OrderRepository, OrderManager）と状態遷移の検証
- RiskManager：Gate1/2/3 の三段階リスクガード（余力・ポジション上限・レート制限・サーキットブレーカー・ドローダウン）
- Broker クライアント抽象（Protocol）と Mock 実装（ペーパートレード用）
- 起動時リコンシリエーション（Reconciler）で OrderSent な注文を突合
- 監視用プロセス（SystemMonitor のポーリングループ）
- データ系ユーティリティ：JPX カレンダー管理、RSS ニュース収集（前処理、SSRF 対策等）
- DuckDB / SQLite を使用したデータ永続化（デフォルトは data/ 配下）

---

## 必要条件（推奨）
- Python 3.10+
- パッケージ（用途に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml のパース検証に必要、任意）
  - defusedxml（ニュース収集で使用）
- SQLite は標準ライブラリで利用可能

（実際のプロジェクトでは requirements.txt を用意して `pip install -r requirements.txt` を推奨します）

---

## セットアップ手順

1. リポジトリをチェックアウトして依存パッケージをインストールします（例）:
   - python -m pip install duckdb httpx websocket-client PyYAML defusedxml

2. プロジェクトルートに `data/` ディレクトリを作成（既定の DB / PID / flag 用）:
   - mkdir -p data

3. .env を作成（対話式ウィザード推奨、下記参照）

環境変数読み込みルール:
- 自動読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## .env 作成（対話式ウィザード）
対話式で .env を作成・更新できます。

コマンド:
- python -m kabusys.config_setup

ウィザード内で入力し、最後に保存確認があります。保存後は:
- python -m kabusys.validate_config で検証してください。

主要な設定項目（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
- 任意 / 推奨:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
  - KILL_FLAG_CLEAR_ON_START（0|1、デフォルト: 0。本番では 0 推奨）
  - PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject）

---

## 設定検証
起動前に設定のチェックを行う CLI。

コマンド:
- python -m kabusys.validate_config
- python -m kabusys.validate_config --strict  # 警告もエラー扱い（exit 1）

主なチェック内容:
- 必須環境変数が設定されているか
- KABUSYS_ENV の値チェック（development/paper_trading/live）
- LOG_LEVEL の妥当性
- DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在チェック
- config/*.yaml の存在確認・（PyYAML がある場合）パース検証
- KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）

戻り値 / exit code:
- エラーがあれば exit(1)
- 警告のみで --strict を指定した場合も exit(1)
- 問題なければ exit(0)

---

## 実行（ランタイム） — 監視 / エンジン

- 監視プロセス（SystemMonitor のポーリングループ）
  - コマンド:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（ポーリング間隔秒、デフォルト 60）
  - 特記事項:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- 発注エンジン（ExecutionEngine）
  - コマンド:
    - python -m kabusys.run_execution
  - 動作概要:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用（本番 DB と分離して paper_trading 用 SQLite が使われる）
    - シグナル処理時間帯（既定: 8:50〜9:10）にシグナルを読み込み Gate1/2 を通して発注
    - WebSocket push のドレインループ（既定: 9:10〜15:30）
    - kill.flag を検知すると全 active 注文をキャンセルして安全停止
  - PID / stop flag:
    - PID ファイル: data/execution.pid（config で上書き可）
    - 停止フラグ: data/stop_requested.flag
    - kill.flag（起動時の起動拒否判定 / 自動クリアは KILL_FLAG_CLEAR_ON_START）

Mock ブローカ:
- 開発・テスト時は MockBrokerClient（fill_mode を指定可能）で実行可能
- KABUSYS_ENV=live は現時点で Live client の完全実装を必要とするためエラーまたは未実装通知が出ます

---

## 主要コンポーネントの役割（抜粋）
- kabusys.config
  - .env 自動読み込みロジック、Settings クラス（プロパティ経由で設定取得）
  - 読み込み順序や保護された OS 環境変数の取り扱いを実装
- kabusys.config_setup
  - .env 作成ウィザード（対話式）
- kabusys.validate_config
  - 起動前チェック CLI（エラー / 警告 / 情報を出力）
- kabusys.run_execution
  - ExecutionEngine を組み立てて起動するスクリプト
- kabusys.run_monitoring
  - SystemMonitor のポーリングループを起動するスクリプト
- kabusys.execution
  - broker_api: Broker API Protocol、データモデル、例外、ファクトリ
  - kabu_client: KabuStation REST API 実装（httpx, websocket）
  - mock_client: テスト用 MockBrokerClient
  - broker_factory: Settings に応じてクライアントを生成
  - order_record / order_repository / order_manager: 注文状態モデル・永続化・外向け API
  - execution_engine: セッション実行ロジック（シグナル処理・push drain）
  - reconciler: 起動時の自動復旧・同期処理
  - risk_manager: Gate1/2/3 のリスクガード
- kabusys.data
  - calendar_management: JPX カレンダー取得・営業日ロジック
  - news_collector: RSS 取得・前処理・DB 保存ロジック
- utils（ログ設定・プロセス優先度等）: 起動時に呼ばれるユーティリティ（logging_setup, process_priority など）

---

## 典型的なワークフロー（例）
1. .env を作成
   - python -m kabusys.config_setup
2. 設定検証
   - python -m kabusys.validate_config
3. 監視プロセスを起動（常駐）
   - python -m kabusys.run_monitoring
4. 発注エンジンを起動（セッション時）
   - python -m kabusys.run_execution
5. （開発）ペーパートレード実行は KABUSYS_ENV=paper_trading を設定して実行

---

## 主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意:
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (data/kabusys.duckdb)
  - SQLITE_PATH (data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
  - LOG_LEVEL (INFO 等)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番通知）
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔）
  - PAPER_FILL_MODE（instant | partial | never | reject）

設定は Settings クラス経由で取得され、妥当性チェックはプロパティで行われます（不正なら例外）。

---

## トラブルシューティング
- config/*.yaml のパースチェックは PyYAML が必要です。未インストール時は検証はスキップされ警告になります。
- KabuStationClient を使う場合は kabuステーション® アプリがローカルで起動している必要があります（API 稼働）。
- WebSocket 通信には websocket-client が必要です。
- DuckDB を使用するため duckdb Python パッケージが必要です。
- .env の自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで利用）。

---

## ディレクトリ構成（主要ファイル）
（以下は src/kabusys 配下の主要ファイル / モジュールの一覧と概要）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 自動読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py         — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API Protocol / データモデル / ファクトリ
    - kabu_client.py         — kabu station REST API 実装（httpx / websocket）
    - mock_client.py         — MockBrokerClient（テスト用）
    - broker_factory.py      — Settings に応じたクライアント生成
    - order_record.py        — Order の状態モデルと遷移ロジック
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — 外向け注文 API（create/send/sync/cancel）
    - execution_engine.py    — セッション実行ロジック（信号処理・push ドレイン）
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — Gate1/2/3 のリスクチェック
  - data/
    - calendar_management.py — JPX カレンダー管理、営業日判定、夜間ジョブ
    - news_collector.py      — RSS ニュース収集・前処理
  - monitoring/ (監視関連のモジュール群 — example: monitoring_db, system_monitor 等)
  - utils/ (logging_setup, process_priority などのユーティリティ)

---

## 開発メモ / 注意点
- Order の状態遷移は OrderRecord と OrderManager で厳密に管理されています。Reconciler はクラッシュ後の自動復旧に重要です。
- ExecutionEngine はセッション時間に依存した処理フロー（シグナル処理と push ドレイン）を実装しています。テストでは個別メソッド呼び出しで再利用可能です。
- 本番運用時は KABUSYS_ENV=live の設定を慎重に行ってください（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 等のガードがあります）。

---

必要であれば、README に含める具体的な例（.env.example、起動スクリプトの systemd ユニットサンプル、Dockerfile、requirements.txt 等）も作成できます。どの内容を優先して追加しますか？